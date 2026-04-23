---
name: codebase-understanding
description: >
  Use this skill when you need to understand how an unfamiliar codebase works before doing anything
  else. Activate when the user asks you to explore a project, trace a feature or bug, map the
  architecture, plan a refactor, or answer "how does X work?" — even if they don't explicitly say
  "analyze the codebase." Also use it when you're about to make a large or cross-cutting change and
  need to understand the system first. Supports all languages and project types.
metadata:
  version: "1.0"
---

# Codebase Understanding

## Workflow

Complete these steps in order. Do not skip ahead.

- [ ] **1. Orient** — map the surface area
- [ ] **2. Identify architecture** — name the pattern and major components
- [ ] **3. Trace one flow** — follow a key action end-to-end
- [ ] **4. Verify** — check your model against tests and git history
- [ ] **5. Summarize** — write findings before making any changes

---

## Step 1: Orient

Read these first, in this order:

1. `README.md` (or `README`) — purpose, setup, high-level design
2. Primary manifest — `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, or `pom.xml`
3. `.env.example` or `config/` — required secrets and feature knobs

Then get a structural overview:

```bash
# Directory tree (depth 2)
find . -maxdepth 2 -type d | grep -vE "node_modules|venv|vendor|build|dist|__pycache__|\.git" | sort

# File counts by type
find . -type f | grep -vE "node_modules|venv|vendor" | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -15

# Likely entry points
find . -maxdepth 3 -type f \( -name "main.*" -o -name "index.*" -o -name "app.*" -o -name "__main__.py" \) \
  | grep -vE "node_modules|venv"
```

---

## Step 2: Identify Architecture

**Project type** — pick the best fit:
- **Frontend SPA** — `src/components/`, framework in `package.json` (`react`, `vue`, `angular`, `next`)
- **Backend API** — `routes/` or `controllers/`, look for OpenAPI spec
- **CLI tool** — `cmd/` or `cli/`, look for `cobra`, `click`, `argparse`
- **Library/SDK** — `src/` or `lib/`, exported `index.ts` or `__init__.py`
- **Microservices** — multiple `services/` subdirs, proto files, message broker config
- **Monorepo** — `packages/` or `apps/`, workspace config in manifest

**Architecture style** — pick the best fit:
- **Layered** — `models/`, `views/`, `controllers/` (or equivalent)
- **Clean/Hexagonal** — `domain/`, `application/`, `infrastructure/`, `interfaces/`
- **Event-driven** — `events/`, `handlers/`, `subscribers/`, message broker clients
- **Flat** — no strong layering; trace from entry point directly

Quick check:
```bash
rg -l "class.*Controller|class.*Service|class.*Repository|class.*Handler" 2>/dev/null | head -10
```

---

## Step 3: Trace One Key Flow

Pick the most important user-facing action and trace it fully before anything else.

**1. Find the entry point:**
```bash
# Web API routes
rg "(@app\.route|@router\.|app\.get|app\.post|router\.get|router\.post)" | head -20
# CLI commands
rg "(click\.command|cobra\.Command|argparse\.add_argument)" | head -10
```

**2. Follow the call chain** — handler → service → repository → external:
```bash
rg "def <function_name>|function <function_name>|func <FunctionName>" .
```

**3. Map data transformations** — what shape enters and exits each layer.

**4. Spot side effects:**
```bash
rg "(\.save\(|\.create\(|insert|update|delete|commit|publish|emit|send)" path/to/file
```

**5. Check for auth gates on this flow:**
```bash
rg "(authenticate|authorize|@login_required|middleware.*auth)" path/to/route_file
```

---

## Step 4: Verify Your Model

```bash
# Do tests cover the flow you traced?
find . -name "*test*" -o -name "*spec*" | xargs grep -l "<function_name>" 2>/dev/null

# What changed recently in the key files?
git log --oneline -15 -- path/to/key/file

# Any other callers you missed?
rg "<function_name>" . | grep -v "_test\."
```

Flag it if: tests are absent, git log shows frequent churn, or you find callers you hadn't expected.

---

## Step 5: Summarize

Write this before making any changes:

```
Project type    : e.g. REST API — Python/FastAPI
Architecture    : e.g. Layered — routes → services → repositories
Flow traced     : e.g. POST /orders → OrderService.create → OrderRepo.save → DB
Key entry points: [files]
External deps   : [APIs, DBs, queues]
Risks/gotchas   : [e.g. no auth on admin endpoints, soft deletes]
Test coverage   : [e.g. good unit coverage on services, no integration tests]
```

---

## Gotchas

- **Soft deletes** — queries without `WHERE deleted_at IS NULL` silently return deleted records.
- **Generated code** — `build/`, `dist/`, `*.pb.go`, `*.generated.ts` are outputs; trace back to the source generator.
- **Monkey-patching** — Python/Ruby may override methods at runtime (`setattr`, `module_eval`).
- **Implicit globals** — DB connections, config objects, caches that don't appear in function signatures.
- **ID aliasing** — the same entity may be `user_id` in the DB, `uid` in auth, `accountId` in billing.
- **Dead code** — unused files and imports survive in active repos; don't read code that isn't reachable.
- **Feature flags** — `if feature_enabled("X")` wrappers can hide the real behavior; check for them.
- **Env-specific branches** — `if ENV == "production"` logic may be the actual critical path.

---

## Adjust Depth by Goal

| Goal | Start here | Time |
|------|-----------|------|
| Bug investigation | Reproduce → stack trace → trace failing flow → `git log` | 20–60 min |
| Feature addition | Find the closest analogous existing feature; use it as template | 30–90 min |
| Onboarding | All 5 steps, then run locally and read tests | 2–4 hrs |
| Refactoring | Map component boundaries and coupling before touching anything | 1–3 hrs |
| Security audit | Map all input boundaries → auth flows → secret handling | 2–4 hrs |
