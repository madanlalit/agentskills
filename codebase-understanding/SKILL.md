---
name: codebase-understanding
description: Systematically analyze and understand any codebase. Use when: exploring unfamiliar projects, onboarding to new codebases, tracing features or bugs, documenting architecture, analyzing dependencies, planning refactors, or conducting technical due diligence. Supports all major languages and project types.
---

# Codebase Understanding Skill

## Objective
Systematically analyze and comprehend unfamiliar codebases through progressive discovery, pattern recognition, and structured documentation. Transform a complex codebase into a clear mental model of its architecture, components, data flows, and key patterns.

---

## Quick Start Workflow

```
1. INITIAL RECONNAISSANCE (5-10 min)
   ├── Read README and documentation
   ├── Identify tech stack and dependencies
   ├── Map directory structure
   └── Find entry points and main files

2. ARCHITECTURE MAPPING (10-20 min)
   ├── Identify project type and patterns
   ├── Map major components/modules
   ├── Understand separation of concerns
   └── Document high-level architecture

3. DEEP DIVE (20-40 min per component)
   ├── Trace key user flows
   ├── Map data models and schemas
   ├── Understand API boundaries
   └── Identify configuration points

4. DOCUMENTATION (ongoing)
   ├── Create architecture diagram
   ├── Document component relationships
   ├── Map data flows
   └── Note important patterns and gotchas

5. VERIFICATION
   ├── Run the application locally
   ├── Execute tests to see coverage
   ├── Verify understanding with targeted questions
   └── Update documentation with learnings
```

---

## Discovery Strategies

### Phase 1: Project Overview (Start Here)

**Essential Files to Check:**
```bash
# Documentation
README.md, CONTRIBUTING.md, docs/

# Configuration
package.json, requirements.txt, go.mod, Cargo.toml, pom.xml
.env.example, config/, settings.py

# Build & Deploy
Makefile, Dockerfile, docker-compose.yml, .github/workflows/
setup.py, pyproject.toml, tsconfig.json

# Tests
tests/, test/, __tests__, *_test.go, *.spec.ts
pytest.ini, jest.config.js
```

**Quick Analysis Commands:**
```bash
# Get file counts by type
find . -type f | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -20

# Find main entry points
find . -name "main.*" -o -name "index.*" -o -name "app.*" -o -name "__init__.py"

# Identify frameworks/libraries
cat package.json requirements.txt go.mod Cargo.toml pom.xml 2>/dev/null | head -50

# Find configuration files
find . -name "*.config.*" -o -name "*rc" -o -name "*.yml" -o -name "*.yaml" | head -20
```

**Use Automated Script:**
```bash
./scripts/analyze-structure.sh /path/to/codebase
```

### Phase 2: Architecture Identification

**Project Type Patterns:**

| Pattern | Indicators | Key Files |
|---------|-----------|-----------|
| **Web App (Frontend)** | React/Vue/Angular components | `src/components/`, `public/`, `index.html` |
| **Web App (Backend)** | Routes, controllers, models | `routes/`, `controllers/`, `models/`, `api/` |
| **REST API** | Endpoints, OpenAPI specs | `api/`, `routes/`, `swagger.yaml` |
| **GraphQL API** | Schema, resolvers | `schema.graphql`, `resolvers/` |
| **CLI Tool** | Command definitions, arg parsing | `cmd/`, `cli/`, `commands/` |
| **Library/SDK** | Public API, examples | `src/`, `lib/`, `examples/`, `index.ts` |
| **Microservice** | Service boundaries, messaging | `services/`, message queues, gRPC |
| **Monorepo** | Multiple packages/apps | `packages/`, `apps/`, workspaces |
| **Data Pipeline** | ETL, jobs, workflows | `jobs/`, `pipelines/`, Airflow DAGs |

**Architecture Styles:**

```bash
# Monolithic patterns
rg -l "class.*Controller|def.*view|@app.route" --type py
rg -l "class.*Service|interface.*Repository" --type java

# Microservices patterns
rg -l "grpc|protobuf|kafka|rabbitmq|nats"
find . -name "service.yaml" -o -name "deployment.yaml"

# Event-driven patterns
rg -l "event.*emitter|publish|subscribe|on\(|addEventListener"

# Layered architecture
ls -la src/ | grep -E "(controllers?|services?|repositories?|models?|views?)"
```

### Phase 3: Component Deep Dive

**For Each Major Component:**

