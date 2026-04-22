---
name: chrome-cdp
description: A Python CLI for interacting directly with the user's running Chromium-based browser (Chrome, Edge, Brave, etc.) via the Chrome DevTools Protocol. Use this to inspect pages, extract data, evaluate JavaScript, and automate UI actions in existing open tabs. Requires explicit user approval.
---

# Chrome CDP

A lightweight, dependency-free Python CLI for the Chrome DevTools Protocol (CDP). It connects directly to Chrome's remote debugging port via WebSocket, bypassing bulky automation frameworks. A per-tab background daemon ensures the "Allow debugging" prompt requires only one approval per tab.

## Prerequisites

- Chromium-based browser with remote debugging enabled (`chrome://inspect/#remote-debugging`).
- Python 3.9+
- No third-party packages required.
- Optional: Set `CDP_PORT_FILE` to the full path if `DevToolsActivePort` is in a non-standard location.

## Commands

All commands use `scripts/cdp.py`. The `<target>` is a unique `targetId` prefix from `list`; use the exact prefix shown there.

### List open pages

```bash
python3 scripts/cdp.py list
```

### Take a screenshot

```bash
python3 scripts/cdp.py shot <target> [file]
python3 scripts/cdp.py shot <target> --full [file]
```

Captures the current viewport (or the full page with `--full`). The output includes the page DPR to convert screenshot coordinates to CSS pixels for `clickxy`.

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

Avoid index-based selection across multiple `eval` calls when the DOM may change. Prefer stable selectors or collecting data in one expression.

### Navigation and waiting

```bash
python3 scripts/cdp.py nav     <target> <url>
python3 scripts/cdp.py wait    <target> <selector>
python3 scripts/cdp.py wait    <target> --gone <selector>
python3 scripts/cdp.py wait    <target> --idle
python3 scripts/cdp.py wait    <target> <selector> --timeout 15000
```

`nav` navigates and waits for page load. `wait` polls for a selector to appear (default), disappear (`--gone`), or network idle (`--idle`). Default timeout is 10s.

### Interaction commands

```bash
python3 scripts/cdp.py click   <target> <selector>
python3 scripts/cdp.py clickxy <target> <x> <y>
python3 scripts/cdp.py hover   <target> <selector>
python3 scripts/cdp.py hover   <target> <x> <y>
python3 scripts/cdp.py type    <target> <text>
python3 scripts/cdp.py press   <target> <key> [modifier...]
python3 scripts/cdp.py fill    <target> <selector> <text>
python3 scripts/cdp.py select  <target> <selector> <value>
python3 scripts/cdp.py scroll  <target> [selector] <direction> [px]
```

- `click` clicks a CSS selector (scrolls into view first).
- `clickxy` clicks at CSS pixel coordinates.
- `hover` moves the mouse over an element or coordinates.
- `type` uses `Input.insertText` (works in focused cross-origin iframes where DOM-based `eval` fails).
- `press` dispatches `keyDown`/`keyUp` events. Supports named keys (`Enter`, `Tab`, `Escape`, `ArrowDown`, `Backspace`, `Delete`, `Space`, etc.) and modifiers (`ctrl`, `alt`, `shift`, `meta`/`cmd`).
- `fill` clicks a field to focus it, clears existing text, then types new text. Prefer over `click` + `type` for inputs.
- `select` sets a `<select>` dropdown's value by option value or visible text, and dispatches `change`/`input` events.
- `scroll` scrolls the page or a specific container. Directions: `up`, `down`, `left`, `right`, `top`, `bottom`. Optional pixel amount (default: 85% of viewport/container height).

### Data commands

```bash
python3 scripts/cdp.py html    <target> [selector]
python3 scripts/cdp.py net     <target>
python3 scripts/cdp.py cookies <target>
python3 scripts/cdp.py cookies <target> --set name=value
python3 scripts/cdp.py cookies <target> --clear
python3 scripts/cdp.py storage <target>
python3 scripts/cdp.py storage <target> --session
python3 scripts/cdp.py storage <target> --set key=value
python3 scripts/cdp.py pdf     <target> [file]
python3 scripts/cdp.py console <target>
```

- `html` returns the full page or a specific element's outer HTML.
- `net` shows network performance entries (resource timing).
- `cookies` lists, sets, or clears cookies.
- `storage` reads/writes localStorage (or sessionStorage with `--session`).
- `pdf` saves the page as a PDF.
- `console` returns recent console logs and browser errors.

### Other commands

```bash
python3 scripts/cdp.py loadall <target> <selector> [ms]
python3 scripts/cdp.py evalraw <target> <method> [json]
python3 scripts/cdp.py open    [url]
python3 scripts/cdp.py stop    [target]
```

## Example Workflows

```bash
# 1. Fill form and wait for navigation
python3 scripts/cdp.py nav    <target> https://example.com/login
python3 scripts/cdp.py fill   <target> '#email' user@example.com
python3 scripts/cdp.py press  <target> Enter
python3 scripts/cdp.py wait   <target> .dashboard

# 2. Extract data and paginate
python3 scripts/cdp.py eval   <target> "document.body.innerText"
python3 scripts/cdp.py click  <target> '.next-page'
python3 scripts/cdp.py wait   <target> --idle
```

## Notes

- `shot` saves image pixels, while input commands use CSS pixels:

```text
CSS px = screenshot px / DPR
```

- A background daemon starts on first tab access and exits after 20 minutes of inactivity (configurable via `CDP_IDLE_TIMEOUT` in seconds).
- `press` key names are case-sensitive: use `Enter` not `enter`, `Tab` not `tab`.
- `scroll` defaults to 85% of the viewport/container height per scroll step.