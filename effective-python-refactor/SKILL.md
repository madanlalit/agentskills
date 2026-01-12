---
name: effective-python-refactor
description: Refactor Python codebases (greenfield or brownfield) using the Effective Python checklist; apply when modernizing code, enforcing best practices, or restructuring APIs, tests, concurrency, and packaging.
---

# Effective Python Refactoring Skill

## Objective
Use the 125 Effective Python items as a detailed refactoring checklist to improve correctness, clarity, performance, and maintainability while preserving behavior unless explicitly asked to change it.

---

## Quick Start Workflow

```
1. GATHER CONTEXT
   ├── Confirm Python version(s) supported
   ├── Identify toolchain (formatter, linter, type checker, test runner)
   └── Understand project constraints and style rules

2. SCOPE THE WORK
   ├── User requested specific files? → Focus only on those
   ├── Full audit requested? → Use Priority Tiers below
   └── Bug fix or feature? → Apply only relevant items

3. DISCOVER ISSUES
   └── Use Discovery Patterns section to find violations

4. CREATE DETAILED REPORT
   ├── Summarize all discovered issues by priority tier
   ├── List affected files and specific violations
   ├── Estimate scope and impact of changes
   └── Ask user: "Would you like to proceed with refactoring?"

5. REFACTOR
   ├── One item at a time, in priority order
   ├── Keep changes small and reviewable
   └── Preserve public APIs unless redesign requested

6. VERIFY
   ├── Run formatter, linter, type checker
   ├── Run tests (add new tests if coverage gaps exist)
   └── Document any exceptions or migrations needed
```

---

## Scope Control

**CRITICAL: Do not attempt all 125 items at once.**

| Scenario | Scope |
|----------|-------|
| User mentions specific files | Only those files, only relevant items |
| Bug fix | Items related to the bug category only |
| New feature | Items 1-3, then items relevant to the feature |
| Code review | Scan for Priority 1 issues, note others |
| Full audit | Work through Priority Tiers, max 10-15 items per session |
| Modernization | Focus on version-specific items and Quick Wins |

**Per-session limits:**
- Quick refactor: 3-5 items
- Standard refactor: 5-10 items
- Deep refactor: 10-15 items
- Full audit: Plan multiple sessions

---

## Priority Tiers

### Priority 1: Security & Correctness (Fix Immediately)
These items prevent bugs, security vulnerabilities, and data corruption.

| Item | Name | Discovery Pattern |
|------|------|-------------------|
| 10 | bytes vs str | `Grep: \.encode\(\)` without explicit encoding |
| 32 | Raise exceptions, don't return None | `Grep: return None` in error paths |
| 36 | Mutable default arguments | `Grep: def.*=\[\]|def.*=\{\}|def.*=set\(\)` |
| 67 | subprocess safety | `Grep: os\.system|shell=True` |
| 69 | Thread locks for shared state | `Grep: threading` then check for unguarded shared state |
| 85 | Don't catch broad Exception | `Grep: except Exception:|except:` |
| 86 | Exception vs BaseException | `Grep: except BaseException` |
| 91 | Avoid exec/eval | `Grep: \bexec\(|\beval\(` |
| 107 | Pickle security | `Grep: pickle\.load` with untrusted input |

### Priority 2: High-Impact Quick Wins (Easy Improvements)
Low effort, high readability/maintainability gains.

| Item | Name | Discovery Pattern |
|------|------|-------------------|
| 2 | PEP 8 style | Run formatter/linter |
| 11 | F-strings | `Grep: %s|%d|\.format\(` |
| 17 | enumerate over range | `Grep: range\(len\(` |
| 18 | zip for parallel iteration | `Grep: range\(len\(.*\]\s*$` with parallel access |
| 26 | dict.get over in+index | `Grep: if.*in.*:.*\[` dict access patterns |
| 38 | functools.wraps | `Grep: def \w+\(func` decorator without @wraps |
| 40 | Comprehensions over map/filter | `Grep: \bmap\(|\bfilter\(` |
| 51 | dataclasses | Classes with only `__init__` setting attributes |
| 124 | Type hints | `Grep: ^def ` without `->` return annotations |

### Priority 3: Architecture & Design (Plan Carefully)
Larger refactors that improve structure but require careful migration.

| Item | Name | When to Apply |
|------|------|---------------|
| 29 | Classes over nested dicts | Deep nesting (3+ levels) in data structures |
| 31 | Result objects over long tuples | Functions returning 4+ values |
| 49 | Polymorphism over isinstance | Long isinstance chains |
| 57 | collections.abc for containers | Custom container-like classes |
| 73-79 | Concurrency patterns | Performance-critical I/O or CPU code |
| 119 | Package organization | Growing codebases with import complexity |
| 121 | Root exception hierarchy | Libraries with multiple exception types |
| 122 | Break circular imports | Import errors or tangled dependencies |

### Priority 4: Performance (Profile First)
Only apply after profiling identifies actual bottlenecks.

| Item | Name | Applies When |
|------|------|--------------|
| 43-44 | Generators | Large data processing, memory issues |
| 92-93 | Profiling | Before any optimization work |
| 94-96 | Native extensions | Profiler shows Python as bottleneck |
| 97-98 | Startup optimization | Slow application startup |
| 99 | memoryview/bytearray | Large binary data processing |
| 102 | bisect for sorted search | Frequent searches in sorted data |
| 103-104 | deque/heapq | Queue or priority queue patterns |

---

## Version Compatibility Matrix

Features requiring specific Python versions:

