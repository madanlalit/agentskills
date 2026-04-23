---
name: code-review
description: Review Python code for bugs, security vulnerabilities, and best practices. Use when auditing code quality, checking for security issues, or evaluating Python pull requests.
allowed-tools: ['grep', 'read', 'bash', 'sed', 'glob', 'cat', 'ls', 'pwd', 'cd', 'mkdir', 'rm']

---

# Python Code Review

## Quick Start
1. Understand the goal of the Python code change.
2. Review linked issues/documentation.
3. Check code against the Python priority checklist.
4. Provide structured, actionable feedback (group by Critical/Major/Minor).

## Severity Levels
- 🔴 **Critical:** Security, data loss, crashes. Block merge.
- 🟠 **Major:** Logic errors, significant bugs. Should fix.
- 🟡 **Minor:** Style issues, small improvements. Consider.
- 🔵 **Suggestion:** Optional enhancements.
- 🟢 **Praise:** Good patterns.

## Review Checklist

### 1. Security (Critical) 🔴
- No hardcoded secrets, API keys, passwords
- No `eval()`, `exec()`, or `pickle.load()` with untrusted data
- No `os.system()` or `subprocess.run(..., shell=True)`
- No `assert` for security checks (disabled with -O)
- Parameterized SQL queries (no string formatting for SQL)
- `yaml.safe_load()` over `yaml.load()`
- Input validation & secure path handling

### 2. Correctness & Reliability (Major) 🟠
- No mutable default arguments (`def f(x=[])` -> `def f(x=None)`)
- No bare `except:` -> use `except Exception:`
- Context managers used for resources (`with open(...)`)
- `is` for None/True/False, `==` for values
- Timezone-aware `datetime` objects
- Explicit string encoding (`open(..., encoding='utf-8')`)
- Edge cases handled (nulls, bounds, empty states)

### 3. Maintainability (Minor) 🟡
- Type hints on public interfaces
- Docstrings on modules/classes/functions
- f-strings preferred over `.format()` or `%`
- `pathlib.Path` preferred over `os.path`
- `logging` preferred over `print()`
- Clear naming & single responsibility functions
- DRY principles applied

## Output Format Example
```markdown
## Code Review Summary
**Verdict:** Request Changes

### Critical Issues
1. 🔴 SQL injection in `db.py:45` - use parameterized query instead of f-string.

### Major Issues
1. 🟠 Mutable default argument in `utils.py:12` - change `x=[]` to `x=None`.
```
