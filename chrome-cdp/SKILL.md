---
name: chrome-cdp
description: Interact with a local Chrome browser session using a Python Chrome DevTools Protocol CLI; use when the user asks to inspect, debug, or interact with tabs already open in Chrome, Chromium, Brave, Edge, or Vivaldi, and only after explicit user approval.
---

# Chrome CDP

Lightweight Chrome DevTools Protocol CLI implemented in Python. It talks directly to Chrome's remote debugging WebSocket, avoids browser automation frameworks, and keeps a per-tab background daemon alive so Chrome's "Allow debugging" prompt is usually a one-time approval per tab.

## Prerequisites

- Chrome, Chromium, Brave, Edge, or Vivaldi with remote debugging enabled:
  open `chrome://inspect/#remote-debugging` and toggle the switch
- Python 3.9+
- No third-party packages required
- If your browser stores `DevToolsActivePort` in a non-standard location, set `CDP_PORT_FILE` to the full path

## Commands

All commands use `scripts/cdp.py`. The `<target>` is a unique `targetId` prefix from `list`; use the exact prefix shown there. Ambiguous prefixes are rejected.

### List open pages

```bash
python3 scripts/cdp.py list
```

### Take a screenshot

```bash
python3 scripts/cdp.py shot <target> [file]
```

Captures the current viewport. The output includes the page DPR so screenshot coordinates can be converted back to CSS pixels for `clickxy`.

### Accessibility tree snapshot

```bash
python3 scripts/cdp.py snap <target>
python3 scripts/cdp.py snap <target> --full
```

Compact mode is the default. Use `--full` if you need the noisier tree.

### Evaluate JavaScript

```bash
python3 scripts/cdp.py eval <target> <expr>
```

Avoid index-based selection across multiple `eval` calls when the DOM may change between calls. Prefer stable selectors or collect the data in one expression.

### Other commands

```bash
python3 scripts/cdp.py html    <target> [selector]
python3 scripts/cdp.py nav     <target> <url>
python3 scripts/cdp.py net     <target>
python3 scripts/cdp.py click   <target> <selector>
python3 scripts/cdp.py clickxy <target> <x> <y>
python3 scripts/cdp.py type    <target> <text>
python3 scripts/cdp.py loadall <target> <selector> [ms]
python3 scripts/cdp.py evalraw <target> <method> [json]
python3 scripts/cdp.py open    [url]
python3 scripts/cdp.py stop    [target]
```

## Notes

- `type` uses `Input.insertText`, which works in focused cross-origin iframes where DOM-based `eval` approaches often fail.
- `shot` saves image pixels, while CDP input commands use CSS pixels:

```text
CSS px = screenshot px / DPR
```

- A background daemon is started the first time a tab is accessed and exits after 20 minutes of inactivity.