| Feature | Min Version | Items |
|---------|-------------|-------|
| Walrus operator `:=` | 3.8 | 8, 42 |
| Positional-only params `/` | 3.8 | 37 |
| `dict` ordering guaranteed | 3.7 | 25 |
| `dataclasses` | 3.7 | 51, 56 |
| `match`/`case` | 3.10 | 9 |
| `zip(..., strict=True)` | 3.10 | 18 |
| `asyncio.run()` | 3.7 | 75-78 |
| `typing.Protocol` | 3.8 | 49, 124 |
| `importlib.resources` | 3.7 | 98 |
| Exception groups | 3.11 | 88 |
| `Self` type | 3.11 | 52 |

**Before using these features:** Confirm the project's minimum Python version supports them.

---

## Discovery Patterns

Use these patterns to find violations. Run from project root.

### Security & Correctness
```bash
# Mutable default arguments (Item 36) - CRITICAL
Grep: "def .*(=\[\]|=\{\}|=set\(\))"

# Broad exception catching (Items 85-86)
Grep: "except\s*(Exception|BaseException)?\s*:"

# Shell injection risk (Item 67)
Grep: "shell\s*=\s*True|os\.system\s*\("

# Unsafe eval/exec (Item 91)
Grep: "\b(eval|exec)\s*\("

# Pickle with potentially untrusted data (Item 107)
Grep: "pickle\.(load|loads)\s*\("
```

### Style & Modernization
```bash
# Old-style string formatting (Item 11)
Grep: '"%.*%[sdrf]|\.format\s*\('

# range(len()) anti-pattern (Item 17)
Grep: "range\s*\(\s*len\s*\("

# Missing @wraps in decorators (Item 38)
Grep: "def \w+\s*\(\s*func\s*\)" -A5  # Then check for @wraps

# map/filter instead of comprehensions (Item 40)
Grep: "\b(map|filter)\s*\(\s*lambda"

# Type hints missing (Item 124)
Grep: "^def \w+\([^)]*\)\s*:" # No return annotation
```

### Architecture
```bash
# Long tuple returns (Item 31)
Grep: "return\s+\w+\s*,\s*\w+\s*,\s*\w+\s*,\s*\w+" # 4+ values

# isinstance chains (Item 49)
Grep: "isinstance\s*\([^)]+\)" -A2 -B2 # Look for elif isinstance patterns

# Nested dict access (Item 29)
Grep: "\]\s*\[\s*['\"]?\w+['\"]?\s*\]\s*\[" # 3+ levels deep
```

### Concurrency
```bash
# Thread creation without pooling (Item 72)
Grep: "Thread\s*\(\s*target\s*="

# Missing locks with shared state (Item 69)
Grep: "threading\.(Thread|Lock)" # Cross-reference shared variables

# Blocking calls in async (Items 75-78)
Grep: "async def" -A20 # Look for time.sleep, requests., open()
```

---

## Greenfield vs Brownfield

### Greenfield (New Projects)
Establish conventions early:

1. **First commits should include:**
   - Formatter config (black/ruff)
   - Linter config (ruff/flake8)
   - Type checker config (mypy/pyright with strict mode)
   - Pre-commit hooks

2. **Design APIs to align with:**
   - Item 32: Raise exceptions for errors
   - Item 35-37: Keyword-only arguments for options
   - Item 51: dataclasses for data containers
   - Item 121: Root exception for the library

3. **From the start:**
   - Item 2: Consistent style
   - Item 118: Docstrings on public APIs
   - Item 124: Full type annotations

### Brownfield (Existing Projects)
Prioritize safety and incremental progress:

1. **Before ANY refactor:**
   - Ensure tests exist for the code being changed
   - If no tests, add characterization tests first
   - Run tests to establish baseline

2. **Safe migration pattern:**
   ```python
   # Step 1: Add deprecation warning (Item 123)
   import warnings
   def old_function():
       warnings.warn(
           "old_function is deprecated, use new_function instead",
           DeprecationWarning,
           stacklevel=2
       )
       return new_function()

   # Step 2: Update callers over time
   # Step 3: Remove old function after migration period
   ```

3. **Priority order for brownfield:**
   - Priority 1 (Security) → Fix immediately
   - Add tests for risky modules
   - Priority 2 (Quick Wins) → During regular work
   - Priority 3 (Architecture) → Plan dedicated refactor cycles

---

## Test Integration Strategy

### When to Add Tests

| Situation | Action |
|-----------|--------|
| Changing code with no tests | Add characterization tests BEFORE refactoring |
| Fixing a bug | Add regression test that fails without fix |
| Refactoring with existing tests | Ensure tests still pass; add edge cases if gaps |
| Adding new behavior | Write tests first or alongside |

### Test Patterns by Item Category

**Error Handling (Items 32, 80-88):**
```python
def test_raises_on_invalid_input():
    with pytest.raises(ValueError, match="expected pattern"):
        function_under_test(invalid_input)

def test_exception_chain_preserved():
    with pytest.raises(WrapperError) as exc_info:
        function_that_wraps()
    assert exc_info.value.__cause__ is not None
```

**Concurrency (Items 67-79):**
```python
def test_thread_safety():
    results = []
    def worker():
        results.append(shared_resource.operation())

    threads = [threading.Thread(target=worker) for _ in range(100)]
    for t in threads: t.start()
    for t in threads: t.join()

    assert len(results) == 100  # No lost updates
```

