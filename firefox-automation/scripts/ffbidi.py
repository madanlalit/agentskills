#!/usr/bin/env python3
"""
ffbidi — driverless Firefox automation over WebDriver BiDi (native WebSocket, no drivers).

Drive Firefox directly through its built-in BiDi endpoint:
  Firefox:  --remote-debugging-port <port>   (Remote Agent, BiDi at ws://host:port/session)

Architecture:
  ffbidi.py <cmd> ── HTTP/JSON ──► daemon (holds live sessions) ── BiDi WebSocket ──► browser
"""
import argparse
import atexit
import base64
import datetime
import glob
import hashlib
import http.server
import json
import os
import platform
import secrets
import shutil
import signal
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_STATE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "ffbidi")

IDLE_TIMEOUT = int(os.environ.get("FFBIDI_IDLE_TIMEOUT", "1200"))   # daemon exits after idle (no RPC) with no sessions
EVENT_CAP = 2000
SHORT_ID = 8

FIREFOX_BIN = os.environ.get("FFBIDI_FIREFOX_BIN") or "/Applications/Firefox.app/Contents/MacOS/firefox"


class WebSocketError(Exception):
    pass


# ---------------------------------------------------------------------------
# Minimal WebSocket client (stdlib only — RFC 6455)
#
# Sends NO Origin header on the handshake (required by Firefox's BiDi Remote
# Agent, which rejects connections with an Origin). Same proven approach as
# the chrome-cdp skill's RawWebSocket.
# ---------------------------------------------------------------------------


class RawWebSocket:
    def __init__(self, sock):
        self.sock = sock
        self._closed = False
        self._send_lock = threading.Lock()

    @classmethod
    def connect(cls, ws_url, timeout=30):
        parsed = urlparse(ws_url)
        if parsed.scheme not in {"ws", "wss"}:
            raise WebSocketError(f"Unsupported WebSocket scheme: {parsed.scheme}")
        host = parsed.hostname
        if not host:
            raise WebSocketError(f"Invalid WebSocket URL: {ws_url}")
        port = parsed.port or (443 if parsed.scheme == "wss" else 80)
        try:
            raw_sock = socket.create_connection((host, port), timeout=timeout)
        except OSError as e:
            raise WebSocketError(f"could not connect to {host}:{port}: {e}") from None
        if parsed.scheme == "wss":
            context = ssl.create_default_context()
            raw_sock = context.wrap_socket(raw_sock, server_hostname=host)
        raw_sock.settimeout(timeout)

        key = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        host_header = f"{host}:{port}" if parsed.port else host
        # NB: deliberately no Origin header
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host_header}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        raw_sock.sendall(request.encode("ascii"))

        response = b""
        while b"\r\n\r\n" not in response:
            chunk = raw_sock.recv(4096)
            if not chunk:
                raw_sock.close()
                raise WebSocketError("WebSocket handshake failed: connection closed")
            response += chunk
        head = response.split(b"\r\n\r\n", 1)[0].decode("utf-8", "replace")
        lines = head.split("\r\n")
        if not lines or "101" not in lines[0]:
            raw_sock.close()
            raise WebSocketError(f"WebSocket handshake failed: {lines[0] if lines else 'no response'}")
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        expected = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
        ).decode("ascii")
        if headers.get("sec-websocket-accept") != expected:
            raw_sock.close()
            raise WebSocketError("WebSocket handshake failed: invalid Sec-WebSocket-Accept")
        # blocking after handshake: the daemon holds the connection open
        raw_sock.settimeout(None)
        return cls(raw_sock)

    def _recv_exact(self, size):
        buf = bytearray()
        while len(buf) < size:
            chunk = self.sock.recv(size - len(buf))
            if not chunk:
                raise EOFError("WebSocket closed")
            buf.extend(chunk)
        return bytes(buf)

    def _send_frame(self, opcode, payload=b""):
        if self._closed:
            return
        first = 0x80 | (opcode & 0x0F)
        length = len(payload)
        if length < 126:
            header = bytes([first, 0x80 | length])
        elif length < (1 << 16):
            header = bytes([first, 0x80 | 126]) + length.to_bytes(2, "big")
        else:
            header = bytes([first, 0x80 | 127]) + length.to_bytes(8, "big")
        mask = secrets.token_bytes(4)
        masked = bytes(value ^ mask[i % 4] for i, value in enumerate(payload))
        with self._send_lock:
            self.sock.sendall(header + mask + masked)

    def send_text(self, text):
        self._send_frame(0x1, text.encode("utf-8"))

    def recv_message(self):
        message_opcode = None
        fragments = []
        while True:
            first, second = self._recv_exact(2)
            fin = bool(first & 0x80)
            opcode = first & 0x0F
            length = second & 0x7F
            if length == 126:
                length = int.from_bytes(self._recv_exact(2), "big")
            elif length == 127:
                length = int.from_bytes(self._recv_exact(8), "big")
            payload = self._recv_exact(length) if length else b""
            if opcode == 0x8:      # close
                self._closed = True
                raise EOFError("WebSocket closed by remote")
            if opcode == 0x9:      # ping -> pong
                self._send_frame(0xA, payload)
                continue
            if opcode == 0xA:      # pong
                continue
            if opcode in (0x1, 0x2):
                message_opcode = opcode
                fragments.append(payload)
            elif opcode == 0x0:    # continuation
                if message_opcode is None:
                    raise WebSocketError("Unexpected continuation frame")
                fragments.append(payload)
            else:
                continue
            if fin:
                data = b"".join(fragments)
                if message_opcode == 0x1:
                    return data.decode("utf-8")
                return data

    def close(self):
        if self._closed:
            return
        try:
            self._send_frame(0x8, b"")
        except OSError:
            pass
        self._closed = True
        try:
            self.sock.close()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def log(msg):
    print(f"[ffbidi {datetime.datetime.now().strftime('%H:%M:%S')}] {msg}", file=sys.stderr)