1. **Entry Points**
   ```bash
   # Web: Routes/endpoints
   rg "(@app.route|@router|app.get|app.post|Route)" --type py --type js --type go
   
   # CLI: Commands
   rg "(command|subcommand|flag|arg)" cmd/ cli/
   
   # Background: Jobs/workers
   rg "(task|job|worker|celery|sidekiq)" 
   ```

2. **Data Models**
   ```bash
   # Database models
   rg "(class.*Model|Schema|Entity|@entity)" models/ entities/
   
   # ORMs
   rg "(sequelize|mongoose|sqlalchemy|gorm|diesel)" 
   
   # Schema files
   find . -name "schema.*" -o -name "migrations/" -o -name "*.prisma"
   ```

3. **Business Logic**
   ```bash
   # Services/use cases
   find . -path "*/services/*" -o -path "*/usecases/*" -o -path "*/domain/*"
   
   # Core algorithms
   rg "class.*Service|class.*Handler|class.*Processor"
   ```

4. **External Dependencies**
   ```bash
   # API clients
   rg "(requests\.|axios|fetch|http\.get|http\.post)" 
   
   # Database connections
   rg "(connect|createConnection|newDB|sql\.open)"
   
   # Message queues
   rg "(kafka|rabbitmq|redis|sqs|pubsub)"
   ```

---

## Language-Specific Patterns

### Python

**Structure Discovery:**
```bash
# Find packages
find . -name "__init__.py" -type f | sed 's/__init__.py//' 

# Main entry points
find . -name "__main__.py" -o -name "main.py" -o -name "app.py"

# Django/Flask apps
rg "Django|Flask|FastAPI|from django|from flask|from fastapi"

# Key patterns
rg "class.*\(.*\):|def |@decorator|if __name__"
```

**Important Conventions:**
- `__init__.py` - Package marker
- `settings.py` / `config.py` - Configuration
- `models.py` - Data models
- `views.py` / `routes.py` - Request handlers
- `forms.py` - Form definitions
- `serializers.py` - Data serialization
- `tasks.py` - Background jobs (Celery)
- `tests/test_*.py` - Tests

### JavaScript/TypeScript

**Structure Discovery:**
```bash
# Entry points
find . -name "index.js" -o -name "index.ts" -o -name "main.js" -o -name "app.js"

# Module types
cat package.json | jq '.type' # "module" or "commonjs"

# Framework detection
rg "from 'react'|from 'vue'|from 'angular'|from 'next'|from 'express'"

# Key patterns
rg "export |import |class |function |const.*=.*\(|interface "
```

**Important Conventions:**
- `index.ts/js` - Module entry point
- `package.json` - Dependencies and scripts
- `tsconfig.json` - TypeScript configuration
- `src/` - Source code
- `dist/` or `build/` - Compiled output
- `components/` - React/Vue components
- `routes/` or `pages/` - Routing
- `*.test.ts` / `*.spec.ts` - Tests

### Go

**Structure Discovery:**
```bash
# Module and packages
cat go.mod
find . -name "*.go" -type f | xargs dirname | sort -u

# Main packages
rg "^package main" --type go

# Key patterns
rg "func |type |interface |struct |package " --type go
```

**Important Conventions:**
- `main.go` - Entry point
- `go.mod` / `go.sum` - Dependencies
- `cmd/` - Main applications
- `pkg/` - Public libraries
- `internal/` - Private code
- `*_test.go` - Tests

### Rust

**Structure Discovery:**
```bash
# Cargo workspace
cat Cargo.toml

# Modules
rg "^mod |^pub mod |^use " --type rust

# Entry point
cat src/main.rs src/lib.rs
```

**Important Conventions:**
- `Cargo.toml` - Package manifest
- `src/main.rs` - Binary entry
- `src/lib.rs` - Library entry
- `src/bin/` - Multiple binaries
- `tests/` - Integration tests
- `benches/` - Benchmarks

### Java

**Structure Discovery:**
```bash
# Maven/Gradle
cat pom.xml build.gradle

# Package structure
find . -name "*.java" | sed 's|/[^/]*\.java||' | sort -u

# Spring Boot
rg "@SpringBootApplication|@RestController|@Service|@Repository" --type java
```

**Important Conventions:**
- `src/main/java/` - Source code
- `src/main/resources/` - Configuration
- `src/test/java/` - Tests
- `Application.java` - Spring Boot entry
- `pom.xml` / `build.gradle` - Dependencies

---

## Analysis Checkpoints