**Data Structures (Items 25-29):**
```python
def test_dict_ordering_preserved():
    d = build_ordered_dict()
    assert list(d.keys()) == ["first", "second", "third"]

def test_dataclass_equality():
    obj1 = MyDataClass(x=1, y=2)
    obj2 = MyDataClass(x=1, y=2)
    assert obj1 == obj2
```

### Coverage Requirements

- **Security-critical code:** 100% branch coverage
- **Public API:** 90%+ coverage including edge cases
- **Internal utilities:** 80%+ coverage
- **Generated/boilerplate:** Can be lower if generated correctly

---

## Item Guides with Examples

### Category: Pythonic Foundations (Items 1-16)

#### Item 1: Know Which Version of Python You're Using
**Why:** Align code behavior and available language features to the minimum supported Python version.

**Refactor:** Identify the lowest supported version, remove or guard version-specific features.

**Pitfalls:** Assuming a feature exists because it works locally.

**Verify:** Run tests under all supported versions.

---

#### Item 2: Follow the PEP 8 Style Guide
**Why:** Consistent style reduces cognitive load and helps teams review code faster.

**Refactor:** Apply a formatter/linter, align naming and import order.

**Pitfalls:** Treating style as purely cosmetic; style often uncovers deeper issues.

**Verify:** Enforce formatting and lint rules in CI.

---

#### Item 3: Never Expect Python to Detect Errors at Compile Time
**Why:** Python defers most errors to runtime, so safety must be built through tests and type checks.

**Refactor:** Add tests and runtime validation, add type hints to clarify contracts.

**Pitfalls:** Relying on "it would fail to run" as a guard.

**Verify:** Exercise error paths explicitly in tests.

---

#### Item 4: Write Helper Functions Instead of Complex Expressions
**Why:** Complex expressions hide intent and are difficult to test or debug.

**Before:**
```python
result = [(x, y) for x in range(10) for y in range(10)
          if x != y and (x + y) % 2 == 0 and x * y > 10]
```

**After:**
```python
def is_valid_pair(x: int, y: int) -> bool:
    """Check if pair meets selection criteria."""
    return x != y and (x + y) % 2 == 0 and x * y > 10

result = [(x, y) for x in range(10) for y in range(10) if is_valid_pair(x, y)]
```

**Pitfalls:** Over-extracting trivial logic.

**Verify:** Ensure extracted functions preserve behavior and improve readability.

---

#### Item 5: Prefer Multiple-Assignment Unpacking over Indexing
**Why:** Unpacking documents structure and reduces indexing mistakes.

**Before:**
```python
item = get_item()
name = item[0]
price = item[1]
quantity = item[2]
```

**After:**
```python
name, price, quantity = get_item()
```

**Pitfalls:** Unpacking with mismatched lengths.

**Verify:** Add tests that validate ordering and length assumptions.

---

#### Item 6: Always Surround Single-Element Tuples with Parentheses
**Why:** A single element without a trailing comma is not a tuple.

**Before:**
```python
values = "hello"  # This is a string, not a tuple!
values = ("hello")  # Still a string!
```

**After:**
```python
values = ("hello",)  # Now it's a tuple
```

**Verify:** Add tests that validate the returned type.

---

#### Item 7: Consider Conditional Expressions for Simple Inline Logic
**Why:** Ternary expressions are concise for simple cases.

**Before:**
```python
if condition:
    x = "yes"
else:
    x = "no"
```

**After:**
```python
x = "yes" if condition else "no"
```

**Pitfalls:** Nesting conditional expressions.

---

#### Item 8: Prevent Repetition with Assignment Expressions
**Min Python:** 3.8+

**Why:** Avoid repeating expensive lookups.

**Before:**
```python
match = pattern.search(text)
if match:
    process(match.group(1))
```

**After:**
```python
if match := pattern.search(text):
    process(match.group(1))
```

**Pitfalls:** Overusing walrus in already complex expressions.

---

#### Item 9: Consider match for Destructuring in Flow Control
**Min Python:** 3.10+

**Why:** Pattern matching cleanly expresses structural branching.

**Before:**
```python
if isinstance(event, dict):
    if event.get("type") == "click":
        handle_click(event.get("x"), event.get("y"))
    elif event.get("type") == "keypress":
        handle_key(event.get("key"))
```

**After:**
```python
match event:
    case {"type": "click", "x": x, "y": y}:
        handle_click(x, y)
    case {"type": "keypress", "key": key}:
        handle_key(key)
    case _:
        raise ValueError(f"Unknown event: {event}")
```

**Pitfalls:** Overusing match for trivial cases; forgetting fallback case.

---

#### Item 10: Know the Differences Between bytes and str
**Why:** Mixing text and binary data leads to encoding bugs.

**Before:**
```python
def read_file(path):
    with open(path) as f:  # Implicit encoding
        return f.read()
```

**After:**
```python
def read_file(path: str, encoding: str = "utf-8") -> str:
    with open(path, encoding=encoding) as f:
        return f.read()

def read_binary(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()
```

**Verify:** Add tests with non-ASCII characters and binary data.

---

#### Item 11: Prefer Interpolated F-Strings
**Why:** F-strings are more readable and less error-prone.

**Before:**
```python
msg = "User %s has %d points" % (name, points)
msg = "User {} has {} points".format(name, points)
```

**After:**
```python
msg = f"User {name} has {points} points"
```

**Pitfalls:** Side effects inside f-strings.

---

#### Item 12: Understand repr vs str
**Why:** repr is for debugging, str is for user-facing output.

**Example:**
```python
@dataclass
class User:
    name: str
    email: str

    def __repr__(self) -> str:
        return f"User(name={self.name!r}, email={self.email!r})"

    def __str__(self) -> str:
        return self.name
```