def state_dir():
    d = os.environ.get("FFBIDI_STATE_DIR") or DEFAULT_STATE_DIR
    os.makedirs(d, exist_ok=True)
    return d


def daemon_file():
    return os.path.join(state_dir(), "daemon.json")


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class BidiError(Exception):
    def __init__(self, error, message, stacktrace=""):
        super().__init__(f"{error}: {message}")
        self.error = error
        self.message = message
        self.stacktrace = stacktrace


# WebDriver key values (Unicode PUA) as accepted by BiDi input.performActions
KEY_MAP = {
    "Enter": "\uE007", "Return": "\uE007", "Tab": "\uE004", "Escape": "\uE00C",
    "Backspace": "\uE003", "Delete": "\uE017", "Insert": "\uE016", "Home": "\uE011",
    "End": "\uE010", "PageUp": "\uE00E", "PageDown": "\uE00F",
    "ArrowLeft": "\uE012", "ArrowUp": "\uE013", "ArrowRight": "\uE014", "ArrowDown": "\uE015",
    "Shift": "\uE008", "Control": "\uE009", "Alt": "\uE00A", "Meta": "\uE03D", "Cmd": "\uE03D",
    "CapsLock": "\uE01E", "Space": " ", "\n": "\uE007", "\t": "\uE004",
}
for _i in range(1, 13):
    KEY_MAP[f"F{_i}"] = chr(0xE031 + _i - 1)


def unwrap(v):
    if not isinstance(v, dict) or "type" not in v:
        return v
    t = v["type"]
    if t in ("string", "number", "boolean", "null", "undefined"):
        return v.get("value")
    if t == "array":
        return [unwrap(x) for x in v.get("value", [])]
    if t == "object":
        return {k: unwrap(x) for k, x in v.get("value", [])}
    if t == "map":
        return {k: unwrap(x) for k, x in v.get("value", [])}
    if t == "set":
        return [unwrap(x) for x in v.get("value", [])]
    if t == "node":
        return {"node": v.get("sharedId"), "localName": v.get("value", {}).get("localName")}
    return {"type": t, "value": v.get("value")}


# ---------------------------------------------------------------------------
# BiDi client (one per browser session)
# ---------------------------------------------------------------------------


class BidiClient:
    def __init__(self, ws, session_id):
        self.ws = ws
        self.session_id = session_id
        self._id = 0
        self._lock = threading.Lock()
        self._pending = {}          # msg id -> (threading.Event, slot dict)
        self._closed = False

    def command(self, method, params=None, timeout=30):
        with self._lock:
            self._id += 1
            mid = self._id
            ev = threading.Event()
            slot = {"msg": None}
            self._pending[mid] = (ev, slot)
        self.ws.send_text(json.dumps({"id": mid, "method": method, "params": params or {}}))
        if not ev.wait(timeout):
            with self._lock:
                self._pending.pop(mid, None)
            raise BidiError("timeout", f"{method} did not respond within {timeout}s")
        msg = slot["msg"]
        if msg.get("type") == "error":
            raise BidiError(msg.get("error", "error"), msg.get("message", ""), msg.get("stacktrace", ""))
        return msg.get("result", {})

    def reader(self, on_event):
        """Background reader thread: dispatch responses + events."""
        while not self._closed:
            try:
                msg = json.loads(self.ws.recv_message())
            except Exception:
                break
            mid = msg.get("id")
            if mid is not None:
                with self._lock:
                    entry = self._pending.pop(mid, None)
                if entry:
                    entry[1]["msg"] = msg
                    entry[0].set()
            elif msg.get("type") == "event":
                try:
                    on_event(msg)
                except Exception:
                    pass
        # fail any stragglers
        with self._lock:
            pend = list(self._pending.items())
            self._pending.clear()
        for mid, (ev, slot) in pend:
            slot["msg"] = {"type": "error", "error": "connection closed", "message": "websocket closed"}
            ev.set()

    def close(self):
        self._closed = True
        try:
            self.ws.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Browser session
# ---------------------------------------------------------------------------


