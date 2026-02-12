---
name: langsmith-fetch
description: Fetch and inspect LangSmith traces and threads with the langsmith-fetch CLI. Use when a user asks to pull recent traces/threads, fetch a specific trace/thread by ID, export LangSmith data to JSON files, filter by project or time window, or produce raw JSON output for downstream analysis/automation.
---

# LangSmith Fetch

Fetch LangSmith traces and threads through `langsmith-fetch` with reliable defaults for debugging and automation.
Prefer directory-mode bulk export, switch to stdout only when explicitly requested, and use `--format raw` when machine parsing stdout.

## Preflight (required)

1. Verify the CLI is installed:
```bash
command -v langsmith-fetch
```
2. Inspect current config:
```bash
langsmith-fetch config show
```
3. Set/verify environment variables when needed:
```bash
export LANGSMITH_API_KEY=lsv2_...
export LANGSMITH_PROJECT=your-project-name
export LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```
4. Edit `~/.langsmith-cli/config.yaml` directly if configuration changes are needed and no config write subcommand is available in the installed CLI.

## Pick the right command

- Use `langsmith-fetch trace <trace-id>` for one trace.
- Use `langsmith-fetch thread <thread-id>` for one thread.
- Use `langsmith-fetch traces <output-dir>` for many traces.
- Use `langsmith-fetch threads <output-dir>` for many threads.
- Pass `--project-uuid <uuid>` whenever project scope may be ambiguous.
- Treat `--project-uuid` as required for thread operations unless a valid value is already configured.

## Apply output-mode rules

- Default to directory mode for bulk commands:
```bash
langsmith-fetch traces ./out/traces --limit 10
langsmith-fetch threads ./out/threads --limit 10
```
- Use stdout mode only when the user explicitly asks for terminal output or piping.
- Use `--format raw` in stdout mode when output is consumed by tools/agents.
- Avoid adding `--format` in directory mode unless requested; the CLI ignores it and warns.
- Use `--file` for single output artifacts when the user wants one file.

## Use core recipes

Fetch one trace in raw JSON:
```bash
langsmith-fetch trace <trace-id> --format raw
```

Fetch one thread in raw JSON with explicit project:
```bash
langsmith-fetch thread <thread-id> --project-uuid <project-uuid> --format raw
```

Fetch recent traces by time window into a directory:
```bash
langsmith-fetch traces ./out/traces --limit 25 --last-n-minutes 60 --project-uuid <project-uuid>
```

Fetch recent threads since timestamp:
```bash
langsmith-fetch threads ./out/threads --since 2026-01-01T00:00:00Z --project-uuid <project-uuid>
```

Customize filenames in directory mode:
```bash
langsmith-fetch traces ./out/traces --limit 20 --filename-pattern "trace_{index:03d}_{trace_id}.json"
```

## Report results clearly

- Report the exact command used.
- Report where files were written.
- Report how many files were produced.
- Provide one sample file path to confirm output shape.
- Call out if zero results were returned due to filters.

## References

Load only when needed:
- `references/cli-recipes.md` for command cookbook and troubleshooting.

## Guardrails

- Do not invent trace IDs, thread IDs, or project UUIDs.
- Ask for missing IDs only when they cannot be inferred from config or prior context.
- Keep bulk fetch limits reasonable unless the user requests larger exports.
- Preserve original JSON payloads; do not rewrite fetched files unless requested.