---

#### Item 13: Prefer Explicit String Concatenation
**Why:** Implicit concatenation hides intent; loops need join().

**Before:**
```python
# Implicit concatenation (surprising)
items = [
    "apple"
    "banana"  # Missing comma - these concatenate!
    "cherry"
]

# Quadratic performance
result = ""
for item in items:
    result += item + ", "
```

**After:**
```python
items = [
    "apple",
    "banana",
    "cherry",
]

result = ", ".join(items)
```

---

#### Item 14: Know How to Slice Sequences
**Why:** Slicing is powerful but can hide off-by-one errors.

**Best practices:**
```python
# Prefer explicit over implicit
first_three = items[:3]
last_three = items[-3:]
middle = items[1:-1]

# Named slices for reuse
HEADER = slice(0, 10)
BODY = slice(10, -5)
data_header = raw_data[HEADER]
```

---

#### Item 15: Avoid Striding and Slicing Together
**Why:** Combining them reduces readability.

**Before:**
```python
reversed_every_other = items[::-2]  # Confusing
```

**After:**
```python
reversed_items = items[::-1]
every_other = reversed_items[::2]
```

---

#### Item 16: Prefer Catch-All Unpacking over Slicing
**Why:** Catch-all unpacking is explicit about structure.

**Before:**
```python
first = items[0]
rest = items[1:]
last = items[-1]
middle = items[1:-1]
```

**After:**
```python
first, *rest = items
*rest, last = items
first, *middle, last = items
```

---

### Category: Iteration & Comprehensions (Items 17-24, 40-47)

#### Item 17: Prefer enumerate over range
**Why:** enumerate avoids index errors.

**Before:**
```python
for i in range(len(items)):
    print(f"{i}: {items[i]}")
```

**After:**
```python
for i, item in enumerate(items):
    print(f"{i}: {item}")

# Start at 1 for user-facing numbering
for i, item in enumerate(items, start=1):
    print(f"{i}. {item}")
```

---

#### Item 18: Use zip to Process Iterators in Parallel
**Why:** zip expresses parallel iteration cleanly.

**Before:**
```python
for i in range(len(names)):
    print(f"{names[i]}: {scores[i]}")
```

**After:**
```python
for name, score in zip(names, scores):
    print(f"{name}: {score}")

# Python 3.10+: strict mode catches length mismatches
for name, score in zip(names, scores, strict=True):
    print(f"{name}: {score}")
```

---

#### Item 19: Avoid else Blocks After Loops
**Why:** Loop-else is often misunderstood.

**Before:**
```python
for item in items:
    if matches(item):
        result = item
        break
else:
    result = None  # Confusing: runs when loop completes normally
```

**After:**
```python
def find_match(items):
    for item in items:
        if matches(item):
            return item
    return None

result = find_match(items)
```

---

#### Item 20: Never Use Loop Variables After the Loop
**Why:** Loop variables can be undefined or misleading.

**Before:**
```python
for user in users:
    if user.is_admin:
        break
# user might be last user, not admin!
do_something(user)
```

**After:**
```python
admin = None
for user in users:
    if user.is_admin:
        admin = user
        break

if admin:
    do_something(admin)
```

---

#### Item 21: Be Defensive When Iterating Over Arguments
**Why:** Iterators can only be consumed once.

**Before:**
```python
def process(items):  # items might be an iterator
    total = sum(items)  # Consumes iterator
    for item in items:  # Empty! Iterator exhausted
        ...
```

**After:**
```python
def process(items):
    items = list(items)  # Materialize once
    total = sum(items)
    for item in items:
        ...
```

---

#### Item 22: Never Modify Containers While Iterating
**Why:** Mutating during iteration can skip elements or raise errors.

**Before:**
```python
for key in d:
    if should_remove(key):
        del d[key]  # RuntimeError!
```

**After:**
```python
keys_to_remove = [k for k in d if should_remove(k)]
for key in keys_to_remove:
    del d[key]

# Or build new container
d = {k: v for k, v in d.items() if not should_remove(k)}
```

---

#### Item 23: Use any and all for Short-Circuit Logic
**Why:** any/all make intent clear and stop early.

**Before:**
```python
found = False
for item in items:
    if matches(item):
        found = True
        break
```

**After:**
```python
found = any(matches(item) for item in items)
all_valid = all(is_valid(item) for item in items)
```

---

#### Item 24: Consider itertools
**Why:** itertools provides optimized iterator utilities.

**Examples:**
```python
from itertools import chain, groupby, islice, cycle, accumulate

# Chaining iterables
all_items = chain(list1, list2, list3)

# Grouping (requires sorted input!)
sorted_data = sorted(data, key=lambda x: x.category)
for category, group in groupby(sorted_data, key=lambda x: x.category):
    process_category(category, list(group))

# Sliding window (Python 3.10+)
from itertools import pairwise
for prev, curr in pairwise(items):
    compare(prev, curr)
```

---

#### Item 40: Use Comprehensions Instead of map and filter
**Why:** Comprehensions are more readable.

**Before:**
```python
squares = list(map(lambda x: x**2, numbers))
evens = list(filter(lambda x: x % 2 == 0, numbers))
```

**After:**
```python
squares = [x**2 for x in numbers]
evens = [x for x in numbers if x % 2 == 0]
```

---

#### Item 41: Avoid Complex Comprehensions
**Why:** Complex comprehensions are hard to read and debug.