### Security & Auth
```bash
# Authentication
rg "authenticate|login|logout|session|jwt|token|passport"

# Authorization
rg "authorize|permission|role|@requires|@secured|middleware.*auth"

# Secrets management
rg "process\.env|os\.getenv|ENV\[|config\.|dotenv"
find . -name ".env.example" -o -name "secrets.yaml"
```

### Database & Storage
```bash
# Schema
find . -name "schema.sql" -o -name "models.py" -o -name "*.prisma"
find . -path "*/migrations/*"

# ORM/Query builders
rg "sequelize|typeorm|mongoose|sqlalchemy|diesel|gorm|prisma"

# Database connections
rg "createConnection|connect.*mongo|pool|db\.connect"
```

### API Design
```bash
# REST endpoints
rg "@(Get|Post|Put|Delete|Patch)|@app\.(get|post)|router\.(get|post)"

# GraphQL
find . -name "*.graphql" -o -name "schema.gql"
rg "type Query|type Mutation|resolvers"

# API documentation
find . -name "openapi.yaml" -o -name "swagger.json"
rg "@api|@swagger"
```

### Configuration
```bash
# Environment variables
rg "process\.env\.|os\.getenv|ENV\[" | cut -d: -f1 | sort -u
find . -name ".env.example"

# Config files
find . -name "config.yaml" -o -name "settings.json" -o -name "*.toml"

# Feature flags
rg "feature.*flag|toggle|experiment"
```

### Error Handling
```bash
# Error patterns
rg "try.*catch|except|Result<|Error|panic|throw new"

# Logging
rg "logger|log\.|console\.(log|error|warn)|print|fmt\.Print"

# Monitoring
rg "sentry|datadog|newrelic|prometheus|opentelemetry"
```

### Testing Strategy
```bash
# Test files
find . -name "*test*" -o -name "*spec*" | head -20

# Test frameworks
rg "pytest|jest|mocha|junit|testify|cargo test"

# Coverage
find . -name ".coverage" -o -name "coverage/"
cat package.json | jq '.scripts.test'
```

### Build & Deploy
```bash
# Build systems
find . -name "Makefile" -o -name "build.sh" -o -name "Dockerfile"

# CI/CD
find . -path "*/.github/workflows/*" -o -path "*/.gitlab-ci.yml"

# Package/Docker
cat Dockerfile docker-compose.yml

# Scripts
cat package.json | jq '.scripts'
```

---

## Data Flow Tracing

**Trace a Request/Flow:**

1. **Find Entry Point**
   ```bash
   # Web: Find route definition
   rg "'/api/users'" routes/ api/
   
   # CLI: Find command
   rg "command.*'create'|@click.command"
   ```

2. **Follow the Call Chain**
   - Controller/Handler → Service → Repository → Database
   - Use IDE "Go to Definition" or:
   ```bash
   rg "def process_user|function processUser|func ProcessUser"
   ```

3. **Map Data Transformations**
   - Request → DTO → Domain Model → Entity → Database
   - Track validation, serialization, transformation

4. **Identify Side Effects**
   ```bash
   # External calls
   rg "requests\.|fetch\(|http\." file_with_logic.py
   
   # Database writes
   rg "save\(|insert|update|delete|commit"
   
   # Events/Messages
   rg "publish|emit|send.*message|trigger"
   ```

---

## Automated Analysis Tools

### Structure Analysis Script
```bash
./scripts/analyze-structure.sh /path/to/codebase
```

Outputs:
- File count by language
- Directory structure visualization
- Entry point identification
- Configuration file listing
- Test coverage overview

### Dependency Mapping Script
```bash
./scripts/map-dependencies.sh /path/to/codebase
```

Outputs:
- External dependencies with versions
- Internal module dependency graph
- Circular dependency detection
- Unused dependency warnings

---

## Documentation Templates

After analysis, use these templates to document findings:

### Architecture Overview
See: [examples/architecture-template.md](examples/architecture-template.md)

Contents:
- System architecture diagram
- Component descriptions
- Technology stack
- Data flow overview
- Key design decisions

### Component Map
See: [examples/component-map.template.md](examples/component-map-template.md)

Contents:
- Component relationship matrix
- Interface definitions
- Dependency graph
- Responsibility mapping

---

## Context-Specific Analysis

### Onboarding (Comprehensive Understanding)
**Goal:** Build complete mental model

Priority:
1. Run the application locally
2. Understand the "happy path" user flows
3. Map all major components
4. Read architecture docs and ADRs
5. Run and read tests

Time: 2-4 hours for medium codebase

### Bug Investigation (Targeted Analysis)
**Goal:** Understand specific failure

