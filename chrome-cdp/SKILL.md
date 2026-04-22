---
name: chrome-cdp
description: A Python CLI for interacting directly with the user's running Chromium browser via the Chrome DevTools Protocol (CDP). Connects via WebSocket to inspect pages, extract data, evaluate JS, and automate UI actions in open tabs. Requires explicit user approval; a background daemon ensures the "Allow debugging" prompt only requires one approval per tab.
metadata:
  author: madanlalit
  compatibility: Requires Python 3.9+ and chromium-based browser with remote debugging enabled (`chrome://inspect/#remote-debugging`).
---

## Usage

For detailed command syntax, workflow examples, and technical notes, see the `references/commands.txt` file.