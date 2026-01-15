# Language-Specific Code Review Checklists

Detailed checklists for reviewing code in specific languages. Load this file when doing in-depth reviews for these languages.

---

## Python

### Security
- [ ] No `eval()`, `exec()`, or `compile()` with user input
- [ ] No `pickle.load()` with untrusted data
- [ ] No `os.system()` or `subprocess.run(..., shell=True)`
- [ ] No `assert` for security checks (disabled with -O)
- [ ] `secrets` module used instead of `random` for crypto
- [ ] SQL queries use parameterized statements
- [ ] File paths validated (no path traversal)
- [ ] YAML: `yaml.safe_load()` not `yaml.load()`

### Correctness
- [ ] No mutable default arguments: `def f(x=[])` → `def f(x=None)`
- [ ] No bare `except:` → use `except Exception:`
- [ ] Context managers for resources: `with open(...)`
- [ ] `is` for None/True/False, `==` for values
- [ ] Iteration doesn't modify collection being iterated
- [ ] Generator exhaustion handled (can only iterate once)
- [ ] `datetime` timezone-aware when needed
- [ ] String encoding explicit: `open(..., encoding='utf-8')`

### Best Practices
- [ ] Type hints on public functions
- [ ] Docstrings on public modules/classes/functions
- [ ] f-strings over `.format()` or `%`
- [ ] `enumerate()` over `range(len())`
- [ ] `pathlib.Path` over `os.path`
- [ ] `dataclasses` or `pydantic` for data containers
- [ ] `logging` over `print` for apps
- [ ] Constants in UPPER_SNAKE_CASE

### Testing
- [ ] pytest fixtures for setup/teardown
- [ ] `@pytest.mark.parametrize` for variations
- [ ] Mocking external services/APIs
- [ ] Exception testing with `pytest.raises`
- [ ] Async tests with `pytest-asyncio`

---

## JavaScript / TypeScript

### Security
- [ ] No `eval()` or `new Function()` with user input
- [ ] No `innerHTML` with unsanitized content → use `textContent`
- [ ] No `dangerouslySetInnerHTML` without sanitization
- [ ] No `document.write()`
- [ ] Cookie: `httpOnly`, `secure`, `sameSite` flags
- [ ] CORS configured correctly
- [ ] No prototype pollution: check `__proto__`, `constructor`
- [ ] Dependencies audited: `npm audit`

### Correctness
- [ ] `===` over `==` (strict equality)
- [ ] `const`/`let` over `var`
- [ ] Nullish coalescing `??` over `||` for defaults
- [ ] Optional chaining `?.` for nullable access
- [ ] Promises have `.catch()` or try/catch with await
- [ ] Event listeners removed on cleanup
- [ ] No memory leaks (closures, timers, subscriptions)
- [ ] Array methods return new arrays (immutability)

### TypeScript Specific
- [ ] No `any` without justification
- [ ] Strict mode enabled
- [ ] Union types over type assertions
- [ ] Generics for reusable functions
- [ ] `unknown` over `any` for unknown types
- [ ] Enums or const objects for fixed values
- [ ] Proper null checks, not `!` assertions

### React Specific
- [ ] Keys on list items (not index unless static)
- [ ] `useEffect` cleanup returns
- [ ] Dependencies array complete in hooks
- [ ] `useMemo`/`useCallback` for expensive operations
- [ ] No state updates on unmounted components
- [ ] Error boundaries for graceful failures

### Testing
- [ ] Jest/Vitest patterns followed
- [ ] React Testing Library for components
- [ ] Mock external APIs/services
- [ ] Async tests properly awaited
- [ ] Snapshot tests used sparingly

---

## Go

### Security
- [ ] Errors always checked (no `_ = err`)
- [ ] Input validated before use
- [ ] SQL: use `db.Query(query, args...)` not string concat
- [ ] Crypto: use `crypto/rand` not `math/rand`
- [ ] TLS: verify certificates (no `InsecureSkipVerify`)
- [ ] File paths cleaned with `filepath.Clean()`
- [ ] HTTP timeouts set on clients and servers

### Correctness
- [ ] All errors handled or explicitly ignored with `//nolint`
- [ ] `defer` for resource cleanup
- [ ] Context cancellation checked and propagated
- [ ] No goroutine leaks (use `sync.WaitGroup` or context)
- [ ] `sync.Mutex` for shared state
- [ ] No data races (test with `-race`)
- [ ] Slices: append may reallocate (careful with sub-slices)
- [ ] Maps not safe for concurrent access

### Best Practices
- [ ] Exported names have doc comments
- [ ] Error wrapping: `fmt.Errorf("context: %w", err)`
- [ ] Accept interfaces, return structs
- [ ] Small, focused interfaces
- [ ] Table-driven tests
- [ ] `context.Context` as first parameter
- [ ] Errors are values, wrap for context