**Before:**
```python
result = [transform(x, y) for x in xs for y in ys if pred1(x) and pred2(y) and pred3(x, y)]
```

**After:**
```python
def valid_pairs(xs, ys):
    for x in xs:
        if not pred1(x):
            continue
        for y in ys:
            if pred2(y) and pred3(x, y):
                yield x, y

result = [transform(x, y) for x, y in valid_pairs(xs, ys)]
```

---

#### Item 42: Reduce Repetition with Assignment Expressions in Comprehensions
**Min Python:** 3.8+

**Before:**
```python
results = [transform(expensive(x)) for x in items if expensive(x) > threshold]
# expensive(x) called twice!
```

**After:**
```python
results = [transform(y) for x in items if (y := expensive(x)) > threshold]
```

---

#### Item 43: Consider Generators Instead of Returning Lists
**Why:** Generators avoid unnecessary memory use.

**Before:**
```python
def read_lines(path):
    with open(path) as f:
        return [line.strip() for line in f]  # All in memory
```

**After:**
```python
def read_lines(path):
    with open(path) as f:
        for line in f:
            yield line.strip()

# Or for simple transforms
def read_lines(path):
    with open(path) as f:
        yield from (line.strip() for line in f)
```

---

#### Item 44: Generator Expressions for Large Data
**Why:** Generator expressions avoid building intermediate lists.

**Before:**
```python
sum([x**2 for x in range(1000000)])  # Creates list of 1M items
```

**After:**
```python
sum(x**2 for x in range(1000000))  # Streams values
```

---

#### Item 45: Compose Generators with yield from
**Why:** yield from simplifies delegation.

**Before:**
```python
def all_items():
    for item in list1:
        yield item
    for item in list2:
        yield item
```

**After:**
```python
def all_items():
    yield from list1
    yield from list2
```

---

#### Item 46: Pass Iterators into Generators (Not send)
**Why:** send complicates control flow.

**Prefer:** Design generators to accept iterators as arguments rather than using send().

---

#### Item 47: Use Classes Instead of Generator throw
**Why:** throw-based control flow is opaque.

**Prefer:** Implement state machines as classes with explicit methods.

---

### Category: Dictionaries & Data Structures (Items 25-31)

#### Item 25: Be Cautious with Dictionary Ordering
**Why:** Dict order is guaranteed (3.7+) but relying on it without documentation is fragile.

**Best practice:**
```python
# Document when order matters
# Processing order: auth first, then validation, then transform
pipeline = {
    "auth": auth_middleware,
    "validation": validate_middleware,
    "transform": transform_middleware,
}
```

---

#### Item 26: Prefer get Over in+KeyError
**Why:** dict.get is concise and avoids double lookups.

**Before:**
```python
if key in d:
    value = d[key]
else:
    value = default
```

**After:**
```python
value = d.get(key, default)

# When None is a valid value, use sentinel
MISSING = object()
value = d.get(key, MISSING)
if value is MISSING:
    handle_missing()
```

---

#### Item 27: Prefer defaultdict Over setdefault
**Why:** defaultdict reduces boilerplate.

**Before:**
```python
d = {}
for item in items:
    key = item.category
    if key not in d:
        d[key] = []
    d[key].append(item)
```

**After:**
```python
from collections import defaultdict
d = defaultdict(list)
for item in items:
    d[item.category].append(item)
```

---

#### Item 28: Use __missing__ for Key-Dependent Defaults
**Why:** __missing__ allows defaults based on the key itself.

**Example:**
```python
class FileCache(dict):
    def __missing__(self, path):
        with open(path) as f:
            self[path] = f.read()
        return self[path]

cache = FileCache()
content = cache["/etc/hosts"]  # Loaded and cached
```

---

#### Item 29: Classes Over Nested Dicts
**Why:** Deeply nested primitives obscure meaning.

**Before:**
```python
user = {
    "name": "Alice",
    "address": {
        "street": "123 Main",
        "city": "Boston",
        "location": {
            "lat": 42.36,
            "lng": -71.06
        }
    }
}
city = user["address"]["city"]  # No type safety
```

**After:**
```python
@dataclass
class Location:
    lat: float
    lng: float

@dataclass
class Address:
    street: str
    city: str
    location: Location

@dataclass
class User:
    name: str
    address: Address

user = User(
    name="Alice",
    address=Address(
        street="123 Main",
        city="Boston",
        location=Location(lat=42.36, lng=-71.06)
    )
)
city = user.address.city  # Type-checked!
```

---

#### Item 30: Know That Arguments Can Be Mutated
**Why:** Mutating inputs surprises callers.

**Before:**
```python
def add_defaults(config):
    config["timeout"] = config.get("timeout", 30)  # Mutates input!
    return config
```

**After:**
```python
def add_defaults(config):
    result = config.copy()  # Or dict(config)
    result["timeout"] = result.get("timeout", 30)
    return result
```

---

#### Item 31: Return Result Objects Over Long Tuples
**Why:** Long tuples are error-prone.

**Before:**
```python
def analyze(data):
    return mean, median, mode, std_dev, variance, count

m, med, mo, s, v, c = analyze(data)  # Easy to mix up
```

**After:**
```python
@dataclass
class AnalysisResult:
    mean: float
    median: float
    mode: float
    std_dev: float
    variance: float
    count: int

def analyze(data) -> AnalysisResult:
    return AnalysisResult(...)

result = analyze(data)
print(result.mean)  # Clear and extensible
```

---

### Category: Functions & Arguments (Items 32-39)

#### Item 32: Raise Exceptions, Don't Return None
**Why:** Exceptions make failures explicit.

