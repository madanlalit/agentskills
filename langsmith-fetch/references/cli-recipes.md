# LangSmith Fetch CLI Recipes

Use this file when you need exact command patterns or troubleshooting steps.

## Confirm setup

```bash
command -v langsmith-fetch
langsmith-fetch --help
langsmith-fetch config show
```

If auth/project context is missing, set environment variables:

```bash
export LANGSMITH_API_KEY=lsv2_...
export LANGSMITH_PROJECT=your-project-name
export LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

## Single-item fetch

Fetch one trace by ID:

```bash
langsmith-fetch trace <trace-id> --format raw
```

Fetch one thread by ID:

```bash
langsmith-fetch thread <thread-id> --project-uuid <project-uuid> --format raw
```

Write single-item output to a file:

```bash
langsmith-fetch trace <trace-id> --format json --file ./out/trace.json
langsmith-fetch thread <thread-id> --project-uuid <project-uuid> --format json --file ./out/thread.json
```

Include metadata/feedback for traces:

```bash
langsmith-fetch trace <trace-id> --include-metadata --include-feedback --format json
```

## Bulk fetch (preferred mode)

Export recent traces into one file per trace:

```bash
langsmith-fetch traces ./out/traces --limit 10 --project-uuid <project-uuid>
```

Export recent threads into one file per thread:

```bash
langsmith-fetch threads ./out/threads --limit 10 --project-uuid <project-uuid>
```

Apply time filters:

```bash
langsmith-fetch traces ./out/traces --last-n-minutes 30 --limit 20 --project-uuid <project-uuid>
langsmith-fetch threads ./out/threads --since 2026-01-01T00:00:00Z --limit 20 --project-uuid <project-uuid>
```

Customize output filenames:

```bash
langsmith-fetch traces ./out/traces --limit 20 --filename-pattern "trace_{index:03d}_{trace_id}.json"
langsmith-fetch threads ./out/threads --limit 20 --filename-pattern "thread_{index:03d}_{thread_id}.json"
```

Notes:
- Directory mode writes JSON files regardless of `--format`.
- Directory mode ignores `--format` and prints a warning if provided.

## Stdout mode (only when explicitly requested)

Fetch latest trace to stdout:

```bash
langsmith-fetch traces --limit 1 --format raw
```

Fetch latest threads to stdout:

```bash
langsmith-fetch threads --limit 5 --project-uuid <project-uuid> --format raw
```

Pipe stdout JSON to `jq`:

```bash
langsmith-fetch trace <trace-id> --format raw | jq '.'
langsmith-fetch traces --limit 3 --format raw | jq '.'
```

## Troubleshooting

Auth failures:
- Confirm `LANGSMITH_API_KEY` or config `api-key` is present.
- Confirm `LANGSMITH_ENDPOINT` if using self-hosted LangSmith.

Thread fetch fails:
- Pass `--project-uuid <project-uuid>` explicitly.
- Confirm `project-uuid` in `langsmith-fetch config show`.

No results:
- Relax `--last-n-minutes` or use an earlier `--since`.
- Increase `--limit`.
- Verify the project UUID points to the expected project.

Slow bulk fetch:
- Lower or raise `--max-concurrent` based on API behavior (default 5).
- Keep progress enabled unless logs must stay clean (`--no-progress`).