Priority:
1. Reproduce the bug
2. Read error logs and stack traces
3. Trace the failing flow end-to-end
4. Examine related tests
5. Check recent changes (git blame/log)

Time: 20-60 minutes

### Feature Addition (Impact Analysis)
**Goal:** Understand where and how to add feature

Priority:
1. Find similar existing features
2. Map affected components
3. Identify integration points
4. Review testing requirements
5. Check for configuration changes

Time: 30-90 minutes

### Refactoring (Structural Understanding)
**Goal:** Understand current design to improve it

Priority:
1. Map current component boundaries
2. Identify coupling and dependencies
3. Understand data flows
4. Review test coverage
5. Identify technical debt

Time: 1-3 hours

### Security Audit (Attack Surface Mapping)
**Goal:** Identify security vulnerabilities

Priority:
1. Map all input boundaries
2. Trace authentication flows
3. Review authorization checks
4. Check secret management
5. Examine data validation

Time: 2-4 hours

---

## Common Codebase Patterns

### MVC (Model-View-Controller)
```
models/         - Data structures
views/          - Templates/UI
controllers/    - Request handlers
```

### Clean/Hexagonal Architecture
```
domain/         - Business logic (pure)
application/    - Use cases
infrastructure/ - External integrations
interfaces/     - Controllers, presenters
```

### Microservices
```
services/
  ├── user-service/
  ├── order-service/
  └── payment-service/
shared/         - Common libraries
infrastructure/ - K8s, configs
```

### Repository Pattern
```
repositories/   - Data access layer
services/       - Business logic
controllers/    - API layer
models/         - Domain entities
```

---

## Quick Reference Commands

### Find All Functions/Classes
```bash
# Python
rg "^(class |def )" --type py

# JavaScript/TypeScript
rg "(class |function |const.*=.*=>)" --type js --type ts

# Go
rg "^func " --type go

# Rust
rg "^(pub )?fn |^(pub )?struct |^(pub )?trait " --type rust
```

### Find All Imports/Dependencies
```bash
# Python
rg "^(import |from .* import)" --type py | sort -u

# JavaScript
rg "^(import |const.*require)" --type js

# Go
rg "^import " --type go
```

### Find Public API Surface
```bash
# Python: Look for __all__ or public functions
rg "^__all__|^def [^_]|^class [^_]" --type py

# TypeScript: Exported items
rg "^export " --type ts

# Go: Capitalized (public) functions
rg "^func [A-Z]" --type go

# Rust: pub items
rg "^pub (fn|struct|enum|trait)" --type rust
```

### Find Configuration Usage
```bash
# Environment variables being accessed
rg "process\.env\.|os\.getenv|ENV\[|System\.getenv"

# Config file loading
rg "config\.|settings\.|loadConfig|readConfig"
```

---

## Tips & Best Practices

### Progressive Disclosure
- Don't try to understand everything at once
- Start with boundaries and contracts
- Zoom in only when needed
- Document as you go

### Pattern Recognition
- Look for familiar frameworks and paradigms
- Identify naming conventions early
- Notice repeated structures
- Compare with similar projects

### Ask Questions
When stuck:
- "What problem does this solve?"
- "How does data flow through here?"
- "What would break if I removed this?"
- "Where is this used?"

### Verify Understanding
- Run the code locally
- Make a small change and see what breaks
- Read and run tests
- Draw diagrams and check them against code

### Time Management
- Set time boxes for exploration
- Focus on the most relevant parts
- Document key findings early
- Don't get lost in rabbit holes

---

## Common Gotchas

- **Hidden configuration** - Check environment variables, config services
- **Generated code** - Look for `// generated`, `build/`, `dist/`
- **Monkey patching** - Dynamic language runtime modifications
- **Implicit dependencies** - Globals, singletons, service locators
- **Legacy code** - Mixed patterns, different styles
- **Dead code** - Unused imports, functions, entire files

---

## Success Criteria

You understand the codebase when you can:

✅ Explain the system architecture to someone else  
✅ Trace a user action from UI to database and back  
✅ Find where to add a new feature  
✅ Identify the impact of proposed changes  
✅ Answer "why does X work this way?"  
✅ Navigate to any component without searching  
✅ Predict what will break when you change Y  

---

## Resources

- **Scripts**: See `scripts/` for automated analysis tools
- **Templates**: See `examples/` for documentation templates
- **IDE Tools**: Use "Find Usages", "Go to Definition", "Call Hierarchy"
- **Visualization**: Consider tools like `tree`, `graphviz`, dependency-cruiser