class Session:
    def __init__(self, sid, browser, proc, port, profile_dir, ws_url, bidi, created, trace, temp_profile):
        self.sid = sid
        self.browser = browser
        self.proc = proc
        self.port = port
        self.profile_dir = profile_dir
        self.temp_profile = temp_profile
        self.ws_url = ws_url
        self.bidi = bidi
        self.created = created
        self.trace = trace
        self.net_on = trace
        self.console_on = trace
        self.net_events = []
        self.log_entries = []
        self.events_lock = threading.Lock()
        self.trace_lock = threading.Lock()
        self.subscriptions = {}   # event name -> subscription id
        self.active_context = None

    def on_event(self, msg):
        method = msg.get("method", "")
        params = msg.get("params", {})
        ts = time.time()
        with self.events_lock:
            if method == "log.entryAdded":
                self.log_entries.append({"t": ts, "level": params.get("level"), "text": params.get("text"),
                                         "stack": params.get("stackTrace")})
                if len(self.log_entries) > EVENT_CAP:
                    del self.log_entries[:-EVENT_CAP]
            elif method.startswith("network."):
                req = params.get("request") or {}
                resp = params.get("response") or {}
                kind = {"network.beforeRequestSent": "request", "network.responseStarted": "response",
                        "network.responseCompleted": "completed", "network.fetchError": "error",
                        "network.authRequired": "auth"}.get(method, method)
                self.net_events.append({"t": ts, "type": kind, "url": req.get("url") or resp.get("url"),
                                        "method": req.get("method"), "status": resp.get("status")})
                if len(self.net_events) > EVENT_CAP:
                    del self.net_events[:-EVENT_CAP]

    # ---- helpers used by commands ----

    def context(self, ctx=None):
        """Return the target context: explicit, else the ACTIVE (focused) tab, else tracked, else first."""
        if ctx:
            return ctx
        try:
            tree = self.bidi.command("browsingContext.getTree")
        except Exception:
            tree = {"contexts": []}

        def flatten(nodes):
            for n in nodes or []:
                yield n
                yield from flatten(n.get("children") or [])

        all_ctx = list(flatten(tree.get("contexts") or []))
        tops = [n for n in all_ctx if not n.get("parent")]
        if not tops:
            raise BidiError("no contexts", "no browsing contexts found")

        # 1. tracked active context, if it still exists
        if self.active_context:
            if any(c["context"] == self.active_context for c in all_ctx):
                return self.active_context
            self.active_context = None

        # 2. single-tab case
        if len(tops) == 1:
            self.active_context = tops[0]["context"]
            return self.active_context

        # 3. multi-tab: find the one with document focus
        for n in tops:
            try:
                r = self.bidi.command("script.evaluate", {
                    "expression": "document.hasFocus()",
                    "target": {"context": n["context"]},
                    "awaitPromise": True, "resultOwnership": "none"})
                if r.get("result", {}).get("value") is True:
                    self.active_context = n["context"]
                    return n["context"]
            except Exception:
                continue

        # 4. fallback: first top-level context
        self.active_context = tops[0]["context"]
        return self.active_context

    def all_contexts(self):
        tree = self.bidi.command("browsingContext.getTree")
        out = []

        def walk(nodes, depth):
            for n in nodes or []:
                out.append({"context": n["context"], "url": n.get("url"), "parent": n.get("parent"), "depth": depth})
                walk(n.get("children"), depth + 1)
        walk(tree.get("contexts"), 0)
        return out

    def evaluate(self, expression, ctx=None, await_promise=True):
        r = self.bidi.command("script.evaluate", {
            "expression": expression,
            "target": {"context": self.context(ctx)},
            "awaitPromise": await_promise,
            "resultOwnership": "none",
        }, timeout=30)
        if r.get("type") == "exception":
            ex = r.get("exceptionDetails", {})
            return {"exception": unwrap(ex.get("exception", {})), "text": ex.get("text")}
        return unwrap(r.get("result"))

    def subscribe(self, events):
        r = self.bidi.command("session.subscribe", {"events": events})
        sub_id = r.get("subscription")
        for ev in events:
            self.subscriptions[ev] = sub_id
        return sub_id

    def unsubscribe(self, subscription_id):
        self.bidi.command("session.unsubscribe", {"subscriptions": [subscription_id]})
        for ev in list(self.subscriptions):
            if self.subscriptions[ev] == subscription_id:
                del self.subscriptions[ev]

    def unsubscribe_net(self):
        ids = {v for k, v in self.subscriptions.items() if k.startswith("network.")}
        for i in ids:
            self.unsubscribe(i)

    def unsubscribe_console(self):
        ids = {v for k, v in self.subscriptions.items() if k == "log.entryAdded"}
        for i in ids:
            self.unsubscribe(i)

    def element_point(self, selector):
        """Scroll element into view, return its center point (viewport coords)."""
        expr = f"""( () => {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el) return {{ err: 'not found: {selector}' }};
            el.scrollIntoView({{ block: 'center', inline: 'center', behavior: 'instant' }});
            const r = el.getBoundingClientRect();
            return {{ x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2), w: Math.round(r.width), h: Math.round(r.height) }};
        }} )()"""
        return self.evaluate(expr, await_promise=True)

    def perform_actions(self, actions):
        self.bidi.command("input.performActions", {"context": self.context(), "actions": actions})

    def key_actions(self, sequence, press=False):
        seq = list(sequence)
        acts = []
        for c in seq:
            key = KEY_MAP.get(c, c)
            acts.append({"type": "keyDown", "value": key})
            acts.append({"type": "keyUp", "value": key})
        return [{"type": "key", "id": "keyboard", "actions": acts}]

    def pointer_click_actions(self, x, y):
        return [{"type": "pointer", "id": "mouse", "parameters": {"pointerType": "mouse"}, "actions": [
            {"type": "pointerMove", "x": x, "y": y, "duration": 50, "origin": "viewport"},
            {"type": "pointerDown", "button": 0},
            {"type": "pointerUp", "button": 0},
        ]}]

    def pointer_hover_actions(self, x, y):
        return [{"type": "pointer", "id": "mouse", "parameters": {"pointerType": "mouse"}, "actions": [
            {"type": "pointerMove", "x": x, "y": y, "duration": 50, "origin": "viewport"},
        ]}]

    def screenshot(self, full=False):
        r = self.bidi.command("browsingContext.captureScreenshot",
                              {"context": self.context(), "origin": "document" if full else "viewport"}, timeout=60)
        return base64.b64decode(r["data"])

    def alive(self):
        return self.proc is None or self.proc.poll() is None

    def info(self):
        if not self.alive():
            return {"id": self.sid, "browser": self.browser, "url": "(browser process exited)",
                    "created": self.created, "trace": self.trace, "net_on": self.net_on,
                    "console_on": self.console_on, "port": self.port, "dead": True}
        try:
            r = self.bidi.command("browsingContext.getTree", {"maxDepth": 0})
            ctx = (r.get("contexts") or [{}])[0]
            url = ctx.get("url", "")
        except Exception:
            url = ""
        return {"id": self.sid, "browser": self.browser, "url": url, "created": self.created,
                "trace": self.trace, "net_on": self.net_on, "console_on": self.console_on, "port": self.port}

    def stop(self):
        try:
            self.bidi.command("session.end", timeout=10)
        except Exception:
            pass
        try:
            self.bidi.close()
        except Exception:
            pass
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self.temp_profile and self.profile_dir and os.path.isdir(self.profile_dir):
            shutil.rmtree(self.profile_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Browser launching
# ---------------------------------------------------------------------------


def _check_binary(path, display):
    if not os.path.exists(path):
        raise BidiError("browser not found", f"{display} binary not found at: {path}\n  set BIDI_*_BIN env var to override")
    return path


def browser_version(binpath):
    try:
        out = subprocess.run([binpath, "--version"], capture_output=True, text=True, timeout=10)
        return (out.stdout or out.stderr or "").strip().splitlines()[0] if (out.stdout or out.stderr) else "?"
    except Exception:
        return "?"


def launch_firefox(profile, headless):
    port = free_port()
    temp_profile = False
    binpath = _check_binary(FIREFOX_BIN, "Firefox")
    if profile:
        profdir = os.path.abspath(os.path.expanduser(profile))
        if not os.path.isdir(profdir):
            raise BidiError("profile not found", f"profile dir does not exist: {profdir}")
    else:
        profdir = tempfile.mkdtemp(prefix="ffbidi-ff-")
        temp_profile = True
    cmd = [binpath, "--remote-debugging-port", str(port), "-profile", profdir]
    if headless:
        cmd.append("-headless")
    cmd.append("about:blank")
    logfile = open(os.path.join(state_dir(), f"browser-{port}.log"), "w")
    proc = subprocess.Popen(cmd, stdout=logfile, stderr=subprocess.STDOUT)
    return port, proc, profdir, temp_profile


def connect_bidi(port, timeout=40):
    url = f"ws://127.0.0.1:{port}/session"
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            ws = RawWebSocket.connect(url, timeout=5)
            ws.send_text(json.dumps({"id": 1, "method": "session.new", "params": {"capabilities": {"alwaysMatch": {}}}}))
            msg = json.loads(ws.recv_message())
            if msg.get("type") != "success":
                raise BidiError("session.new failed", json.dumps(msg)[:300])
            sid = msg["result"].get("sessionId")
            return ws, sid, url
        except Exception as e:
            last_err = e
            try:
                ws.close()
            except Exception:
                pass
            time.sleep(0.5)
    raise BidiError("connect failed", f"could not establish BiDi session on port {port}: {last_err}")


# ---------------------------------------------------------------------------
# Daemon
# ---------------------------------------------------------------------------


class Daemon:
    def __init__(self):
        self.sessions = {}
        self.lock = threading.Lock()
        self.last_rpc = time.time()
        self.stopping = False
        self.port = free_port()
        self.httpd = None

    # ---- RPC handlers ----

    def rpc(self, method, params):
        self.last_rpc = time.time()
        fn = getattr(self, f"do_{method}", None)
        if fn is None:
            return {"ok": False, "error": f"unknown method: {method}"}
        try:
            return {"ok": True, "result": fn(params)}
        except BidiError as e:
            return {"ok": False, "error_type": e.error, "error": e.message}
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}

    def do_ping(self, p):
        return {"pong": True}

    def do_doctor(self, p):
        ff = os.path.exists(FIREFOX_BIN)
        return {
            "state_dir": state_dir(),
            "daemon_port": self.port,
            "python": sys.version.split()[0],
            "deps": "stdlib only (no packages required)",
            "browsers": {
                "firefox": {"found": ff, "path": FIREFOX_BIN, "version": browser_version(FIREFOX_BIN) if ff else None},
            },
            "sessions": len(self.sessions),
            "idle_timeout_s": IDLE_TIMEOUT,
        }

    def do_list(self, p):
        return [s.info() for s in self.sessions.values()]

    def do_new(self, p):
        trace = bool(p.get("trace"))
        port, proc, profdir, temp_profile = launch_firefox(p.get("profile"), p.get("headless"))
        ws, sid, ws_url = connect_bidi(port)
        sess = Session(sid=uuid.uuid4().hex[:SHORT_ID], browser="firefox", proc=proc, port=port,
                       profile_dir=profdir, temp_profile=temp_profile, ws_url=ws_url, bidi=BidiClient(ws, sid),
                       created=datetime.datetime.now().isoformat(timespec="seconds"), trace=trace)
        threading.Thread(target=ws_reader_loop, args=(sess,), daemon=True).start()
        sess.context()   # establish active context
        if trace:
            sess.subscribe(["network.beforeRequestSent", "network.responseStarted",
                            "network.responseCompleted", "network.fetchError", "network.authRequired"])
            sess.subscribe(["log.entryAdded"])
        nav = {}
        if p.get("url"):
            nav = self._nav_and_wait(sess, sess.context(), p["url"])
        with self.lock:
            self.sessions[sess.sid] = sess
        info = sess.info()
        info["nav"] = nav or None
        return info

    def do_stop(self, p):
        sid = p["session"]
        with self.lock:
            sess = self.sessions.pop(sid, None)
        if not sess:
            raise BidiError("no session", f"unknown session: {sid}")
        sess.stop()
        return {"stopped": sid}

    def do_stop_all(self, p):
        stopped = []
        with self.lock:
            sessions = list(self.sessions.values())
            self.sessions.clear()
        for s in sessions:
            s.stop()
            stopped.append(s.sid)
        return {"stopped": stopped}

    def _sess(self, p):
        sid = p.get("session")
        with self.lock:
            s = self.sessions.get(sid)
        if not s:
            raise BidiError("no session", f"unknown session: {sid} (see `list`)")
        if not s.alive():
            raise BidiError("session dead", f"browser process for session {sid} has exited")
        return s

    def _nav_and_wait(self, s, ctx, url, timeout=25):
        s.bidi.command("browsingContext.navigate", {"context": ctx, "url": url, "wait": "none"})
        deadline = time.time() + timeout
        state = "incomplete"
        final_url = url
        while time.time() < deadline:
            try:
                state = s.evaluate("document.readyState")
                final_url = s.evaluate("location.href")
                if state == "complete":
                    break
            except Exception:
                pass
            time.sleep(0.3)
        return {"url": final_url, "readyState": state}

    def do_nav(self, p):
        s = self._sess(p)
        return self._nav_and_wait(s, s.context(), p["url"])

    def do_eval(self, p):
        s = self._sess(p)
        r = s.evaluate(p["expression"], p.get("context"))
        if isinstance(r, dict) and r.get("exception"):
            return {"exception": r.get("exception"), "text": r.get("text")}
        return {"value": r}

    def do_wait(self, p):
        s = self._sess(p)
        sel = p["selector"]
        gone = bool(p.get("gone"))
        timeout = float(p.get("timeout", 15))
        expr = f"!!document.querySelector({json.dumps(sel)})"
        if gone:
            expr = f"!document.querySelector({json.dumps(sel)})"
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if s.evaluate(expr):
                    return {"found": True, "selector": sel, "gone": gone, "waited_s": round(timeout - (deadline - time.time()), 2)}
            except Exception:
                pass
            time.sleep(0.3)
        return {"found": False, "selector": sel, "gone": gone, "waited_s": timeout}

    def do_click(self, p):
        s = self._sess(p)
        pt = s.element_point(p["selector"])
        if "err" in pt:
            raise BidiError("not found", pt["err"])
        s.perform_actions(s.pointer_click_actions(pt["x"], pt["y"]))
        return {"clicked": p["selector"], "at": [pt["x"], pt["y"]]}

    def do_hover(self, p):
        s = self._sess(p)
        pt = s.element_point(p["selector"])
        if "err" in pt:
            raise BidiError("not found", pt["err"])
        s.perform_actions(s.pointer_hover_actions(pt["x"], pt["y"]))
        return {"hovered": p["selector"], "at": [pt["x"], pt["y"]]}

    def do_type(self, p):
        s = self._sess(p)
        s.perform_actions(s.key_actions(p["text"]))
        return {"typed": len(p["text"])}

    def do_fill(self, p):
        s = self._sess(p)
        sel = p["selector"]
        # Focus via JS, then select-all + type via real key events. No JS value
        # manipulation: that fights React/Vue controlled inputs (they re-render and
        # drop the edit). Real keys update framework state correctly.
        expr = f"""( () => {{
            const el = document.querySelector({json.dumps(sel)});
            if (!el) return {{ err: 'not found: {sel}' }};
            el.focus();
            return {{ ok: true }};
        }} )()"""
        r = s.evaluate(expr)
        if isinstance(r, dict) and r.get("err"):
            raise BidiError("not found", r["err"])
        time.sleep(0.15)  # let focus settle
        meta = KEY_MAP.get("Meta")
        s.perform_actions([{"type": "key", "id": "keyboard", "actions": [
            {"type": "keyDown", "value": meta}, {"type": "keyDown", "value": "a"},
            {"type": "keyUp", "value": "a"}, {"type": "keyUp", "value": meta}]}])
        s.perform_actions(s.key_actions(p["text"]))
        return {"filled": sel}

    def do_press(self, p):
        s = self._sess(p)
        key = KEY_MAP.get(p["key"], p["key"])
        s.perform_actions([{"type": "key", "id": "keyboard", "actions": [
            {"type": "keyDown", "value": key}, {"type": "keyUp", "value": key}]}])
        return {"pressed": p["key"]}

    def do_html(self, p):
        s = self._sess(p)
        if p.get("selector"):
            expr = f"(() => {{ const el = document.querySelector({json.dumps(p['selector'])}); return el ? el.outerHTML : null; }})()"
        else:
            expr = "document.documentElement.outerHTML"
        return {"html": s.evaluate(expr)}

    def do_shot(self, p):
        s = self._sess(p)
        full = bool(p.get("full"))
        png = s.screenshot(full=full)
        path = p.get("path") or os.path.join(os.getcwd(), f"bidi-shot-{s.sid}-{int(time.time())}.png")
        with open(path, "wb") as f:
            f.write(png)
        return {"path": os.path.abspath(path), "bytes": len(png), "full": full}

    def do_scroll(self, p):
        s = self._sess(p)
        direction = p.get("direction", "down")
        px = p.get("px")
        if direction == "top":
            expr = "window.scrollTo(0, 0); 'top'"
        elif direction == "bottom":
            expr = "window.scrollTo(0, document.body.scrollHeight); 'bottom'"
        elif direction in ("up", "down", "left", "right"):
            sign = {"down": 1, "up": -1, "right": 1, "left": -1}[direction]
            prop = "left" if direction in ("left", "right") else "top"
            if px is None:
                expr = f"window.scrollBy({{ {prop}: Math.round(window.innerHeight * 0.85) * {sign}, behavior: 'instant' }}); '{direction}'"
            else:
                expr = f"window.scrollBy({{ {prop}: {sign * int(px)}, behavior: 'instant' }}); '{direction}'"
        else:
            raise BidiError("bad direction", f"scroll direction must be up/down/left/right/top/bottom, got {direction}")
        s.evaluate(expr)
        pos = s.evaluate("window.scrollY")
        return {"scrolled": direction, "scrollY": pos}

    def do_activate(self, p):
        s = self._sess(p)
        ctx = p.get("context") or p["session"]
        # context ids are stable in Firefox, but a tab mid-navigation-commit can
        # transiently report "no such frame"; retry briefly
        last = None
        for _ in range(10):
            try:
                s.bidi.command("browsingContext.activate", {"context": ctx})
                s.active_context = ctx
                return {"activated": ctx}
            except BidiError as e:
                last = e
                if "not found" not in (e.message + e.error):
                    raise
                time.sleep(0.3)
        raise last

    def do_tab(self, p):
        s = self._sess(p)
        r = s.bidi.command("browsingContext.create", {"type": "tab"})
        ctx = r["context"]
        s.active_context = ctx
        if p.get("url"):
            s.bidi.command("browsingContext.navigate", {"context": ctx, "url": p["url"], "wait": "none"})
            deadline = time.time() + 20
            while time.time() < deadline:
                try:
                    if s.evaluate("document.readyState", ctx=ctx) == "complete":
                        break
                except Exception:
                    pass
                time.sleep(0.3)
        return {"tab": ctx, "url": p.get("url") or "about:blank", "active": True}

    def do_tabs(self, p):
        s = self._sess(p)
        active = s.context()
        out = []
        for c in s.all_contexts():
            c["active"] = (c["context"] == active)
            out.append(c)
        return out

    def do_cookies(self, p):
        s = self._sess(p)
        out = {}
        for ctx in s.all_contexts():
            if ctx["parent"]:  # top-level only
                continue
            r = s.bidi.command("storage.getCookies", {"partition": {"type": "context", "context": ctx["context"]}})
            for c in r.get("cookies", []):
                out[c["name"]] = {"name": c["name"], "value": unwrap(c.get("value")), "domain": c.get("domain"),
                                  "path": c.get("path"), "expires": c.get("expires"), "secure": c.get("secure"),
                                  "httpOnly": c.get("httpOnly"), "sameSite": c.get("sameSite")}
        return list(out.values())

    def do_storage(self, p):
        s = self._sess(p)
        session_storage = bool(p.get("session_flag"))
        prefix = "sessionStorage" if session_storage else "localStorage"
        expr = f"""( () => {{
            const o = {{}};
            for (let i = 0; i < {prefix}.length; i++) {{ const k = {prefix}.key(i); o[k] = {prefix}.getItem(k); }}
            return o;
        }} )()"""
        return s.evaluate(expr)

    def do_storage_set(self, p):
        s = self._sess(p)
        prefix = "sessionStorage" if p.get("session_flag") else "localStorage"
        expr = f"{prefix}.setItem({json.dumps(p['key'])}, {json.dumps(p['value'])}); 'ok'"
        s.evaluate(expr)
        return {"set": p["key"]}

    def do_net(self, p):
        s = self._sess(p)
        if p.get("on"):
            if s.net_on:
                return {"net": "on", "already": True}
            s.net_on = True
            s.subscribe(["network.beforeRequestSent", "network.responseStarted", "network.responseCompleted",
                         "network.fetchError", "network.authRequired"])
            return {"net": "on"}
        if p.get("off"):
            s.net_on = False
            s.unsubscribe_net()
            return {"net": "off"}
        if p.get("clear"):
            with s.events_lock:
                s.net_events = []
            return {"cleared": True}
        flt = p.get("filter")
        with s.events_lock:
            evts = list(s.net_events)
        if flt:
            evts = [e for e in evts if flt in (e.get("url") or "")]
        return {"on": s.net_on, "events": evts[-200:]}

    def do_console(self, p):
        s = self._sess(p)
        if p.get("on"):
            if s.console_on:
                return {"console": "on", "already": True}
            s.console_on = True
            s.subscribe(["log.entryAdded"])
            return {"console": "on"}
        if p.get("off"):
            s.console_on = False
            s.unsubscribe_console()
            return {"console": "off"}
        if p.get("clear"):
            with s.events_lock:
                s.log_entries = []
            return {"cleared": True}
        with s.events_lock:
            entries = list(s.log_entries)
        return {"on": s.console_on, "entries": entries[-200:]}

    def do_state(self, p):
        return self._sess(p).info()

    # ---- daemon server ----

    def serve(self):
        self._kill_stale_daemons()
        host = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path != "/rpc":
                    self.send_error(404)
                    return
                length = int(self.headers.get("Content-Length", 0))
                try:
                    req = json.loads(self.rfile.read(length))
                except Exception:
                    req = {}
                resp = host.rpc(req.get("method"), req.get("params") or {})
                body = json.dumps(resp).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        with open(daemon_file(), "w") as f:
            json.dump({"pid": os.getpid(), "port": self.port}, f)
        log(f"daemon ready on 127.0.0.1:{self.port} (state: {state_dir()})")
        threading.Thread(target=self._idle_watchdog, daemon=True).start()
        try:
            self.httpd.serve_forever()
        finally:
            self.shutdown()

    def _kill_stale_daemons(self):
        """Single-daemon invariant: terminate other bidi daemons (from this skill) before serving.
        Prevents stale daemons accumulating when daemon.json goes stale."""
        try:
            out = subprocess.run(["pgrep", "-f", "ffbidi.py daemon"], capture_output=True, text=True, timeout=5)
            for pid_str in out.stdout.split():
                pid = int(pid_str)
                if pid == os.getpid():
                    continue
                try:
                    os.kill(pid, signal.SIGKILL)
                    log(f"killed stale daemon pid {pid}")
                except Exception:
                    pass
        except Exception:
            pass

    def _idle_watchdog(self):
        while not self.stopping:
            time.sleep(30)
            if self.stopping:
                return
            with self.lock:
                has_sessions = bool(self.sessions)
            idle_for = time.time() - self.last_rpc
            if not has_sessions and idle_for > IDLE_TIMEOUT:
                log(f"idle {int(idle_for)}s with no sessions, exiting")
                self.shutdown()
                os._exit(0)   # hard exit: never leave a zombie daemon behind
                return

    def shutdown(self):
        if self.stopping:
            return
        self.stopping = True
        with self.lock:
            sessions = list(self.sessions.values())
            self.sessions.clear()
        for s in sessions:
            s.stop()
        if self.httpd:
            # run shutdown() in a daemon thread so a wedged httpd can't block exit;
            # the process exits when serve() returns regardless.
            try:
                t = threading.Thread(target=self.httpd.shutdown, daemon=True)
                t.start()
            except Exception:
                pass
        try:
            if os.path.exists(daemon_file()):
                os.remove(daemon_file())
        except Exception:
            pass
        log("daemon stopped")


