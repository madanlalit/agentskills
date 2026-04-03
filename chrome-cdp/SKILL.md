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
python3 scripts/cdp.py shot <target> --full [file]
```

Captures the current viewport (or the full page with `--full`). The output includes the page DPR so screenshot coordinates can be converted back to CSS pixels for `clickxy`.

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
- `type` uses `Input.insertText`, which works in focused cross-origin iframes where DOM-based `eval` approaches often fail.
- `press` dispatches `keyDown`/`keyUp` events. Supports named keys (`Enter`, `Tab`, `Escape`, `ArrowDown`, `Backspace`, `Delete`, `Space`, etc.) and modifiers (`ctrl`, `alt`, `shift`, `meta`/`cmd`).
- `fill` clicks a field to focus it, selects all existing text, deletes it, then types new text. Use this instead of `click` + `type` for input fields.
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
```

- `html` returns the full page or a specific element's outer HTML.
- `net` shows network performance entries (resource timing).
- `cookies` lists, sets, or clears cookies.
- `storage` reads/writes localStorage (or sessionStorage with `--session`).
- `pdf` saves the page as a PDF.

### Other commands

```bash
python3 scripts/cdp.py loadall <target> <selector> [ms]
python3 scripts/cdp.py evalraw <target> <method> [json]
python3 scripts/cdp.py open    [url]
python3 scripts/cdp.py stop    [target]
```

## Recipes

### Log into a website

```bash
python3 scripts/cdp.py list
python3 scripts/cdp.py nav     <target> https://example.com/login
python3 scripts/cdp.py fill    <target> '#email' user@example.com
python3 scripts/cdp.py fill    <target> '#password' s3cret
python3 scripts/cdp.py press   <target> Enter
python3 scripts/cdp.py wait    <target> .dashboard
python3 scripts/cdp.py shot    <target>
```

### Scrape a paginated table

```bash
python3 scripts/cdp.py snap    <target>
python3 scripts/cdp.py eval    <target> "JSON.stringify([...document.querySelectorAll('table tr')].map(r => [...r.cells].map(c => c.textContent)))"
python3 scripts/cdp.py click   <target> '.next-page'
python3 scripts/cdp.py wait    <target> --idle
python3 scripts/cdp.py eval    <target> "..."
```

### Fill a multi-field form

```bash
python3 scripts/cdp.py fill    <target> '#name' 'Jane Doe'
python3 scripts/cdp.py select  <target> '#country' 'United States'
python3 scripts/cdp.py click   <target> '#agree-checkbox'
python3 scripts/cdp.py click   <target> 'button[type=submit]'
python3 scripts/cdp.py wait    <target> '.success-message'
```

### Debug network requests

```bash
python3 scripts/cdp.py net      <target>
python3 scripts/cdp.py cookies  <target>
python3 scripts/cdp.py storage  <target>
python3 scripts/cdp.py eval     <target> "document.cookie"
```

## Notes

- `shot` saves image pixels, while CDP input commands use CSS pixels:

```text
CSS px = screenshot px / DPR
```

- A background daemon is started the first time a tab is accessed and exits after 20 minutes of inactivity.
- `press` key names are case-sensitive: use `Enter` not `enter`, `Tab` not `tab`.
- `scroll` defaults to 85% of the viewport/container height per scroll step.