### Testing
- [ ] Table-driven tests for variations
- [ ] Subtests with `t.Run()`
- [ ] `t.Helper()` in helper functions
- [ ] `testify` for assertions if used
- [ ] Benchmarks with `b.ResetTimer()`
- [ ] Race detection in CI: `go test -race`

---

## Rust

### Security
- [ ] No `unsafe` without justification and comments
- [ ] Input validated before use
- [ ] No `unwrap()`/`expect()` on user input paths
- [ ] Crypto: use audited crates (`ring`, `rustcrypto`)
- [ ] Dependencies audited: `cargo audit`
- [ ] No panics in library code

### Correctness
- [ ] `Result` and `Option` handled properly
- [ ] Error propagation with `?` operator
- [ ] Lifetimes explicit when needed
- [ ] No unnecessary `clone()`
- [ ] `Drop` implemented for cleanup
- [ ] Thread safety: `Send`/`Sync` bounds correct
- [ ] No data races (Rust prevents most at compile time)

### Best Practices
- [ ] Doc comments on public items: `///`
- [ ] Custom error types with `thiserror`
- [ ] `clippy` lints addressed
- [ ] Derive macros: `Debug`, `Clone`, `PartialEq` where appropriate
- [ ] Builder pattern for complex construction
- [ ] Iterators over manual loops
- [ ] `#[must_use]` on functions with important return values

### Testing
- [ ] Unit tests in same file: `#[cfg(test)]`
- [ ] Integration tests in `tests/` directory
- [ ] Doc tests for examples
- [ ] Property-based testing with `proptest` if appropriate

---

## SQL

### Security
- [ ] All queries parameterized (no string concatenation)
- [ ] Least privilege: minimal permissions for each role
- [ ] No dynamic table/column names from user input
- [ ] Audit logging for sensitive operations
- [ ] Sensitive data encrypted at rest
- [ ] Connection strings not in code

### Correctness
- [ ] Transactions for multi-statement operations
- [ ] Proper isolation levels
- [ ] Constraints: NOT NULL, FOREIGN KEY, UNIQUE, CHECK
- [ ] Default values explicit
- [ ] NULL handling: use `COALESCE` or `IS NULL`
- [ ] Date/time types appropriate for use case

### Performance
- [ ] Indexes on frequently queried columns
- [ ] Indexes on foreign key columns
- [ ] No `SELECT *` in production code
- [ ] `EXPLAIN ANALYZE` for complex queries
- [ ] Pagination: `LIMIT` and `OFFSET` or cursor-based
- [ ] Batch operations for bulk inserts/updates
- [ ] Connection pooling configured

### Best Practices
- [ ] Consistent naming: snake_case for tables/columns
- [ ] Migrations versioned and reversible
- [ ] Soft deletes if audit trail needed
- [ ] Created/updated timestamps on tables
- [ ] UUID vs auto-increment considered

---

## Java

### Security
- [ ] No SQL string concatenation → use PreparedStatement
- [ ] No `Runtime.exec()` with user input
- [ ] No unsafe deserialization
- [ ] Input validation on all boundaries
- [ ] Secrets not in code or logs
- [ ] HTTPS enforced for external calls

### Correctness
- [ ] Null checks: `Objects.requireNonNull()` or Optional
- [ ] Resources closed: try-with-resources
- [ ] Thread safety: synchronized or concurrent collections
- [ ] Equals/hashCode contract maintained
- [ ] Immutability preferred
- [ ] Exception handling: don't catch `Throwable`

### Best Practices
- [ ] Javadoc on public APIs
- [ ] Records for data classes (Java 16+)
- [ ] `var` for local variables with clear types
- [ ] Streams over explicit loops where clearer
- [ ] Dependency injection for testability
- [ ] Final classes/methods unless extension needed

---

## C/C++

### Security
- [ ] No buffer overflows: bounds checking everywhere
- [ ] No `gets()`, use `fgets()` or safer alternatives
- [ ] No format string vulnerabilities: `printf(var)` → `printf("%s", var)`
- [ ] Memory freed exactly once (no double-free)
- [ ] Pointers nulled after free
- [ ] Integer overflow checked
- [ ] Stack canaries, ASLR enabled

### Correctness
- [ ] All memory freed (use valgrind/ASan)
- [ ] No use-after-free
- [ ] No uninitialized variables
- [ ] Pointer arithmetic bounds checked
- [ ] Return values checked
- [ ] Resource cleanup in all paths (RAII in C++)

### C++ Specific
- [ ] Smart pointers over raw pointers
- [ ] `const` correctness
- [ ] Rule of 5/0 for resource management
- [ ] `override` keyword on virtual functions
- [ ] `noexcept` where exceptions won't be thrown
- [ ] Range-based for loops
- [ ] `std::string_view` for non-owning strings