def ws_reader_loop(sess):
    sess.bidi.reader(sess.on_event)


def main_daemon():
    daemon = Daemon()
    atexit.register(daemon.shutdown)
    signal.signal(signal.SIGTERM, lambda *a: daemon.shutdown())
    signal.signal(signal.SIGINT, lambda *a: daemon.shutdown())
    daemon.serve()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def find_daemon():
    """Return base URL of a live daemon, starting one if needed."""
    port = None
    dfile = daemon_file()
    if os.path.exists(dfile):
        try:
            with open(dfile) as f:
                meta = json.load(f)
            port = meta.get("port")
        except Exception:
            port = None
    if port:
        try:
            import urllib.request
            req = urllib.request.Request(f"http://127.0.0.1:{port}/rpc",
                                         data=json.dumps({"method": "ping", "params": {}}).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=2) as r:
                if json.loads(r.read()).get("ok"):
                    return port
        except Exception:
            pass
    # spawn daemon (stdlib-only: same interpreter as the CLI)
    devnull = open(os.devnull, "w")
    subprocess.Popen([sys.executable, os.path.abspath(__file__), "daemon"], stdout=devnull, stderr=devnull,
                     start_new_session=True)
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            with open(dfile) as f:
                port = json.load(f).get("port")
            import urllib.request
            req = urllib.request.Request(f"http://127.0.0.1:{port}/rpc",
                                         data=json.dumps({"method": "ping", "params": {}}).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=2) as r:
                if json.loads(r.read()).get("ok"):
                    return port
        except Exception:
            time.sleep(0.3)
    raise SystemExit("ERROR: daemon did not start")


