#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import signal
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

TIMEOUT = 15.0
NAVIGATION_TIMEOUT = 30.0
IDLE_TIMEOUT = 20 * 60.0
DAEMON_CONNECT_RETRIES = 20
DAEMON_CONNECT_DELAY = 0.3
MIN_TARGET_PREFIX_LEN = 8
IS_WINDOWS = os.name == "nt"

if not IS_WINDOWS:
    os.umask(0o077)


class CLIError(RuntimeError):
    pass


class WebSocketError(RuntimeError):
    pass


class CDPError(RuntimeError):
    pass


def runtime_dir() -> Path:
    home = Path.home()
    candidates: list[Path] = []
    runtime_name = "chrome-cdp"

    custom = os.environ.get("CDP_RUNTIME_DIR")
    if custom:
        candidates.append(Path(custom).expanduser())

    if IS_WINDOWS:
        base = Path(os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local")))
        candidates.append(base / runtime_name)
    else:
        xdg_runtime = os.environ.get("XDG_RUNTIME_DIR")
        if xdg_runtime:
            candidates.append(Path(xdg_runtime) / runtime_name)
        candidates.append(home / ".cache" / runtime_name)

    candidates.append(Path(tempfile.gettempdir()) / runtime_name)

    for root in candidates:
        try:
            root.mkdir(parents=True, exist_ok=True)
            try:
                root.chmod(0o700)
            except OSError:
                pass
            return root
        except OSError:
            continue

    raise CLIError("Unable to create a writable runtime directory. Set CDP_RUNTIME_DIR to a writable path.")


RUNTIME_DIR = runtime_dir()
PAGES_CACHE = RUNTIME_DIR / "pages.json"


def secure_write_text(path: Path, text: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(text)
    try:
        os.chmod(tmp, mode)
    except OSError:
        pass
    os.replace(tmp, path)


def secure_write_json(path: Path, value: Any, mode: int = 0o600) -> None:
    secure_write_text(path, json.dumps(value), mode=mode)


def safe_unlink(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return
    except OSError:
        return


def read_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def daemon_meta_path(target_id: str) -> Path:
    return RUNTIME_DIR / f"cdp-{target_id}.json"


def get_ws_url() -> str:
    home = Path.home()
    mac_browsers = [
        "Google/Chrome",
        "Google/Chrome Beta",
        "Google/Chrome for Testing",
        "Chromium",
        "BraveSoftware/Brave-Browser",
        "Microsoft Edge",
    ]
    linux_browsers = [
        "google-chrome",
        "google-chrome-beta",
        "chromium",
        "vivaldi",
        "vivaldi-snapshot",
        "BraveSoftware/Brave-Browser",
        "microsoft-edge",
    ]
    flatpak_browsers = [
        ("org.chromium.Chromium", "chromium"),
        ("com.google.Chrome", "google-chrome"),
        ("com.brave.Browser", "BraveSoftware/Brave-Browser"),
        ("com.microsoft.Edge", "microsoft-edge"),
        ("com.vivaldi.Vivaldi", "vivaldi"),
    ]

    candidates: list[Path] = []
    custom_port_file = os.environ.get("CDP_PORT_FILE")
    if custom_port_file:
        candidates.append(Path(custom_port_file))

    for browser in mac_browsers:
        candidates.append(home / "Library" / "Application Support" / browser / "DevToolsActivePort")
        candidates.append(home / "Library" / "Application Support" / browser / "Default" / "DevToolsActivePort")

    for browser in linux_browsers:
        candidates.append(home / ".config" / browser / "DevToolsActivePort")
        candidates.append(home / ".config" / browser / "Default" / "DevToolsActivePort")

    for app_id, name in flatpak_browsers:
        candidates.append(home / ".var" / "app" / app_id / "config" / name / "DevToolsActivePort")
        candidates.append(home / ".var" / "app" / app_id / "config" / name / "Default" / "DevToolsActivePort")

    if IS_WINDOWS:
        base = Path(os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local")))
        for browser in ("Google/Chrome", "BraveSoftware/Brave-Browser", "Microsoft/Edge"):
            candidates.append(base / browser / "User Data" / "DevToolsActivePort")
            candidates.append(base / browser / "User Data" / "Default" / "DevToolsActivePort")

    port_file = next((path for path in candidates if path.exists()), None)
    if port_file is None:
        raise CLIError(
            "No DevToolsActivePort found. Enable remote debugging at chrome://inspect/#remote-debugging"
        )

    lines = port_file.read_text(encoding="utf-8").strip().splitlines()
    if len(lines) < 2 or not lines[0] or not lines[1]:
        raise CLIError(f"Invalid DevToolsActivePort file: {port_file}")

    host = os.environ.get("CDP_HOST", "127.0.0.1")
    return f"ws://{host}:{lines[0]}{lines[1]}"


def resolve_prefix(prefix: str, candidates: list[str], noun: str = "target", missing_hint: str = "") -> str:
    upper = prefix.upper()
    matches = [candidate for candidate in candidates if candidate.upper().startswith(upper)]
    if not matches:
        hint = f" {missing_hint}" if missing_hint else ""
        raise CLIError(f'No {noun} matching prefix "{prefix}".{hint}')
    if len(matches) > 1:
        raise CLIError(f'Ambiguous prefix "{prefix}" - matches {len(matches)} {noun}s. Use more characters.')
    return matches[0]


def get_display_prefix_length(target_ids: list[str]) -> int:
    if not target_ids:
        return MIN_TARGET_PREFIX_LEN
    max_len = max(len(target_id) for target_id in target_ids)
    for length in range(MIN_TARGET_PREFIX_LEN, max_len + 1):
        prefixes = {target_id[:length].upper() for target_id in target_ids}
        if len(prefixes) == len(target_ids):
            return length
    return max_len


class RawWebSocket:
    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self._send_lock = threading.Lock()
        self._closed = False

    @classmethod
    def connect(cls, ws_url: str, timeout: float = TIMEOUT) -> "RawWebSocket":
        parsed = urlparse(ws_url)
        if parsed.scheme not in {"ws", "wss"}:
            raise WebSocketError(f"Unsupported WebSocket scheme: {parsed.scheme}")

        host = parsed.hostname
        if not host:
            raise WebSocketError(f"Invalid WebSocket URL: {ws_url}")

        port = parsed.port or (443 if parsed.scheme == "wss" else 80)
        try:
            raw_sock = socket.create_connection((host, port), timeout=timeout)
        except ConnectionRefusedError:
            raise CLIError(f"Connection refused - check if the chrome browser is running or please allow remote debugging from chrome://inspect/#remote-debugging") from None

        if parsed.scheme == "wss":
            context = ssl.create_default_context()
            raw_sock = context.wrap_socket(raw_sock, server_hostname=host)
        raw_sock.settimeout(timeout)

        key = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        host_header = f"{host}:{port}" if parsed.port else host
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

        head = response.split(b"\r\n\r\n", 1)[0].decode("utf-8", errors="replace")
        lines = head.split("\r\n")
        if not lines or "101" not in lines[0]:
            raw_sock.close()
            raise WebSocketError(f"WebSocket handshake failed: {lines[0] if lines else 'no response'}")

        headers: dict[str, str] = {}
        for line in lines[1:]:
            if ":" not in line:
                continue
            key_name, value = line.split(":", 1)
            headers[key_name.strip().lower()] = value.strip()

        expected = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
        ).decode("ascii")
        if headers.get("sec-websocket-accept") != expected:
            raw_sock.close()
            raise WebSocketError("WebSocket handshake failed: invalid Sec-WebSocket-Accept")

        # The connect timeout is only for the initial handshake; the daemon needs
        # a blocking socket afterward so an idle tab session does not self-expire.
        raw_sock.settimeout(None)
        return cls(raw_sock)

    def _recv_exact(self, size: int) -> bytes:
        buf = bytearray()
        while len(buf) < size:
            chunk = self.sock.recv(size - len(buf))
            if not chunk:
                raise EOFError("WebSocket closed")
            buf.extend(chunk)
        return bytes(buf)

    def _send_frame(self, opcode: int, payload: bytes = b"") -> None:
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
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        with self._send_lock:
            self.sock.sendall(header + mask + masked)

    def send_text(self, text: str) -> None:
        self._send_frame(0x1, text.encode("utf-8"))

    def recv_message(self) -> str | bytes:
        message_opcode: int | None = None
        fragments: list[bytes] = []

        while True:
            header = self._recv_exact(2)
            first, second = header
            fin = bool(first & 0x80)
            opcode = first & 0x0F
            masked = bool(second & 0x80)
            length = second & 0x7F

            if length == 126:
                length = int.from_bytes(self._recv_exact(2), "big")
            elif length == 127:
                length = int.from_bytes(self._recv_exact(8), "big")

            mask_key = self._recv_exact(4) if masked else b""
            payload = self._recv_exact(length) if length else b""
            if masked:
                payload = bytes(value ^ mask_key[index % 4] for index, value in enumerate(payload))

            if opcode == 0x8:
                self._closed = True
                raise EOFError("WebSocket closed by remote")
            if opcode == 0x9:
                self._send_frame(0xA, payload)
                continue
            if opcode == 0xA:
                continue
            if opcode in (0x1, 0x2):
                message_opcode = opcode
                fragments.append(payload)
            elif opcode == 0x0:
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

    def close(self) -> None:
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


class CDP:
    def __init__(self) -> None:
        self._ws: RawWebSocket | None = None
        self._next_id = 0
        self._responses: dict[int, dict[str, Any]] = {}
        self._events: list[tuple[float, dict[str, Any]]] = []
        self._handlers: dict[str, list[Any]] = {}
        self._close_handlers: list[Any] = []
        self._closed_error: BaseException | None = None
        self._reader_thread: threading.Thread | None = None
        self._condition = threading.Condition()

    def connect(self, ws_url: str) -> None:
        self._ws = RawWebSocket.connect(ws_url)
        self._reader_thread = threading.Thread(target=self._reader_loop, name="cdp-reader", daemon=True)
        self._reader_thread.start()

    def _reader_loop(self) -> None:
        close_handlers: list[Any] = []
        try:
            assert self._ws is not None
            while True:
                raw = self._ws.recv_message()
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8", errors="replace")
                message = json.loads(raw)
                handlers: list[Any] = []
                with self._condition:
                    if "id" in message:
                        self._responses[int(message["id"])] = message
                    elif "method" in message:
                        self._events.append((time.monotonic(), message))
                        if len(self._events) > 1000:
                            self._events = self._events[-500:]
                        handlers = list(self._handlers.get(str(message["method"]), []))
                    self._condition.notify_all()
                for handler in handlers:
                    try:
                        handler(message.get("params") or {}, message)
                    except Exception:
                        continue
        except BaseException as exc:
            with self._condition:
                self._closed_error = exc
                self._condition.notify_all()
                close_handlers = list(self._close_handlers)
        for handler in close_handlers:
            try:
                handler()
            except Exception:
                continue

    def send(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        session_id: str | None = None,
        timeout: float = TIMEOUT,
    ) -> dict[str, Any]:
        if self._ws is None:
            raise CDPError("CDP connection is not open")
        params = params or {}

        with self._condition:
            self._next_id += 1
            message_id = self._next_id

        payload: dict[str, Any] = {"id": message_id, "method": method, "params": params}
        if session_id:
            payload["sessionId"] = session_id
        self._ws.send_text(json.dumps(payload))

        deadline = time.monotonic() + timeout
        with self._condition:
            while True:
                response = self._responses.pop(message_id, None)
                if response is not None:
                    break
                if self._closed_error is not None:
                    raise CDPError(str(self._closed_error))
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f"Timeout: {method}")
                self._condition.wait(timeout=remaining)

        error = response.get("error")
        if error:
            raise CDPError(error.get("message", "CDP request failed"))
        return response.get("result", {})

    def wait_for_event(
        self,
        method: str,
        timeout: float = TIMEOUT,
        session_id: str | None = None,
        since: float | None = None,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        with self._condition:
            while True:
                for index, (timestamp, message) in enumerate(self._events):
                    if message.get("method") != method:
                        continue
                    if since is not None and timestamp < since:
                        continue
                    if session_id is not None and message.get("sessionId") != session_id:
                        continue
                    self._events.pop(index)
                    return message.get("params") or {}
                if self._closed_error is not None:
                    raise CDPError(str(self._closed_error))
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f"Timeout waiting for event: {method}")
                self._condition.wait(timeout=remaining)

    def on_event(self, method: str, handler: Any) -> None:
        with self._condition:
            self._handlers.setdefault(method, []).append(handler)

    def on_close(self, handler: Any) -> None:
        with self._condition:
            self._close_handlers.append(handler)

    def close(self) -> None:
        if self._ws is None:
            return
        self._ws.close()


def get_pages(cdp: CDP) -> list[dict[str, Any]]:
    result = cdp.send("Target.getTargets")
    target_infos = result.get("targetInfos", [])
    return [page for page in target_infos if page.get("type") == "page" and not str(page.get("url", "")).startswith("chrome://")]


def format_page_list(pages: list[dict[str, Any]]) -> str:
    prefix_len = get_display_prefix_length([page["targetId"] for page in pages if page.get("targetId")])
    lines = []
    for page in pages:
        target_id = str(page.get("targetId", ""))[:prefix_len].ljust(prefix_len)
        title = str(page.get("title", ""))[:54].ljust(54)
        lines.append(f"{target_id}  {title}  {page.get('url', '')}")
    return "\n".join(lines)


def should_show_ax_node(node: dict[str, Any], compact: bool = False) -> bool:
    role = node.get("role", {}).get("value", "")
    name = node.get("name", {}).get("value", "")
    value = node.get("value", {}).get("value")
    if compact and role == "InlineTextBox":
        return False
    return role not in {"none", "generic"} and not (name == "" and (value == "" or value is None))


def format_ax_node(node: dict[str, Any], depth: int) -> str:
    role = node.get("role", {}).get("value", "")
    name = node.get("name", {}).get("value", "")
    value = node.get("value", {}).get("value")
    indent = "  " * min(depth, 10)
    line = f"{indent}[{role}]"
    if name != "":
        line += f" {name}"
    if value not in ("", None):
        line += f" = {json.dumps(value)}"
    return line


def ordered_ax_children(
    node: dict[str, Any],
    nodes_by_id: dict[Any, dict[str, Any]],
    children_by_parent: dict[Any, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    children: list[dict[str, Any]] = []
    seen: set[Any] = set()
    for child_id in node.get("childIds", []):
        child = nodes_by_id.get(child_id)
        if child and child.get("nodeId") not in seen:
            seen.add(child.get("nodeId"))
            children.append(child)
    for child in children_by_parent.get(node.get("nodeId"), []):
        if child.get("nodeId") not in seen:
            seen.add(child.get("nodeId"))
            children.append(child)
    return children


def snapshot_str(cdp: CDP, session_id: str, compact: bool = True) -> str:
    result = cdp.send("Accessibility.getFullAXTree", {}, session_id=session_id)
    nodes = result.get("nodes", [])
    nodes_by_id = {node.get("nodeId"): node for node in nodes}
    children_by_parent: dict[Any, list[dict[str, Any]]] = {}
    for node in nodes:
        parent_id = node.get("parentId")
        if parent_id is None:
            continue
        children_by_parent.setdefault(parent_id, []).append(node)

    lines: list[str] = []
    visited: set[Any] = set()

    def visit(node: dict[str, Any] | None, depth: int) -> None:
        if not node:
            return
        node_id = node.get("nodeId")
        if node_id in visited:
            return
        visited.add(node_id)
        if should_show_ax_node(node, compact=compact):
            lines.append(format_ax_node(node, depth))
        for child in ordered_ax_children(node, nodes_by_id, children_by_parent):
            visit(child, depth + 1)

    roots = [node for node in nodes if not node.get("parentId") or node.get("parentId") not in nodes_by_id]
    for root in roots:
        visit(root, 0)
    for node in nodes:
        visit(node, 0)
    return "\n".join(lines)


def remote_object_to_string(remote: dict[str, Any]) -> str:
    if "value" in remote:
        value = remote["value"]
        if isinstance(value, (dict, list)):
            return json.dumps(value, indent=2)
        return "" if value is None else str(value)
    if "unserializableValue" in remote:
        return str(remote["unserializableValue"])
    if "description" in remote:
        return str(remote["description"])
    return json.dumps(remote, indent=2)


def eval_str(cdp: CDP, session_id: str, expression: str) -> str:
    cdp.send("Runtime.enable", {}, session_id=session_id)
    result = cdp.send(
        "Runtime.evaluate",
        {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
        },
        session_id=session_id,
    )
    if result.get("exceptionDetails"):
        details = result["exceptionDetails"]
        message = details.get("text") or details.get("exception", {}).get("description") or "Runtime.evaluate failed"
        raise CDPError(message)
    return remote_object_to_string(result.get("result", {}))


def shot_str(cdp: CDP, session_id: str, file_path: str | None, target_id: str) -> str:
    dpr = 1.0
    try:
        raw_dpr = eval_str(cdp, session_id, "window.devicePixelRatio")
        parsed = float(raw_dpr)
        if parsed > 0:
            dpr = parsed
    except Exception:
        pass

    result = cdp.send("Page.captureScreenshot", {"format": "png"}, session_id=session_id)
    output = Path(file_path).expanduser() if file_path else RUNTIME_DIR / f"screenshot-{target_id[:8]}.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(base64.b64decode(result["data"]))

    lines = [str(output)]
    lines.append(f"Screenshot saved. Device pixel ratio (DPR): {dpr}")
    lines.append("Coordinate mapping:")
    lines.append(f"  Screenshot pixels -> CSS pixels (for CDP Input events): divide by {dpr}")
    lines.append(
        f"  e.g. screenshot point ({round(100 * dpr)}, {round(200 * dpr)}) -> CSS (100, 200) -> use clickxy <target> 100 200"
    )
    if dpr != 1:
        lines.append(f"  On this {dpr}x display: CSS px = screenshot px / {dpr} ~= screenshot px * {round(100 / dpr) / 100}")
    return "\n".join(lines)


def html_str(cdp: CDP, session_id: str, selector: str | None) -> str:
    expression = (
        f"document.querySelector({json.dumps(selector)})?.outerHTML || 'Element not found'"
        if selector
        else "document.documentElement.outerHTML"
    )
    return eval_str(cdp, session_id, expression)


def wait_for_document_ready(cdp: CDP, session_id: str, timeout: float = NAVIGATION_TIMEOUT) -> None:
    deadline = time.monotonic() + timeout
    last_state = ""
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            state = eval_str(cdp, session_id, "document.readyState")
            last_state = state
            if state == "complete":
                return
        except Exception as exc:
            last_error = exc
        time.sleep(0.2)

    if last_state:
        raise CLIError(f"Timed out waiting for navigation to finish (last readyState: {last_state})")
    if last_error is not None:
        raise CLIError(f"Timed out waiting for navigation to finish ({last_error})")
    raise CLIError("Timed out waiting for navigation to finish")


def nav_str(cdp: CDP, session_id: str, url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise CLIError(f"Only http/https URLs allowed, got: {url}")
    cdp.send("Page.enable", {}, session_id=session_id)
    since = time.monotonic()
    result = cdp.send("Page.navigate", {"url": url}, session_id=session_id)
    if result.get("errorText"):
        raise CLIError(str(result["errorText"]))
    if result.get("loaderId"):
        cdp.wait_for_event("Page.loadEventFired", timeout=NAVIGATION_TIMEOUT, session_id=session_id, since=since)
    wait_for_document_ready(cdp, session_id, timeout=5.0)
    return f"Navigated to {url}"


def net_str(cdp: CDP, session_id: str) -> str:
    raw = eval_str(
        cdp,
        session_id,
        """JSON.stringify(performance.getEntriesByType('resource').map(e => ({
  name: e.name.substring(0, 120),
  type: e.initiatorType,
  duration: Math.round(e.duration),
  size: e.transferSize
})))""",
    )
    entries = json.loads(raw)
    return "\n".join(
        f"{str(entry['duration']).rjust(5)}ms  {str(entry.get('size') or '?').rjust(8)}B  {str(entry['type']).ljust(8)}  {entry['name']}"
        for entry in entries
    )


def click_str(cdp: CDP, session_id: str, selector: str) -> str:
    if not selector:
        raise CLIError("CSS selector required")
    expression = f"""
(() => {{
  const el = document.querySelector({json.dumps(selector)});
  if (!el) return {{ ok: false, error: 'Element not found: ' + {json.dumps(selector)} }};
  el.scrollIntoView({{ block: 'center' }});
  const isFocusable =
    typeof el.focus === 'function' &&
    (el.matches('input, textarea, select, button, a, [tabindex], [contenteditable=""], [contenteditable="true"]') ||
     el.isContentEditable);
  if (isFocusable) el.focus({{ preventScroll: true }});
  el.click();
  return {{
    ok: true,
    tag: el.tagName,
    text: (el.textContent || '').trim().substring(0, 80),
    activeTag: document.activeElement && document.activeElement.tagName,
    focused: document.activeElement === el,
  }};
}})()
"""
    result = json.loads(eval_str(cdp, session_id, expression))
    if not result.get("ok"):
        raise CLIError(result.get("error", "Click failed"))
    suffix = " and focused it" if result.get("focused") else ""
    return f'Clicked <{result["tag"]}> "{result["text"]}"{suffix}'


def clickxy_str(cdp: CDP, session_id: str, x: str, y: str) -> str:
    try:
        css_x = float(x)
        css_y = float(y)
    except ValueError as exc:
        raise CLIError("x and y must be numbers (CSS pixels)") from exc

    base = {"x": css_x, "y": css_y, "button": "left", "clickCount": 1, "modifiers": 0}
    cdp.send("Input.dispatchMouseEvent", {**base, "type": "mouseMoved"}, session_id=session_id)
    cdp.send("Input.dispatchMouseEvent", {**base, "type": "mousePressed"}, session_id=session_id)
    time.sleep(0.05)
    cdp.send("Input.dispatchMouseEvent", {**base, "type": "mouseReleased"}, session_id=session_id)
    return f"Clicked at CSS ({css_x}, {css_y})"


def type_str(cdp: CDP, session_id: str, text: str) -> str:
    if not text:
        raise CLIError("text required")
    cdp.send("Input.insertText", {"text": text}, session_id=session_id)
    return f"Typed {len(text)} characters"


def loadall_str(cdp: CDP, session_id: str, selector: str, interval_ms: int = 1500) -> str:
    if not selector:
        raise CLIError("CSS selector required")
    clicks = 0
    deadline = time.monotonic() + 5 * 60.0
    while time.monotonic() < deadline:
        exists_expression = f"""
(() => {{
  const el = document.querySelector({json.dumps(selector)});
  if (!el) return false;
  const visible = !el.hidden && !el.disabled && el.getClientRects().length > 0;
  return visible;
}})()
"""
        exists = eval_str(cdp, session_id, exists_expression).strip().lower()
        if exists != "true":
            break
        click_expression = f"""
(() => {{
  const el = document.querySelector({json.dumps(selector)});
  if (!el || el.hidden || el.disabled || el.getClientRects().length === 0) return false;
  el.scrollIntoView({{ block: 'center' }});
  el.click();
  return true;
}})()
"""
        clicked = eval_str(cdp, session_id, click_expression).strip().lower()
        if clicked != "true":
            break
        clicks += 1
        time.sleep(interval_ms / 1000.0)
    return f'Clicked "{selector}" {clicks} time(s) until it disappeared'


def evalraw_str(cdp: CDP, session_id: str, method: str, params_json: str | None) -> str:
    if not method:
        raise CLIError('CDP method required (for example "DOM.getDocument")')
    params: dict[str, Any] = {}
    if params_json:
        try:
            params = json.loads(params_json)
        except json.JSONDecodeError as exc:
            raise CLIError(f"Invalid JSON params: {params_json}") from exc
    result = cdp.send(method, params, session_id=session_id)
    return json.dumps(result, indent=2)


def wait_str(cdp: CDP, session_id: str, args: list[str]) -> str:
    timeout_ms = 10000
    gone = False
    idle = False
    selector: str | None = None

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--gone":
            gone = True
        elif arg == "--idle":
            idle = True
        elif arg == "--timeout":
            i += 1
            if i >= len(args):
                raise CLIError("--timeout requires a value in ms")
            timeout_ms = int(args[i])
        elif selector is None:
            selector = arg
        i += 1

    timeout_s = timeout_ms / 1000.0
    deadline = time.monotonic() + timeout_s

    if idle:
        # Wait for network idle: no pending requests for 500ms
        expression = """
(() => {
  const entries = performance.getEntriesByType('resource');
  const recent = entries.filter(e => (performance.now() - (e.startTime + e.duration)) < 500);
  return recent.length === 0;
})()
"""
        while time.monotonic() < deadline:
            try:
                result = eval_str(cdp, session_id, expression)
                if result.strip().lower() == "true":
                    return "Network is idle"
            except Exception:
                pass
            time.sleep(0.2)
        raise CLIError(f"Timeout ({timeout_ms}ms): network did not become idle")

    if not selector:
        raise CLIError("Selector required (or use --idle)")

    check = f"!!document.querySelector({json.dumps(selector)})"
    while time.monotonic() < deadline:
        try:
            result = eval_str(cdp, session_id, check)
            exists = result.strip().lower() == "true"
            if gone and not exists:
                return f'Element "{selector}" is gone'
            if not gone and exists:
                return f'Element "{selector}" found'
        except Exception:
            pass
        time.sleep(0.15)

    if gone:
        raise CLIError(f'Timeout ({timeout_ms}ms): "{selector}" still present')
    raise CLIError(f'Timeout ({timeout_ms}ms): "{selector}" not found')


def scroll_str(cdp: CDP, session_id: str, args: list[str]) -> str:
    selector: str | None = None
    direction = "down"
    amount: int | None = None

    # Parse: [selector] <direction> [amount]
    # direction is one of: up, down, left, right, top, bottom
    directions = {"up", "down", "left", "right", "top", "bottom"}
    remaining = list(args)
    for i, arg in enumerate(remaining):
        if arg in directions:
            direction = arg
            # Everything before is the selector
            if i > 0:
                selector = " ".join(remaining[:i])
            # Next arg (if any) is the amount
            if i + 1 < len(remaining):
                try:
                    amount = int(remaining[i + 1])
                except ValueError:
                    raise CLIError(f"Invalid scroll amount: {remaining[i + 1]}")
            break
    else:
        # No direction found; treat all args as selector + default direction
        if remaining:
            raise CLIError("Direction required (up/down/left/right/top/bottom)")

    if direction == "top":
        scroll_js = "el.scrollTo({top: 0, behavior: 'instant'})"
    elif direction == "bottom":
        scroll_js = "el.scrollTo({top: el.scrollHeight, behavior: 'instant'})"
    elif direction == "up":
        px = amount if amount is not None else "Math.round(el.clientHeight * 0.85)"
        scroll_js = f"el.scrollBy({{top: -({px}), behavior: 'instant'}})"
    elif direction == "down":
        px = amount if amount is not None else "Math.round(el.clientHeight * 0.85)"
        scroll_js = f"el.scrollBy({{top: {px}, behavior: 'instant'}})"
    elif direction == "left":
        px = amount if amount is not None else "Math.round(el.clientWidth * 0.85)"
        scroll_js = f"el.scrollBy({{left: -({px}), behavior: 'instant'}})"
    elif direction == "right":
        px = amount if amount is not None else "Math.round(el.clientWidth * 0.85)"
        scroll_js = f"el.scrollBy({{left: {px}, behavior: 'instant'}})"
    else:
        scroll_js = ""

    if selector:
        expression = f"""
(() => {{
  const el = document.querySelector({json.dumps(selector)});
  if (!el) return JSON.stringify({{ok: false, error: 'Element not found: ' + {json.dumps(selector)}}});
  {scroll_js};
  return JSON.stringify({{ok: true, scrollTop: Math.round(el.scrollTop), scrollLeft: Math.round(el.scrollLeft), scrollHeight: el.scrollHeight}});
}})()
"""
    else:
        # Use documentElement as the scroll target
        expression = f"""
(() => {{
  const el = document.documentElement;
  {scroll_js};
  return JSON.stringify({{ok: true, scrollTop: Math.round(el.scrollTop || window.scrollY), scrollLeft: Math.round(el.scrollLeft || window.scrollX), scrollHeight: el.scrollHeight}});
}})()
"""
    raw = eval_str(cdp, session_id, expression)
    result = json.loads(raw)
    if not result.get("ok"):
        raise CLIError(result.get("error", "Scroll failed"))
    target = f'"{selector}"' if selector else "page"
    return f"Scrolled {target} {direction}. scrollTop={result['scrollTop']} scrollHeight={result['scrollHeight']}"


KEY_DEFINITIONS: dict[str, dict[str, str | int]] = {
    "Enter":      {"key": "Enter", "code": "Enter", "keyCode": 13, "which": 13, "text": "\r"},
    "Tab":        {"key": "Tab", "code": "Tab", "keyCode": 9, "which": 9},
    "Escape":     {"key": "Escape", "code": "Escape", "keyCode": 27, "which": 27},
    "Backspace":  {"key": "Backspace", "code": "Backspace", "keyCode": 8, "which": 8},
    "Delete":     {"key": "Delete", "code": "Delete", "keyCode": 46, "which": 46},
    "ArrowUp":    {"key": "ArrowUp", "code": "ArrowUp", "keyCode": 38, "which": 38},
    "ArrowDown":  {"key": "ArrowDown", "code": "ArrowDown", "keyCode": 40, "which": 40},
    "ArrowLeft":  {"key": "ArrowLeft", "code": "ArrowLeft", "keyCode": 37, "which": 37},
    "ArrowRight": {"key": "ArrowRight", "code": "ArrowRight", "keyCode": 39, "which": 39},
    "Home":       {"key": "Home", "code": "Home", "keyCode": 36, "which": 36},
    "End":        {"key": "End", "code": "End", "keyCode": 35, "which": 35},
    "PageUp":     {"key": "PageUp", "code": "PageUp", "keyCode": 33, "which": 33},
    "PageDown":   {"key": "PageDown", "code": "PageDown", "keyCode": 34, "which": 34},
    "Space":      {"key": " ", "code": "Space", "keyCode": 32, "which": 32, "text": " "},
}

MODIFIER_FLAGS = {"alt": 1, "ctrl": 2, "control": 2, "meta": 4, "cmd": 4, "command": 4, "shift": 8}


def press_str(cdp: CDP, session_id: str, args: list[str]) -> str:
    if not args:
        raise CLIError("Key name required (e.g. Enter, Tab, Escape, a, ArrowDown)")

    key_name = args[0]
    modifiers = 0
    for arg in args[1:]:
        flag = MODIFIER_FLAGS.get(arg.lower().lstrip("-"))
        if flag:
            modifiers |= flag
        else:
            raise CLIError(f"Unknown modifier: {arg}. Use: alt, ctrl, meta/cmd, shift")

    key_def = KEY_DEFINITIONS.get(key_name)
    if key_def:
        key_str = str(key_def["key"])
        code = str(key_def["code"])
        key_code = int(key_def.get("keyCode", 0))
        text = str(key_def.get("text", ""))
    elif len(key_name) == 1:
        # Single character
        key_str = key_name
        code = f"Key{key_name.upper()}" if key_name.isalpha() else ""
        key_code = ord(key_name.upper()) if key_name.isalpha() else ord(key_name)
        text = key_name
    else:
        raise CLIError(f'Unknown key: "{key_name}". Use a single character or a named key (Enter, Tab, Escape, ArrowDown, etc.)')

    down: dict[str, Any] = {
        "type": "keyDown",
        "key": key_str,
        "modifiers": modifiers,
        "windowsVirtualKeyCode": key_code,
        "nativeVirtualKeyCode": key_code,
    }
    if code:
        down["code"] = code
    if text and modifiers == 0:
        down["text"] = text
        down["unmodifiedText"] = text

    up: dict[str, Any] = {
        "type": "keyUp",
        "key": key_str,
        "modifiers": modifiers,
        "windowsVirtualKeyCode": key_code,
        "nativeVirtualKeyCode": key_code,
    }
    if code:
        up["code"] = code

    cdp.send("Input.dispatchKeyEvent", down, session_id=session_id)
    time.sleep(0.02)
    cdp.send("Input.dispatchKeyEvent", up, session_id=session_id)

    mod_parts = []
    if modifiers & 2:
        mod_parts.append("Ctrl")
    if modifiers & 1:
        mod_parts.append("Alt")
    if modifiers & 8:
        mod_parts.append("Shift")
    if modifiers & 4:
        mod_parts.append("Meta")
    combo = "+".join(mod_parts + [key_name]) if mod_parts else key_name
    return f"Pressed {combo}"


def fill_str(cdp: CDP, session_id: str, selector: str, text: str) -> str:
    if not selector:
        raise CLIError("CSS selector required")
    # Click and focus the element
    focus_expression = f"""
(() => {{
  const el = document.querySelector({json.dumps(selector)});
  if (!el) return JSON.stringify({{ok: false, error: 'Element not found: ' + {json.dumps(selector)}}});
  el.scrollIntoView({{block: 'center'}});
  el.focus({{preventScroll: true}});
  el.click();
  return JSON.stringify({{ok: true, tag: el.tagName, focused: document.activeElement === el}});
}})()
"""
    result = json.loads(eval_str(cdp, session_id, focus_expression))
    if not result.get("ok"):
        raise CLIError(result.get("error", "Focus failed"))

    # Select all existing text (Ctrl+A / Cmd+A)
    cdp.send("Input.dispatchKeyEvent", {
        "type": "keyDown", "key": "a", "code": "KeyA",
        "modifiers": 4 if sys.platform == "darwin" else 2,
        "windowsVirtualKeyCode": 65,
    }, session_id=session_id)
    cdp.send("Input.dispatchKeyEvent", {
        "type": "keyUp", "key": "a", "code": "KeyA",
        "modifiers": 4 if sys.platform == "darwin" else 2,
        "windowsVirtualKeyCode": 65,
    }, session_id=session_id)
    time.sleep(0.02)

    # Delete selected text
    cdp.send("Input.dispatchKeyEvent", {
        "type": "keyDown", "key": "Backspace", "code": "Backspace",
        "windowsVirtualKeyCode": 8,
    }, session_id=session_id)
    cdp.send("Input.dispatchKeyEvent", {
        "type": "keyUp", "key": "Backspace", "code": "Backspace",
        "windowsVirtualKeyCode": 8,
    }, session_id=session_id)
    time.sleep(0.02)

    # Type new text
    cdp.send("Input.insertText", {"text": text}, session_id=session_id)
    return f'Filled <{result["tag"]}> with {len(text)} characters'


def hover_str(cdp: CDP, session_id: str, args: list[str]) -> str:
    if not args:
        raise CLIError("CSS selector or coordinates (x y) required")

    # Check if it's coordinate-based (two numeric args)
    if len(args) >= 2:
        try:
            css_x = float(args[0])
            css_y = float(args[1])
            cdp.send("Input.dispatchMouseEvent", {
                "type": "mouseMoved", "x": css_x, "y": css_y,
            }, session_id=session_id)
            return f"Hovered at CSS ({css_x}, {css_y})"
        except ValueError:
            pass

    # Selector-based
    selector = " ".join(args)
    expression = f"""
(() => {{
  const el = document.querySelector({json.dumps(selector)});
  if (!el) return JSON.stringify({{ok: false, error: 'Element not found: ' + {json.dumps(selector)}}});
  el.scrollIntoView({{block: 'center'}});
  const rect = el.getBoundingClientRect();
  const x = rect.left + rect.width / 2;
  const y = rect.top + rect.height / 2;
  return JSON.stringify({{ok: true, x: Math.round(x), y: Math.round(y), tag: el.tagName}});
}})()
"""
    result = json.loads(eval_str(cdp, session_id, expression))
    if not result.get("ok"):
        raise CLIError(result.get("error", "Hover failed"))

    cdp.send("Input.dispatchMouseEvent", {
        "type": "mouseMoved", "x": result["x"], "y": result["y"],
    }, session_id=session_id)
    return f'Hovered <{result["tag"]}> at ({result["x"]}, {result["y"]})'


def select_str(cdp: CDP, session_id: str, selector: str, value: str) -> str:
    if not selector:
        raise CLIError("CSS selector required")
    if not value:
        raise CLIError("Value required")
    expression = f"""
(() => {{
  const el = document.querySelector({json.dumps(selector)});
  if (!el) return JSON.stringify({{ok: false, error: 'Element not found: ' + {json.dumps(selector)}}});
  if (el.tagName !== 'SELECT') return JSON.stringify({{ok: false, error: 'Element is <' + el.tagName + '>, not <SELECT>'}});
  const opt = Array.from(el.options).find(o => o.value === {json.dumps(value)} || o.textContent.trim() === {json.dumps(value)});
  if (!opt) return JSON.stringify({{ok: false, error: 'No option matching: ' + {json.dumps(value)}}});
  el.value = opt.value;
  el.dispatchEvent(new Event('input', {{bubbles: true}}));
  el.dispatchEvent(new Event('change', {{bubbles: true}}));
  return JSON.stringify({{ok: true, selected: opt.value, text: opt.textContent.trim()}});
}})()
"""
    result = json.loads(eval_str(cdp, session_id, expression))
    if not result.get("ok"):
        raise CLIError(result.get("error", "Select failed"))
    return f'Selected "{result["text"]}" (value={result["selected"]})'


def cookies_str(cdp: CDP, session_id: str, args: list[str]) -> str:
    if not args or args[0] not in ("--set", "--clear"):
        # List cookies
        result = cdp.send("Network.getCookies", {}, session_id=session_id)
        cookies = result.get("cookies", [])
        if not cookies:
            return "No cookies"
        lines = []
        for c in cookies:
            secure = " Secure" if c.get("secure") else ""
            httponly = " HttpOnly" if c.get("httpOnly") else ""
            lines.append(f'{c["name"]}={str(c.get("value", ""))[:60]}  (domain={c.get("domain", "")}{secure}{httponly})')
        return "\n".join(lines)

    if args[0] == "--clear":
        cdp.send("Network.clearBrowserCookies", {}, session_id=session_id)
        return "Cookies cleared"

    if args[0] == "--set":
        if len(args) < 2:
            raise CLIError("Cookie value required: --set name=value")
        cookie_str = args[1]
        if "=" not in cookie_str:
            raise CLIError("Cookie format: name=value")
        name, value = cookie_str.split("=", 1)
        # Get current page URL for domain
        url = eval_str(cdp, session_id, "window.location.href")
        cdp.send("Network.setCookie", {"name": name, "value": value, "url": url}, session_id=session_id)
        return f'Set cookie {name}={value[:40]}'

    return ""


def storage_str(cdp: CDP, session_id: str, args: list[str]) -> str:
    use_session = "--session" in args
    set_kv: str | None = None
    for i, arg in enumerate(args):
        if arg == "--set" and i + 1 < len(args):
            set_kv = args[i + 1]

    storage_name = "sessionStorage" if use_session else "localStorage"

    if set_kv:
        if "=" not in set_kv:
            raise CLIError("Format: --set key=value")
        key, value = set_kv.split("=", 1)
        expression = f"{storage_name}.setItem({json.dumps(key)}, {json.dumps(value)})"
        eval_str(cdp, session_id, expression)
        return f"Set {storage_name}.{key}={value[:40]}"

    expression = f"JSON.stringify(Object.fromEntries(Object.entries({storage_name})))"
    raw = eval_str(cdp, session_id, expression)
    data = json.loads(raw)
    if not data:
        return f"{storage_name} is empty"
    lines = []
    for key, value in data.items():
        lines.append(f"  {key}={str(value)[:80]}")
    return f"{storage_name} ({len(data)} items):\n" + "\n".join(lines)


def pdf_str(cdp: CDP, session_id: str, file_path: str | None, target_id: str) -> str:
    result = cdp.send("Page.printToPDF", {
        "printBackground": True,
        "preferCSSPageSize": True,
    }, session_id=session_id)
    output = Path(file_path).expanduser() if file_path else RUNTIME_DIR / f"page-{target_id[:8]}.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(base64.b64decode(result["data"]))
    return f"PDF saved: {output}"


def shot_full_str(cdp: CDP, session_id: str, file_path: str | None, target_id: str) -> str:
    """Full-page screenshot using layout metrics."""
    dpr = 1.0
    try:
        raw_dpr = eval_str(cdp, session_id, "window.devicePixelRatio")
        parsed = float(raw_dpr)
        if parsed > 0:
            dpr = parsed
    except Exception:
        pass

    # Get full page dimensions
    metrics = cdp.send("Page.getLayoutMetrics", {}, session_id=session_id)
    content = metrics.get("contentSize") or metrics.get("cssContentSize", {})
    width = content.get("width", 1280)
    height = content.get("height", 800)

    result = cdp.send("Page.captureScreenshot", {
        "format": "png",
        "captureBeyondViewport": True,
        "clip": {"x": 0, "y": 0, "width": width, "height": height, "scale": 1},
    }, session_id=session_id)

    output = Path(file_path).expanduser() if file_path else RUNTIME_DIR / f"screenshot-full-{target_id[:8]}.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(base64.b64decode(result["data"]))

    return f"{output}\nFull-page screenshot saved ({width}x{height} CSS pixels, DPR={dpr})"


def daemon_request(command: str, args: list[str]) -> dict[str, Any]:
    return {"cmd": command, "args": args}


def run_daemon(target_id: str) -> None:
    cdp = CDP()
    try:
        cdp.connect(get_ws_url())
    except Exception as exc:
        print(f"Daemon: cannot connect to Chrome: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    try:
        session_id = cdp.send("Target.attachToTarget", {"targetId": target_id, "flatten": True}).get("sessionId")
    except Exception as exc:
        print(f"Daemon: attach failed: {exc}", file=sys.stderr)
        cdp.close()
        raise SystemExit(1) from exc

    if not session_id:
        print("Daemon: attach failed: no session ID returned", file=sys.stderr)
        cdp.close()
        raise SystemExit(1)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen()
    server.settimeout(1.0)

    meta_path = daemon_meta_path(target_id)
    token = secrets.token_hex(16)
    secure_write_json(
        meta_path,
        {
            "host": "127.0.0.1",
            "port": server.getsockname()[1],
            "token": token,
            "pid": os.getpid(),
        },
    )

    stop_event = threading.Event()
    idle_deadline = time.monotonic() + IDLE_TIMEOUT

    def shutdown() -> None:
        if stop_event.is_set():
            return
        stop_event.set()
        safe_unlink(meta_path)
        try:
            server.close()
        except OSError:
            pass
        try:
            cdp.close()
        except Exception:
            pass

    def on_target_destroyed(params: dict[str, Any], _: dict[str, Any]) -> None:
        if params.get("targetId") == target_id:
            shutdown()

    def on_detached(params: dict[str, Any], _: dict[str, Any]) -> None:
        if params.get("sessionId") == session_id:
            shutdown()

    cdp.on_event("Target.targetDestroyed", on_target_destroyed)
    cdp.on_event("Target.detachedFromTarget", on_detached)
    cdp.on_close(shutdown)

    def signal_handler(*_: Any) -> None:
        shutdown()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, signal_handler)
        except (OSError, ValueError):
            pass

    def handle_command(req: dict[str, Any]) -> dict[str, Any]:
        nonlocal idle_deadline
        idle_deadline = time.monotonic() + IDLE_TIMEOUT
        cmd = str(req.get("cmd", ""))
        args = list(req.get("args") or [])
        try:
            if cmd in {"list", "ls"}:
                return {"ok": True, "result": format_page_list(get_pages(cdp))}
            if cmd == "list_raw":
                return {"ok": True, "result": json.dumps(get_pages(cdp))}
            if cmd in {"snap", "snapshot"}:
                compact = "--full" not in args
                return {"ok": True, "result": snapshot_str(cdp, session_id, compact=compact)}
            if cmd in {"eval"}:
                return {"ok": True, "result": eval_str(cdp, session_id, args[0])}
            if cmd in {"shot", "screenshot"}:
                full = "--full" in args
                if full:
                    return {"ok": True, "result": shot_full_str(cdp, session_id, args[0] if args and args[0] != "--full" else None, target_id)}
                return {"ok": True, "result": shot_str(cdp, session_id, args[0] if args else None, target_id)}
            if cmd == "html":
                return {"ok": True, "result": html_str(cdp, session_id, args[0] if args else None)}
            if cmd in {"nav", "navigate"}:
                return {"ok": True, "result": nav_str(cdp, session_id, args[0])}
            if cmd in {"net", "network"}:
                return {"ok": True, "result": net_str(cdp, session_id)}
            if cmd == "click":
                return {"ok": True, "result": click_str(cdp, session_id, args[0])}
            if cmd == "clickxy":
                return {"ok": True, "result": clickxy_str(cdp, session_id, args[0], args[1])}
            if cmd == "type":
                return {"ok": True, "result": type_str(cdp, session_id, args[0])}
            if cmd == "loadall":
                interval = int(args[1]) if len(args) > 1 else 1500
                return {"ok": True, "result": loadall_str(cdp, session_id, args[0], interval)}
            if cmd == "evalraw":
                return {"ok": True, "result": evalraw_str(cdp, session_id, args[0], args[1] if len(args) > 1 else None)}
            if cmd == "wait":
                return {"ok": True, "result": wait_str(cdp, session_id, args)}
            if cmd == "scroll":
                return {"ok": True, "result": scroll_str(cdp, session_id, args)}
            if cmd == "press":
                return {"ok": True, "result": press_str(cdp, session_id, args)}
            if cmd == "fill":
                if len(args) < 2:
                    return {"ok": False, "error": "fill requires selector and text"}
                return {"ok": True, "result": fill_str(cdp, session_id, args[0], " ".join(args[1:]))}
            if cmd == "hover":
                return {"ok": True, "result": hover_str(cdp, session_id, args)}
            if cmd == "select":
                if len(args) < 2:
                    return {"ok": False, "error": "select requires selector and value"}
                return {"ok": True, "result": select_str(cdp, session_id, args[0], " ".join(args[1:]))}
            if cmd == "cookies":
                return {"ok": True, "result": cookies_str(cdp, session_id, args)}
            if cmd == "storage":
                return {"ok": True, "result": storage_str(cdp, session_id, args)}
            if cmd == "pdf":
                return {"ok": True, "result": pdf_str(cdp, session_id, args[0] if args else None, target_id)}
            if cmd == "stop":
                return {"ok": True, "result": "", "stopAfter": True}
            return {"ok": False, "error": f"Unknown command: {cmd}"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    try:
        while not stop_event.is_set():
            if time.monotonic() >= idle_deadline:
                shutdown()
                break
            try:
                conn, _ = server.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            with conn:
                conn.settimeout(TIMEOUT)
                buffer = ""
                while not stop_event.is_set():
                    try:
                        chunk = conn.recv(4096)
                    except socket.timeout:
                        continue
                    if not chunk:
                        break
                    buffer += chunk.decode("utf-8")
                    if "\n" not in buffer:
                        continue
                    lines = buffer.split("\n")
                    buffer = lines.pop()
                    for line in lines:
                        if not line.strip():
                            continue
                        try:
                            request = json.loads(line)
                        except json.JSONDecodeError:
                            response = {"id": None, "ok": False, "error": "Invalid JSON request"}
                            conn.sendall((json.dumps(response) + "\n").encode("utf-8"))
                            continue
                        if request.get("token") != token:
                            response = {"id": request.get("id"), "ok": False, "error": "Unauthorized daemon request"}
                            conn.sendall((json.dumps(response) + "\n").encode("utf-8"))
                            continue
                        response = {"id": request.get("id")}
                        response.update(handle_command(request))
                        conn.sendall((json.dumps(response) + "\n").encode("utf-8"))
                        if response.get("stopAfter"):
                            shutdown()
                            return
                        break
                    break
    finally:
        shutdown()


def spawn_daemon(target_id: str) -> None:
    args = [sys.executable, str(Path(__file__).resolve()), "_daemon", target_id]
    kwargs: dict[str, Any] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if IS_WINDOWS:
        creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        kwargs["creationflags"] = creationflags
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(args, **kwargs)


def connect_to_daemon(meta: dict[str, Any]) -> socket.socket:
    host = str(meta["host"])
    port = int(meta["port"])
    conn = socket.create_connection((host, port), timeout=TIMEOUT)
    conn.settimeout(None)
    return conn


def get_or_start_tab_daemon(target_id: str) -> tuple[socket.socket, dict[str, Any]]:
    meta_path = daemon_meta_path(target_id)
    if meta_path.exists():
        try:
            meta = read_json(meta_path)
            return connect_to_daemon(meta), meta
        except Exception:
            safe_unlink(meta_path)

    spawn_daemon(target_id)
    for _ in range(DAEMON_CONNECT_RETRIES):
        time.sleep(DAEMON_CONNECT_DELAY)
        if not meta_path.exists():
            continue
        try:
            meta = read_json(meta_path)
            return connect_to_daemon(meta), meta
        except Exception:
            continue
    raise CLIError('Daemon failed to start - did you click Allow in Chrome?')


def send_command(conn: socket.socket, meta: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    payload = dict(request)
    payload["id"] = 1
    payload["token"] = meta["token"]
    conn.sendall((json.dumps(payload) + "\n").encode("utf-8"))

    buffer = ""
    while True:
        chunk = conn.recv(4096)
        if not chunk:
            raise CLIError("Connection closed before response")
        buffer += chunk.decode("utf-8")
        if "\n" not in buffer:
            continue
        line, _rest = buffer.split("\n", 1)
        return json.loads(line)


def live_pages() -> list[dict[str, Any]]:
    cdp = CDP()
    cdp.connect(get_ws_url())
    try:
        return get_pages(cdp)
    finally:
        cdp.close()


def write_pages_cache(pages: list[dict[str, Any]]) -> None:
    secure_write_json(PAGES_CACHE, pages)


def stop_daemons(target_prefix: str | None) -> None:
    targets: list[str]
    if target_prefix:
        candidate_targets: list[str] = []
        if PAGES_CACHE.exists():
            candidate_targets.extend(page["targetId"] for page in read_json(PAGES_CACHE))
        candidate_targets.extend(path.stem.removeprefix("cdp-") for path in RUNTIME_DIR.glob("cdp-*.json"))
        if not candidate_targets:
            return
        targets = [resolve_prefix(target_prefix, sorted(set(candidate_targets)), "target")]
    else:
        targets = [path.stem.removeprefix("cdp-") for path in RUNTIME_DIR.glob("cdp-*.json")]

    for target_id in targets:
        meta_path = daemon_meta_path(target_id)
        if not meta_path.exists():
            continue
        try:
            meta = read_json(meta_path)
            with connect_to_daemon(meta) as conn:
                send_command(conn, meta, daemon_request("stop", []))
        except Exception:
            safe_unlink(meta_path)


USAGE = """cdp.py - lightweight Chrome DevTools Protocol CLI in Python

Usage: python3 scripts/cdp.py <command> [args]

  list                              List open pages (shows unique target prefixes)
  snap  <target> [--full]           Accessibility tree snapshot (compact by default)
  eval  <target> <expr>             Evaluate a JavaScript expression
  shot  <target> [--full] [file]    Screenshot (viewport or --full page)
  html  <target> [selector]         Get full page HTML or element HTML
  nav   <target> <url>              Navigate to URL and wait for load completion
  net   <target>                    Network performance entries
  click   <target> <selector>       Click an element by CSS selector
  clickxy <target> <x> <y>          Click at CSS pixel coordinates
  type    <target> <text>           Type text at current focus via Input.insertText
  press   <target> <key> [mod...]   Dispatch key event (Enter, Tab, Escape, a, ...)
  fill    <target> <selector> <txt> Focus, clear, then type into an input field
  hover   <target> <sel|x y>        Hover over element or coordinates
  scroll  <target> [sel] <dir> [px] Scroll page or container (up/down/left/right/top/bottom)
  wait    <target> <sel> [opts]     Wait for element (--gone, --idle, --timeout ms)
  select  <target> <selector> <val> Select an option in a <select> dropdown
  cookies <target> [--set k=v|--clear]  List, set, or clear cookies
  storage <target> [--session] [--set k=v]  Read/write localStorage or sessionStorage
  pdf     <target> [file]           Save page as PDF
  loadall <target> <selector> [ms]  Click a "load more" selector until it disappears
  evalraw <target> <method> [json]  Send a raw CDP command; returns JSON result
  open  [url]                       Open a new tab (default: about:blank)
  stop  [target]                    Stop daemon(s)

<target> is a unique targetId prefix from "list". If a prefix is ambiguous,
use more characters.

Coordinate note:
  shot captures the viewport at the device's native resolution.
  Screenshot image size = CSS pixels * DPR.
  For CDP Input events (clickxy, etc.), use CSS pixels, not image pixels.
"""

NEEDS_TARGET = {
    "snap",
    "snapshot",
    "eval",
    "shot",
    "screenshot",
    "html",
    "nav",
    "navigate",
    "net",
    "network",
    "click",
    "clickxy",
    "type",
    "press",
    "fill",
    "hover",
    "scroll",
    "wait",
    "select",
    "cookies",
    "storage",
    "pdf",
    "loadall",
    "evalraw",
}


def read_cached_pages() -> list[dict[str, Any]]:
    if not PAGES_CACHE.exists():
        raise CLIError('No page list cached. Run "python3 scripts/cdp.py list" first.')
    return read_json(PAGES_CACHE)


def main(argv: list[str]) -> int:
    if not argv or argv[0] in {"help", "--help", "-h"}:
        print(USAGE)
        return 0

    cmd, *args = argv

    if cmd == "_daemon":
        if not args:
            raise CLIError("Missing target ID for daemon mode")
        run_daemon(args[0])
        return 0

    if cmd in {"list", "ls"}:
        pages = live_pages()
        write_pages_cache(pages)
        print(format_page_list(pages))
        return 0

    if cmd == "open":
        url = args[0] if args else "about:blank"
        cdp = CDP()
        cdp.connect(get_ws_url())
        try:
            target_id = cdp.send("Target.createTarget", {"url": url}).get("targetId")
            pages = get_pages(cdp)
            if target_id and not any(page.get("targetId") == target_id for page in pages):
                pages.append({"targetId": target_id, "title": url, "url": url})
            write_pages_cache(pages)
        finally:
            cdp.close()
        short_id = target_id[:8] if target_id else "unknown"
        print(f"Opened new tab: {short_id}  {url}")
        print('Note: this tab will need "Allow debugging?" approval on first access.')
        return 0

    if cmd == "stop":
        stop_daemons(args[0] if args else None)
        return 0

    if cmd not in NEEDS_TARGET:
        print(f"Unknown command: {cmd}\n", file=sys.stderr)
        print(USAGE)
        return 1

    if not args:
        raise CLIError('Target ID required. Run "python3 scripts/cdp.py list" first.')

    target_prefix = args[0]
    pages = read_cached_pages()
    target_id = resolve_prefix(
        target_prefix,
        [page["targetId"] for page in pages if page.get("targetId")],
        "target",
        'Run "python3 scripts/cdp.py list".',
    )

    with connect_to_daemon_context(target_id) as (conn, meta):
        if cmd in {"snap", "snapshot"}:
            full = any(arg == "--full" for arg in args[1:])
            response = send_command(conn, meta, daemon_request(cmd, ["--full"] if full else []))
        elif cmd == "eval":
            expression = " ".join(args[1:]).strip()
            if not expression:
                raise CLIError("Expression required")
            response = send_command(conn, meta, daemon_request(cmd, [expression]))
        elif cmd == "shot":
            shot_args = list(args[1:])
            response = send_command(conn, meta, daemon_request(cmd, shot_args))
        elif cmd == "html":
            selector = " ".join(args[1:]).strip()
            response = send_command(conn, meta, daemon_request(cmd, [selector] if selector else []))
        elif cmd in {"nav", "navigate"}:
            if len(args) < 2:
                raise CLIError("URL required")
            response = send_command(conn, meta, daemon_request(cmd, [args[1]]))
        elif cmd in {"net", "network"}:
            response = send_command(conn, meta, daemon_request(cmd, []))
        elif cmd == "click":
            selector = " ".join(args[1:]).strip()
            if not selector:
                raise CLIError("CSS selector required")
            response = send_command(conn, meta, daemon_request(cmd, [selector]))
        elif cmd == "clickxy":
            if len(args) < 3:
                raise CLIError("x and y required")
            response = send_command(conn, meta, daemon_request(cmd, [args[1], args[2]]))
        elif cmd == "type":
            text = " ".join(args[1:]).strip()
            if not text:
                raise CLIError("Text required")
            response = send_command(conn, meta, daemon_request(cmd, [text]))
        elif cmd == "press":
            if not args[1:]:
                raise CLIError("Key name required (e.g. Enter, Tab, Escape)")
            response = send_command(conn, meta, daemon_request(cmd, list(args[1:])))
        elif cmd == "fill":
            if len(args) < 3:
                raise CLIError("Selector and text required")
            response = send_command(conn, meta, daemon_request(cmd, [args[1], " ".join(args[2:])]))
        elif cmd == "hover":
            if not args[1:]:
                raise CLIError("CSS selector or coordinates required")
            response = send_command(conn, meta, daemon_request(cmd, list(args[1:])))
        elif cmd == "scroll":
            if not args[1:]:
                raise CLIError("Direction required (up/down/left/right/top/bottom)")
            response = send_command(conn, meta, daemon_request(cmd, list(args[1:])))
        elif cmd == "wait":
            if not args[1:]:
                raise CLIError("Selector or --idle required")
            response = send_command(conn, meta, daemon_request(cmd, list(args[1:])))
        elif cmd == "select":
            if len(args) < 3:
                raise CLIError("Selector and value required")
            response = send_command(conn, meta, daemon_request(cmd, [args[1], " ".join(args[2:])]))
        elif cmd == "cookies":
            response = send_command(conn, meta, daemon_request(cmd, list(args[1:])))
        elif cmd == "storage":
            response = send_command(conn, meta, daemon_request(cmd, list(args[1:])))
        elif cmd == "pdf":
            response = send_command(conn, meta, daemon_request(cmd, list(args[1:])))
        elif cmd == "loadall":
            if len(args) < 2:
                raise CLIError("CSS selector required")
            selector = args[1]
            extra = [selector]
            if len(args) > 2:
                extra.append(args[2])
            response = send_command(conn, meta, daemon_request(cmd, extra))
        elif cmd == "evalraw":
            if len(args) < 2:
                raise CLIError("CDP method required")
            method = args[1]
            params_json = " ".join(args[2:]).strip()
            payload = [method]
            if params_json:
                payload.append(params_json)
            response = send_command(conn, meta, daemon_request(cmd, payload))
        else:
            raise CLIError(f"Unknown command: {cmd}")

    if response.get("ok"):
        if response.get("result"):
            print(response["result"])
        return 0

    raise CLIError(str(response.get("error", "Daemon command failed")))


class connect_to_daemon_context:
    def __init__(self, target_id: str) -> None:
        self.target_id = target_id
        self.conn: socket.socket | None = None
        self.meta: dict[str, Any] | None = None

    def __enter__(self) -> tuple[socket.socket, dict[str, Any]]:
        self.conn, self.meta = get_or_start_tab_daemon(self.target_id)
        return self.conn, self.meta

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self.conn is not None:
            try:
                self.conn.close()
            except OSError:
                pass


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except CLIError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
