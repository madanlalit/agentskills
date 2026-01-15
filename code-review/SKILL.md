---
name: code-review
description: Review code for bugs, security vulnerabilities, and best practices. Use when: reviewing pull requests, auditing code quality, checking for security issues, finding bugs, or evaluating code changes. Supports Python, JavaScript, TypeScript, Go, Rust, Java, C/C++, and SQL.
---

# Code Review Skill

## Objective
Conduct thorough, constructive code reviews that identify issues, suggest improvements, and ensure code meets quality standards while maintaining a positive and educational tone.

---

## Quick Start Workflow

1. UNDERSTAND CONTEXT
   ├── Identify the purpose/goal of the code change
   ├── Understand the broader system architecture
   └── Review any linked issues, PRs, or documentation

2. SCOPE THE REVIEW
   ├── Single file/function? → Deep focused review
   ├── Multiple files/PR? → Start with high-level, then drill down
   └── Full codebase audit? → Use Priority Tiers systematically

3. PERFORM REVIEW
   ├── Use Review Checklist by priority
   ├── Check each category systematically
   └── Document findings with severity levels

4. PREPARE FEEDBACK
   ├── Organize by severity (Critical → Minor)
   ├── Provide actionable suggestions with examples
   ├── Acknowledge good patterns and practices
   └── Ask clarifying questions when unsure

5. DELIVER REVIEW
   ├── Choose appropriate output format
   ├── Start with summary of overall impression
   ├── Group feedback by category
   └── Be specific with line references

---

## Scope Control

**CRITICAL: Scale review depth to change size.**

| Scenario | Scope | Time |
|----------|-------|------|
| Single function/method | Deep review + callers/callees | 5-10 min |
| Single file | Full checklist, all priorities | 15-30 min |
| Small PR (<200 lines) | Priority 1-2 checks thoroughly | 20-40 min |
| Medium PR (200-500 lines) | Priority 1-2, sample 3-4 | 30-60 min |
| Large PR (500+ lines) | Request split OR multiple sessions | 60+ min |
| Full codebase audit | Systematic, plan multiple sessions | Hours |

**Per-review limits:**

- Quick review: 5-10 issues max, focus on blockers
- Standard review: 10-20 issues, balanced feedback
- Deep audit: Comprehensive, organize by category

**When to stop:**

- You've found 3+ critical issues → Stop, report immediately
- Review is taking too long → Note scope and ask to split
- Diminishing returns → Focus on highest-impact items

---

## Severity Levels

| Level | Icon | Description | Action |
|-------|------|-------------|--------|
| **Critical** | 🔴 | Security vulnerabilities, data loss, crashes | Block merge |
| **Major** | 🟠 | Bugs, logic errors, significant issues | Should fix |
| **Minor** | 🟡 | Style issues, small improvements | Consider |
| **Suggestion** | 🔵 | Optional enhancements, alternatives | Optional |
| **Praise** | 🟢 | Good patterns worth highlighting | Encourage |

---

## Output Formats

Choose based on context:

### Inline Comments (for PRs)

```
📍 `file.py:42`
🔴 **Critical:** SQL injection - use parameterized query
```

### Summary Report (for audits)
```markdown
## Code Review Summary

**Verdict:** Request Changes
**Critical:** 2 | **Major:** 3 | **Minor:** 5

### Critical Issues
1. SQL injection in `api/users.py:45` 
2. Hardcoded secret in `config.py:12`
```

### Checklist (for quick reviews)
```
✅ No hardcoded secrets
✅ Input validation present
❌ Missing error handling in async code
⚠️ Could use connection pooling
```

---

## Review Checklist by Priority

### Priority 1: Critical (Always Check) 🔴

#### Security
- [ ] No hardcoded secrets, API keys, or passwords
- [ ] Input validation on all external data
- [ ] No SQL injection (parameterized queries used)
- [ ] No XSS vulnerabilities (proper escaping)
- [ ] No path traversal (file paths validated)
- [ ] Secure auth/authz checks
- [ ] No unsafe deserialization (pickle, eval, exec)
- [ ] Secrets not logged or exposed in errors

#### Correctness
- [ ] Logic handles edge cases (null, empty, bounds)
- [ ] Error conditions caught and handled
- [ ] Resources cleaned up (files, connections, locks)
- [ ] No race conditions in concurrent code
- [ ] No off-by-one errors

### Priority 2: Reliability 🟠

#### Error Handling
- [ ] Appropriate exception types
- [ ] Error messages are informative (not leaking secrets)
- [ ] Graceful degradation where appropriate
- [ ] Errors logged for debugging

#### API Design
- [ ] Backward compatibility (or breaking changes documented)
- [ ] Input validation with helpful messages
- [ ] Consistent naming conventions

### Priority 3: Maintainability 🟡

#### Code Quality
- [ ] Single Responsibility Principle
- [ ] DRY - no unnecessary duplication
- [ ] Functions are focused and small (<50 lines)
- [ ] Clear, descriptive naming
- [ ] Magic numbers/strings → constants

#### Documentation & Testing
- [ ] Public APIs documented
- [ ] Complex logic has comments
- [ ] Unit tests for new code
- [ ] Edge cases and error paths tested

### Priority 4: Performance (When Relevant) 🔵

- [ ] No N+1 queries
- [ ] Appropriate data structures
- [ ] Pagination for large datasets
- [ ] Caching considered
- [ ] No blocking in async code

---

## Discovery Patterns

**✨ Automated Scan:**
Run the included script to check all patterns at once:
```bash
./scan.sh
```