def rpc(port, method, params=None, timeout=60):
    import urllib.request
    req = urllib.request.Request(f"http://127.0.0.1:{port}/rpc",
                                 data=json.dumps({"method": method, "params": params or {}}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read())
    if not resp.get("ok"):
        raise SystemExit(f"ERROR [{resp.get('error_type', 'error')}]: {resp.get('error')}")
    return resp.get("result")


def resolve_session(port, sid=None):
    sessions = rpc(port, "list")
    if sid:
        cands = [s for s in sessions if s["id"].startswith(sid)]
        if len(cands) == 1:
            return cands[0]["id"]
        if len(cands) > 1:
            raise SystemExit(f"ERROR: ambiguous session prefix '{sid}': {[c['id'] for c in cands]}")
        raise SystemExit(f"ERROR: no session matching '{sid}' (see `list`)")
    if len(sessions) == 0:
        raise SystemExit("ERROR: no active sessions (run `new` first)")
    if len(sessions) > 1:
        raise SystemExit("ERROR: multiple sessions; specify one:\n  " +
                         "\n  ".join(f"{s['id']}  {s['browser']}  {s['url']}" for s in sessions))
    return sessions[0]["id"]


def out(v):
    print(json.dumps(v, indent=2, default=str))


def out_page(v):
    """Output page-derived data wrapped in the untrusted-data trust boundary."""
    print("--- BEGIN BROWSER DATA ---")
    print(json.dumps(v, indent=2, default=str))
    print("--- END BROWSER DATA ---")


def main():
    ap = argparse.ArgumentParser(prog="ffbidi", description="Driverless Firefox automation via native WebDriver BiDi")
    sub = ap.add_subparsers(dest="cmd")

    sub.add_parser("doctor", help="environment diagnostics")
    sub.add_parser("list", help="list active sessions")

    p = sub.add_parser("new", help="launch a Firefox session")
    p.add_argument("--url", default=None)
    p.add_argument("--profile", default=None, help="existing Firefox profile dir to use")
    p.add_argument("--headless", action="store_true")
    p.add_argument("--trace", action="store_true", help="capture network + console events from the start")

    p = sub.add_parser("nav", help="navigate current tab")
    p.add_argument("url")
    p.add_argument("--session")

    p = sub.add_parser("eval", help="evaluate JS, return JSON")
    p.add_argument("expression")
    p.add_argument("--session")

    p = sub.add_parser("wait", help="wait for selector (or --gone)")
    p.add_argument("selector")
    p.add_argument("--gone", action="store_true")
    p.add_argument("--timeout", type=float, default=15)
    p.add_argument("--session")

    for c in ("click", "hover"):
        p = sub.add_parser(c, help=f"{c} a CSS selector")
        p.add_argument("selector")
        p.add_argument("--session")

    p = sub.add_parser("type", help="type text into focused element")
    p.add_argument("text")
    p.add_argument("--session")

    p = sub.add_parser("fill", help="focus, clear, and type into a selector")
    p.add_argument("selector")
    p.add_argument("text")
    p.add_argument("--session")

    p = sub.add_parser("press", help="press a key (Enter, Tab, Escape, ArrowDown, meta...)")
    p.add_argument("key")
    p.add_argument("--session")

    p = sub.add_parser("html", help="outer HTML of page or selector")
    p.add_argument("selector", nargs="?", default=None)
    p.add_argument("--session")

    p = sub.add_parser("scroll", help="scroll up/down/left/right (or top/bottom); optional px")
    p.add_argument("direction", choices=["up", "down", "left", "right", "top", "bottom"])
    p.add_argument("px", nargs="?", type=int, default=None)
    p.add_argument("--session")

    p = sub.add_parser("shot", help="screenshot (--full = whole document)")
    p.add_argument("path", nargs="?", default=None)
    p.add_argument("--full", action="store_true")
    p.add_argument("--session")

    p = sub.add_parser("tabs", help="list browsing contexts")
    p.add_argument("--session")

    p = sub.add_parser("tab", help="open a new tab (BiDi browsingContext.create) and make it active")
    p.add_argument("--url", default=None)
    p.add_argument("--session")

    p = sub.add_parser("activate", help="activate a context/tab")
    p.add_argument("context")
    p.add_argument("--session")

    p = sub.add_parser("cookies", help="get cookies (BiDi storage module)")
    p.add_argument("--session")

    p = sub.add_parser("storage", help="localStorage (or --session-storage for sessionStorage)")
    p.add_argument("--session-storage", action="store_true", help="use sessionStorage instead of localStorage")
    p.add_argument("--session", help="session id")
    p.add_argument("--set", metavar="key=value", help="set a storage key")

    p = sub.add_parser("net", help="network capture via BiDi: --on / --off / --clear / --filter <sub>")
    p.add_argument("--on", action="store_true")
    p.add_argument("--off", action="store_true")
    p.add_argument("--clear", action="store_true")
    p.add_argument("--filter", default=None)
    p.add_argument("--session")

    p = sub.add_parser("console", help="console log capture via BiDi: --on / --off / --clear")
    p.add_argument("--on", action="store_true")
    p.add_argument("--off", action="store_true")
    p.add_argument("--clear", action="store_true")
    p.add_argument("--session")

    p = sub.add_parser("stop", help="close a session (default: the only one)")
    p.add_argument("--session")

    p = sub.add_parser("stop-all", help="close every session")

    args = ap.parse_args()
    if not args.cmd:
        ap.print_help()
        return

    if args.cmd == "doctor":
        # doctor should work even without daemon
        port = find_daemon()
        out(rpc(port, "doctor"))
        return

    port = find_daemon()

    if args.cmd == "list":
        out(rpc(port, "list"))
        return

    if args.cmd == "new":
        out(rpc(port, "new", {"url": args.url, "profile": args.profile,
                              "headless": args.headless, "trace": args.trace}, timeout=120))
        return

    if args.cmd == "stop-all":
        out(rpc(port, "stop_all"))
        return

    sid = resolve_session(port, getattr(args, "session", None))

    if args.cmd == "nav":
        out(rpc(port, "nav", {"session": sid, "url": args.url}, timeout=60))
    elif args.cmd == "eval":
        out_page(rpc(port, "eval", {"session": sid, "expression": args.expression}, timeout=60))
    elif args.cmd == "wait":
        out_page(rpc(port, "wait", {"session": sid, "selector": args.selector, "gone": args.gone, "timeout": args.timeout}))
    elif args.cmd in ("click", "hover"):
        out(rpc(port, args.cmd, {"session": sid, "selector": args.selector}))
    elif args.cmd == "type":
        out(rpc(port, "type", {"session": sid, "text": args.text}))
    elif args.cmd == "fill":
        out(rpc(port, "fill", {"session": sid, "selector": args.selector, "text": args.text}))
    elif args.cmd == "press":
        out(rpc(port, "press", {"session": sid, "key": args.key}))
    elif args.cmd == "html":
        out_page(rpc(port, "html", {"session": sid, "selector": args.selector}))
    elif args.cmd == "scroll":
        out(rpc(port, "scroll", {"session": sid, "direction": args.direction, "px": args.px}))
    elif args.cmd == "shot":
        out(rpc(port, "shot", {"session": sid, "path": args.path, "full": args.full}, timeout=90))
    elif args.cmd == "tabs":
        out_page(rpc(port, "tabs", {"session": sid}))
    elif args.cmd == "tab":
        out(rpc(port, "tab", {"session": sid, "url": args.url}, timeout=60))
    elif args.cmd == "activate":
        out(rpc(port, "activate", {"session": sid, "context": args.context}))
    elif args.cmd == "cookies":
        out_page(rpc(port, "cookies", {"session": sid}))
    elif args.cmd == "storage":
        if args.set:
            k, _, v = args.set.partition("=")
            out(rpc(port, "storage_set", {"session": sid, "key": k, "value": v, "session_flag": args.session_storage}))
        else:
            out_page(rpc(port, "storage", {"session": sid, "session_flag": args.session_storage}))
    elif args.cmd == "net":
        out_page(rpc(port, "net", {"session": sid, "on": args.on, "off": args.off, "clear": args.clear, "filter": args.filter}))
    elif args.cmd == "console":
        out_page(rpc(port, "console", {"session": sid, "on": args.on, "off": args.off, "clear": args.clear}))
    elif args.cmd == "stop":
        out(rpc(port, "stop", {"session": sid}))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "daemon":
        main_daemon()
    else:
        main()