**Before:**
```python
def find_user(user_id):
    user = db.query(user_id)
    if not user:
        return None  # Caller might forget to check!
    return user
```

**After:**
```python
class UserNotFoundError(Exception):
    pass

def find_user(user_id):
    user = db.query(user_id)
    if not user:
        raise UserNotFoundError(f"No user with id {user_id}")
    return user
```

---

#### Item 33: Closures and Variable Scope
**Why:** Python's late binding can cause unexpected values.

**Before:**
```python
def create_multipliers():
    return [lambda x: x * i for i in range(5)]

multipliers = create_multipliers()
[m(2) for m in multipliers]  # [8, 8, 8, 8, 8] - all use i=4!
```

**After:**
```python
def create_multipliers():
    return [lambda x, i=i: x * i for i in range(5)]

multipliers = create_multipliers()
[m(2) for m in multipliers]  # [0, 2, 4, 6, 8] - correct!
```

---

#### Item 34: Use *args for Variable Positional Arguments
**Why:** *args simplifies APIs that accept flexible inputs.

**Example:**
```python
def log(message, *values):
    if values:
        message = message % values
    print(message)

log("Simple message")
log("Value: %s, Count: %d", "test", 42)
```

---

#### Item 35: Use Keyword Arguments for Optional Behavior
**Why:** Keyword arguments are self-documenting.

**Before:**
```python
def connect(host, port, True, False, True)  # What do these mean?
```

**After:**
```python
def connect(host, port, *, use_ssl=False, verify_cert=True, timeout=30):
    ...

connect("example.com", 443, use_ssl=True, verify_cert=True)
```

---

#### Item 36: Use None for Dynamic Default Arguments
**Why:** Mutable defaults leak state.

**Before:**
```python
def append_to(element, to=[]):  # DANGER!
    to.append(element)
    return to

append_to(1)  # [1]
append_to(2)  # [1, 2] - shared list!
```

**After:**
```python
def append_to(element, to=None):
    """Append element to list.

    Args:
        element: Item to append
        to: List to append to. Defaults to new empty list.
    """
    if to is None:
        to = []
    to.append(element)
    return to
```

---

#### Item 37: Keyword-Only and Positional-Only Arguments
**Min Python:** 3.8+ for positional-only

**Example:**
```python
def safe_divide(
    numerator,      # positional or keyword
    denominator,    # positional or keyword
    /,              # everything before is positional-only
    *,              # everything after is keyword-only
    round_digits=None
):
    result = numerator / denominator
    if round_digits is not None:
        result = round(result, round_digits)
    return result

safe_divide(10, 3, round_digits=2)  # OK
safe_divide(numerator=10, denominator=3)  # Error: positional-only
```

---

#### Item 38: functools.wraps for Decorators
**Why:** wraps preserves metadata.

**Before:**
```python
def timer(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        print(f"{func.__name__} took {time.time() - start:.2f}s")
        return result
    return wrapper
# wrapper.__name__ == 'wrapper', not original function name!
```

**After:**
```python
from functools import wraps

def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        print(f"{func.__name__} took {time.time() - start:.2f}s")
        return result
    return wrapper
# wrapper.__name__ == original function name
```

---

#### Item 39: Prefer functools.partial Over Lambda
**Why:** partial is clearer and picklable.

**Before:**
```python
callback = lambda x: process(x, config=default_config)
```

**After:**
```python
from functools import partial
callback = partial(process, config=default_config)
```

---

### Category: Classes & OOP (Items 48-66)

#### Item 48: Functions for Simple Interfaces
**Why:** Functions are lighter-weight for simple behavior.

**Prefer functions when:**
- No state is needed between calls
- Single method would be named `__call__` anyway
- Simplicity matters more than extensibility

---

#### Item 49: Polymorphism Over isinstance
**Why:** Behavior belongs with data types.

**Before:**
```python
def calculate_area(shape):
    if isinstance(shape, Circle):
        return math.pi * shape.radius ** 2
    elif isinstance(shape, Rectangle):
        return shape.width * shape.height
    elif isinstance(shape, Triangle):
        return 0.5 * shape.base * shape.height
```

**After:**
```python
from typing import Protocol

class Shape(Protocol):
    def area(self) -> float: ...

@dataclass
class Circle:
    radius: float
    def area(self) -> float:
        return math.pi * self.radius ** 2

@dataclass
class Rectangle:
    width: float
    height: float
    def area(self) -> float:
        return self.width * self.height

def calculate_area(shape: Shape) -> float:
    return shape.area()
```

---

#### Item 50: singledispatch for Functional Polymorphism
**Why:** singledispatch enables type-based behavior without modifying classes.

**Example:**
```python
from functools import singledispatch

@singledispatch
def serialize(obj):
    raise TypeError(f"Cannot serialize {type(obj)}")

@serialize.register
def _(obj: str) -> dict:
    return {"type": "string", "value": obj}

@serialize.register
def _(obj: int) -> dict:
    return {"type": "integer", "value": obj}

@serialize.register
def _(obj: list) -> dict:
    return {"type": "array", "items": [serialize(x) for x in obj]}
```

---

#### Item 51: dataclasses for Lightweight Classes
**Why:** dataclasses reduce boilerplate.

**Before:**
```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        return f"Point(x={self.x}, y={self.y})"

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y
```

**After:**
```python
from dataclasses import dataclass

@dataclass
class Point:
    x: float
    y: float
```

---

#### Item 52: @classmethod for Generic Construction
**Why:** classmethod constructors respect inheritance.

