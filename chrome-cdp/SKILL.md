---
name: chrome-cdp
description: A Python CLI for interacting directly with the user's running Chromium browser via the Chrome DevTools Protocol (CDP). Connects via WebSocket to inspect pages, extract data, evaluate JS, and automate UI actions in open tabs. Requires explicit user approval; a background daemon ensures the "Allow debugging" prompt only requires one approval per tab.
metadata:
  author: madanlalit
  compatibility: Requires Python 3.9+ and chromium-based browser with remote debugging enabled (`chrome://inspect/#remote-debugging`).
---

## Usage

Before doing anything, read `references/commands.txt` to understand how to execute the commands.
For comprehensive workflow examples, refer to `references/usage.txt`.