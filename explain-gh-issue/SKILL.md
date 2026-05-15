---
name: explain-gh-issue
description: Explains, summarizes, and triages GitHub issues. Triggers on URLs, issue IDs (e.g. "#123"), or requests like "explain this issue".
metadata:
  author: madanlalit
  compatibility: Requires authenticated `gh` CLI or issue content via URL/copy-paste.
---

## Goal

Look past the title and labels. Surface the real problem, the actual status (not just open/closed), and one concrete next step. Signal over completeness.

## Tools

- `scripts/check_gh.sh` — validates `gh` CLI auth
- `scripts/fetch_issue.sh <owner/repo> <number>` — fetches issue as plain text
  - `--comments-tail N` — last N comments only (default: all; use for threads >20)
  - `--include-linked-prs` — pull linked PR metadata (recommended for closed issues)

## Heuristics

- **Filter noise.** Skip "+1", "same here", emoji-only, and bot comments. Signal lives in OP, maintainer replies, and comments with code or repros.
- **Labels lie.** "Bug" doesn't mean it's a bug. "Closed" doesn't mean fixed — verify via close reason, linked PRs, and the last substantive comment.
- **Find the resolution.** For closed issues, state *what* resolved it: merged PR, wontfix, workaround, or duplicate. Don't leave this implicit.
- **Surface hidden context.** Task lists signal epics. Images can't be read — note they exist. Linked issues/PRs are the real dependency graph.
- **Maintainer voice wins.** "By design" or "tracked in #X" overrides user interpretation. Self-assignment or info requests signal active triage — flag them.
- **Local relevance.** Search the repo for referenced files, symbols, or error strings. Tie the summary to code the user can act on.

## Output Shape

Adapt to context, but always include:

- **Core problem** in 1-2 sentences (not the title — the actual problem)
- **Status** with evidence (not just the label — *why* it's in that state)
- **Missing/ambiguous** — repro steps, environment, or decisions that block action
- **Next step** — a specific file, command, or label change, not vague advice

Keep it short. If nothing is actionable, say so and explain why.