**Example:**
```python
@dataclass
class Config:
    host: str
    port: int

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            host=os.environ.get("HOST", "localhost"),
            port=int(os.environ.get("PORT", "8080"))
        )

    @classmethod
    def from_file(cls, path: str) -> "Config":
        with open(path) as f:
            data = json.load(f)
        return cls(**data)
```

---

#### Item 53: Initialize Parents with super()
**Why:** super supports cooperative multiple inheritance.

**Before:**
```python
class Child(Parent):
    def __init__(self, x, y):
        Parent.__init__(self, x)  # Breaks with multiple inheritance
        self.y = y
```

**After:**
```python
class Child(Parent):
    def __init__(self, x, y):
        super().__init__(x)
        self.y = y
```

---

#### Item 54: Mix-in Classes
**Why:** Mixins enable reusable behavior.

**Example:**
```python
class JsonMixin:
    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, json_str: str):
        return cls(**json.loads(json_str))

@dataclass
class User(JsonMixin):
    name: str
    email: str

user = User.from_json('{"name": "Alice", "email": "alice@example.com"}')
```

---

#### Item 55: Public Attributes Over Private
**Why:** Public attributes are Pythonic.

**Convention:**
- `attribute` - Public API
- `_attribute` - Internal, but accessible (convention)
- `__attribute` - Name mangling (rarely needed)

---

#### Item 56: Frozen dataclasses for Immutability
**Why:** Immutable objects reduce bugs.

**Example:**
```python
@dataclass(frozen=True)
class Point:
    x: float
    y: float

    def moved(self, dx: float, dy: float) -> "Point":
        return Point(self.x + dx, self.y + dy)
```

---

#### Item 57: collections.abc for Custom Containers
**Why:** ABCs provide standard interfaces.

**Example:**
```python
from collections.abc import MutableMapping

class CaseInsensitiveDict(MutableMapping):
    def __init__(self, data=None):
        self._store = {}
        if data:
            self.update(data)

    def __getitem__(self, key):
        return self._store[key.lower()]

    def __setitem__(self, key, value):
        self._store[key.lower()] = value

    def __delitem__(self, key):
        del self._store[key.lower()]

    def __iter__(self):
        return iter(self._store)

    def __len__(self):
        return len(self._store)
```

---

#### Items 58-61: Properties and Descriptors
**Use plain attributes** unless you need:
- Validation → use `@property`
- Computed values → use `@property`
- Reusable property logic → use descriptors
- Lazy loading → use `__getattr__`

---

#### Items 62-66: Class Customization
**Summary:**
- `__init_subclass__` → validate or register subclasses
- `__set_name__` → descriptors that know their attribute name
- Class decorators → prefer over metaclasses for extensions

---

### Category: Concurrency (Items 67-79)

#### Item 67: subprocess for Child Processes
**Why:** subprocess is safe and explicit.

**Before:**
```python
os.system(f"ls {directory}")  # Shell injection!
```

**After:**
```python
import subprocess

result = subprocess.run(
    ["ls", directory],
    capture_output=True,
    text=True,
    timeout=30,
    check=True
)
print(result.stdout)
```

---

#### Item 68-74: Threading Summary
- Threads for I/O, not CPU parallelism (GIL)
- Use `threading.Lock` for shared state
- Use `queue.Queue` for thread coordination
- Use `ThreadPoolExecutor` over manual thread creation

**Example:**
```python
from concurrent.futures import ThreadPoolExecutor

def fetch_url(url):
    return requests.get(url).text

urls = ["https://example.com", "https://example.org"]

with ThreadPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(fetch_url, urls))
```

---

#### Item 75-78: Async Summary
- Use `async`/`await` for I/O-bound concurrent operations
- Never call blocking functions in coroutines
- Use `run_in_executor` for blocking calls during migration

**Example:**
```python
import asyncio
import aiohttp

async def fetch_all(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, url) for url in urls]
        return await asyncio.gather(*tasks)

async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()

results = asyncio.run(fetch_all(urls))
```

---

#### Item 79: ProcessPoolExecutor for CPU Parallelism
**Why:** Bypasses GIL for CPU-bound work.

**Example:**
```python
from concurrent.futures import ProcessPoolExecutor

def cpu_intensive(n):
    return sum(i * i for i in range(n))

with ProcessPoolExecutor() as executor:
    results = list(executor.map(cpu_intensive, [10**6] * 4))
```

---

### Category: Error Handling (Items 80-91)

#### Item 80: try/except/else/finally
**Why:** Each block has a specific purpose.

**Example:**
```python
try:
    file = open(path)          # Only code that might raise
except FileNotFoundError:
    log.warning(f"File not found: {path}")
    return default_value
else:
    content = file.read()      # Only runs if no exception
    return process(content)
finally:
    file.close()               # Always runs
```

---

#### Item 81: assert vs raise
**Why:** Different purposes.

```python
# assert for developer assumptions (disabled with -O)
assert len(items) > 0, "items should not be empty"

# raise for runtime validation (always active)
if not items:
    raise ValueError("items must not be empty")
```

---

#### Item 82: Context Managers
**Why:** Centralize cleanup.

**Example:**
```python
from contextlib import contextmanager

@contextmanager
def temporary_directory():
    path = tempfile.mkdtemp()
    try:
        yield path
    finally:
        shutil.rmtree(path)

with temporary_directory() as tmpdir:
    # work with tmpdir
    pass
# Automatically cleaned up
```

---

#### Item 83-84: Short try Blocks
**Why:** Narrow try blocks prevent accidental catches.