Or use these individual commands:

### Security Scan
```bash
# Hardcoded secrets
rg -n "(password|secret|api[_-]?key|token|credential)\s*=\s*['\"][^'\"]{8,}['\"]" --type-add 'code:*.{py,js,ts,go,rb}'

# Dangerous functions
rg -n "\b(eval|exec|os\.system|shell=True|dangerouslySetInnerHTML)\b"

# SQL injection patterns
rg -n "(SELECT|INSERT|UPDATE|DELETE).*\+.*\"|f\".*SELECT|`\$\{.*\}.*SELECT"
```

### Code Quality Scan
```bash
# TODO/FIXME items
rg -n "(TODO|FIXME|HACK|XXX|BUG):" 

# Long functions (check manually after)
rg -n "^(def |function |func )" --type py

# Broad exception catching
rg -n "except\s*(Exception|BaseException)?\s*:" --type py
rg -n "catch\s*\(\s*(e|err|error)?\s*\)" --type js
rg -n "catch\s*\(\s*Exception\s+" --type java

### C/C++ Safety Scan
```bash
# Unsafe string functions
rg -n "(strcpy|strcat|sprintf|gets)" --type cpp

# Legacy memory management
rg -n "\b(malloc|free|new|delete)\b" --type cpp
```

### Test Coverage Check
```bash
# Find source files without tests
for f in src/**/*.py; do
  [[ ! -f "tests/test_$(basename $f)" ]] && echo "Missing test: $f"
done
```

---

## Language-Specific Quick Checks

### Python
| Pattern | Issue | Fix |
|---------|-------|-----|
| `def foo(x=[])` | Mutable default | `def foo(x=None)` |
| `except:` | Bare except | `except Exception:` |
| `os.system(...)` | Shell injection | `subprocess.run([...])` |
| `% (user_input)` | Format injection | f-strings |

### JavaScript/TypeScript
| Pattern | Issue | Fix |
|---------|-------|-----|
| `eval(...)` | Code injection | Avoid or sandbox |
| `innerHTML = ` | XSS risk | `textContent` or sanitize |
| `var x` | Scope issues | `const`/`let` |
| `any` type | Type safety | Proper types |

### Go
| Pattern | Issue | Fix |
|---------|-------|-----|
| `_ = err` | Ignored error | Handle it |
| No `defer` cleanup | Resource leak | Add `defer` |
| `go func()` w/o sync | Goroutine leak | Use WaitGroup/context |

### SQL
| Pattern | Issue | Fix |
|---------|-------|-----|
| `"SELECT * FROM " + id` | SQL injection | Parameterized query |
| `SELECT *` | Over-fetching | List columns |
| No `LIMIT` | Unbounded query | Add pagination |

### Rust
| Pattern | Issue | Fix |
|---------|-------|-----|
| `unwrap()` | Panic risk | `expect()` or handle |
| `unsafe { ... }` | Memory safety | Validate invariants |
| `clone()` | Perf/Ownership | Reference/Arc |

### Java
| Pattern | Issue | Fix |
|---------|-------|-----|
| `System.out.print` | Logging | Use Logger |
| `catch (Exception e)` | Broad Catch | Specific Exception |
| `==` on Strings | Equality | `.equals()` |

### C/C++
| Pattern | Issue | Fix |
|---------|-------|-----|
| `strcpy`, `strcat` | Buffer Overflow | `strncpy`, `strncat` |
| `malloc` (C++) | Memory Mgmt | `new` / Smart Ptr |
| `using namespace` | Pollution | Specific imports |

See [references/CHECKLISTS.md](references/CHECKLISTS.md) for complete language guides.

---

## Feedback Examples

### Critical: Security
```
🔴 **SQL Injection Vulnerability**

📍 `api/users.py:45`

**Before:**
query = f"SELECT * FROM users WHERE id = {user_id}"

**After:**
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))

**Impact:** Attackers can read/modify/delete any data.
```

### Major: Logic Error
```
🟠 **Off-by-one in pagination**

📍 `utils/paginator.py:23`

`items[start:end+1]` returns n+1 items.
Should be: `items[start:end]`
```

### Suggestion: Improvement
```
🔵 **Consider extracting validation**

📍 `handlers/order.py:67-89`

This 20-line validation block could become `validate_order()`
for reusability and easier testing.
```

### Praise: Good Pattern
```
🟢 **Nice!** Great use of Strategy pattern for payment processors.
Makes adding new payment methods easy.
```

---

## Review Anti-Patterns

**Avoid these in your reviews:**

| ❌ Don't | ✅ Do Instead |
|----------|---------------|
| "This is wrong" | "Could you explain...? I'm wondering if X handles Y" |
| Nitpick style only | Balance: blockers first, style later |
| No positive feedback | Acknowledge good patterns |
| Vague criticism | Specific line + suggestion + reason |
| Block on preferences | Mark style as "Suggestion 🔵" |

---

## Review Modes

### PR Review Mode
```
Focus: Changes only (delta review)
Check: Security → Correctness → Tests → Style
Output: Inline comments + summary
```

### Security Audit Mode
```
Focus: All input boundaries and data flows
Check: Auth, injection, secrets, crypto, logging
Output: Detailed report with risk ratings
```

### Performance Review Mode
```
Focus: Hot paths and bottlenecks  
Check: Queries, algorithms, caching, async
Output: Report with measurements if possible
```

### Onboarding Review Mode
```
Focus: Teaching and explaining
Check: All categories, explain "why"
Output: Detailed comments, link to docs
```