**Before:**
```python
try:
    value = d[key]
    result = transform(value)  # Might also raise KeyError!
    save(result)
except KeyError:
    result = default
```

**After:**
```python
try:
    value = d[key]
except KeyError:
    value = default_value

result = transform(value)
save(result)
```

---

#### Item 85-86: Specific Exception Handling
**Why:** Broad catches hide bugs.

**Before:**
```python
try:
    do_something()
except Exception:  # Catches everything including bugs!
    pass
```

**After:**
```python
try:
    do_something()
except (ConnectionError, TimeoutError) as e:
    log.warning(f"Network error: {e}")
    return fallback_value
# Let other exceptions propagate
```

---

#### Item 87-88: Exception Chaining
**Why:** Preserve root cause.

**Example:**
```python
try:
    config = load_config(path)
except FileNotFoundError as e:
    raise ConfigurationError(f"Config file missing: {path}") from e
```

---

#### Items 89-91: Safety Items
- **Item 89:** Pass resources into generators, clean up in callers
- **Item 90:** Don't rely on `__debug__` for correctness
- **Item 91:** Avoid `exec`/`eval` unless building developer tools

---

### Category: Performance (Items 92-99)

#### Item 92-93: Profile Before Optimizing
**Why:** Measure, don't guess.

```python
# Profile first
python -m cProfile -s cumtime script.py

# Microbenchmark specific code
python -m timeit -s "setup" "code_to_test"
```

---

#### Items 94-99 Summary
- Profile to find bottlenecks
- Consider native extensions only when profiling proves need
- Use `memoryview`/`bytearray` for zero-copy binary operations
- Lazy imports for faster startup

---

### Category: Standard Library (Items 100-107)

#### Item 100-104: Sorting and Data Structures
```python
# Sorting with key
sorted(users, key=lambda u: (u.last_name, u.first_name))

# bisect for sorted sequences
import bisect
index = bisect.bisect_left(sorted_list, value)

# deque for O(1) append/pop both ends
from collections import deque
queue = deque(maxlen=100)

# heapq for priority queues
import heapq
heapq.heappush(heap, (priority, item))
```

---

#### Item 105-106: Time and Precision
```python
# Timezone-aware datetime
from datetime import datetime, timezone
now = datetime.now(timezone.utc)

# Decimal for financial calculations
from decimal import Decimal, ROUND_HALF_UP
price = Decimal("19.99")
total = (price * quantity).quantize(Decimal("0.01"), ROUND_HALF_UP)
```

---

### Category: Testing (Items 108-115)

#### Key Testing Principles
- Group related tests in TestCase subclasses
- Balance unit and integration tests
- Isolate tests with setUp/tearDown
- Mock external dependencies at usage site
- Use `assertAlmostEqual` for floats
- Remove debug artifacts before commit
- Use `tracemalloc` for memory debugging

---

### Category: Packaging & Organization (Items 116-125)

#### Item 117: Virtual Environments
```bash
# Create and activate
python -m venv .venv
source .venv/bin/activate

# Or use modern tools
uv venv
poetry install
```

---

#### Item 118: Docstrings
```python
def calculate_tax(amount: float, rate: float = 0.1) -> float:
    """Calculate tax on an amount.

    Args:
        amount: The base amount to calculate tax on.
        rate: Tax rate as decimal (default 0.1 = 10%).

    Returns:
        The calculated tax amount.

    Raises:
        ValueError: If amount is negative.

    Example:
        >>> calculate_tax(100.0, 0.15)
        15.0
    """
    if amount < 0:
        raise ValueError("Amount cannot be negative")
    return amount * rate
```

---

#### Item 121: Root Exception
**Why:** Stable error surface for library users.

```python
class MyLibraryError(Exception):
    """Base exception for mylibrary."""

class ConfigError(MyLibraryError):
    """Configuration-related errors."""

class NetworkError(MyLibraryError):
    """Network-related errors."""

# Users can catch all library errors
try:
    use_library()
except MyLibraryError as e:
    handle_library_error(e)
```

---

#### Item 122: Breaking Circular Imports
**Strategies:**
1. Move shared code to a separate module
2. Use local imports inside functions
3. Use `TYPE_CHECKING` for type hints only

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .other_module import OtherClass  # Only for type checker

def process(obj: "OtherClass") -> None:
    from .other_module import OtherClass  # Runtime import
    ...
```

---

#### Item 123: Deprecation Warnings
```python
import warnings

def old_function():
    warnings.warn(
        "old_function is deprecated, use new_function instead. "
        "Will be removed in version 2.0.",
        DeprecationWarning,
        stacklevel=2
    )
    return new_function()
```

---

#### Item 124: Type Hints
**Modern typing:**
```python
from typing import Protocol, TypeVar, Generic
from collections.abc import Callable, Iterable

T = TypeVar("T")

class Comparable(Protocol):
    def __lt__(self, other: "Comparable") -> bool: ...

def find_min(items: Iterable[T]) -> T | None:
    """Find minimum item, or None if empty."""
    ...

# Run type checker
# mypy --strict src/
# pyright src/
```

---

## Checklist for Completeness

Before finishing a refactoring session, verify:

- [ ] All Priority 1 issues addressed in touched files
- [ ] Tests pass
- [ ] Type checker passes (if project uses types)
- [ ] Formatter/linter passes
- [ ] No new warnings introduced
- [ ] Public API preserved (or migration documented)
- [ ] Docstrings updated for changed functions
- [ ] Exceptions documented

