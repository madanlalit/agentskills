# Codebase Understanding Skill

A comprehensive agent skill for systematically analyzing and understanding any codebase.

## Overview

This skill helps AI agents (and developers) quickly understand unfamiliar codebases through:
- Progressive discovery workflow
- Language-specific analysis patterns
- Automated scanning tools
- Structured documentation templates

## When to Use

Use this skill when you need to:
- 🎓 **Onboard** to a new codebase
- 🔍 **Investigate** bugs or features
- 📊 **Document** system architecture
- 🔄 **Plan** refactoring efforts
- 🔒 **Audit** security posture
- 📈 **Assess** technical debt

## Quick Start

1. **Read the skill documentation:**
   ```bash
   cat SKILL.md
   ```

2. **Run automated analysis:**
   ```bash
   # Analyze structure
   ./scripts/analyze-structure.sh /path/to/codebase
   
   # Map dependencies
   ./scripts/map-dependencies.sh /path/to/codebase
   ```

3. **Use documentation templates:**
   - `examples/architecture-template.md` - System architecture docs
   - `examples/component-map-template.md` - Component relationships

## Skill Structure

```
codebase-understanding/
├── SKILL.md                          # Main skill documentation
├── README.md                         # This file
├── scripts/
│   ├── analyze-structure.sh          # Automated structure analysis
│   └── map-dependencies.sh           # Dependency mapping
└── examples/
    ├── architecture-template.md      # Architecture documentation template
    └── component-map-template.md     # Component relationship template
```

## Key Features

### 📋 Comprehensive Workflow
5-phase progressive discovery process:
1. Initial Reconnaissance (5-10 min)
2. Architecture Mapping (10-20 min)
3. Deep Dive (20-40 min per component)
4. Documentation (ongoing)
5. Verification

### 🔍 Language Support
Specific guidance for:
- Python (Django, Flask, FastAPI)
- JavaScript/TypeScript (React, Node.js, Next.js)
- Go
- Rust
- Java (Spring Boot)
- C/C++
- And more...

### 🤖 Automated Tools
Helper scripts for:
- File statistics and structure visualization
- Project type and framework detection
- Entry point identification
- Dependency analysis (external and internal)
- Configuration discovery
- Test coverage overview

### 📝 Documentation Templates
Ready-to-use templates for:
- System architecture documentation
- Component relationship mapping
- Data flow diagrams
- Technology stack documentation

### 🎯 Context-Specific Guidance
Different strategies for:
- Onboarding (comprehensive understanding)
- Bug Investigation (targeted analysis)
- Feature Addition (impact analysis)
- Refactoring (structural understanding)
- Security Audit (attack surface mapping)

## Analysis Scripts

### Structure Analysis
```bash
./scripts/analyze-structure.sh /path/to/codebase
```

**Output includes:**
- File count by language
- Project type detection
- Framework identification
- Entry points
- Directory structure
- Configuration files
- Dependency overview
- Test coverage
- Build & CI/CD setup
- Documentation files

### Dependency Mapping
```bash
./scripts/map-dependencies.sh /path/to/codebase
```

**Output includes:**
- External dependencies with versions
- Package lock status
- Internal module structure
- Import patterns
- Dependency health checks
- Security considerations
- Circular dependency detection

## Example Usage

### For an AI Agent
```markdown
I need to understand this codebase. Use the codebase-understanding skill to:
1. Run the analysis scripts
2. Identify the main components
3. Document the architecture using the provided template
```

### For a Developer
1. Clone this repository
2. Run the analysis scripts on your target codebase
3. Read the SKILL.md for systematic exploration guidance
4. Use the templates to document your findings

## Tips for Best Results

1. **Start Broad, Then Deep**
   - Don't dive into details immediately
   - Build a mental map of the whole system first
   - Zoom in on specific areas as needed

2. **Use the Tools**
   - Run automated scripts first
   - They provide quick insights and save time
   - Manual exploration can then be targeted

3. **Document as You Go**
   - Use the provided templates
   - Fill them out incrementally
   - Share with team members

4. **Verify Your Understanding**
   - Run the code locally
   - Make small changes to test assumptions
   - Read and run tests

## Requirements

### Required
- `bash` shell
- Basic Unix tools (`find`, `grep`, `sed`, etc.)

### Optional (for enhanced features)
- `ripgrep` (`rg`) - Better code search
- `tree` - Better directory visualization
- `jq` - JSON parsing for package files

## Contributing

To improve this skill:
1. Add more language-specific patterns to SKILL.md
2. Enhance the analysis scripts
3. Create additional templates
4. Share common gotchas and tips

## License

See LICENSE file in the repository root.

## Related Skills

- **code-review** - Review code for bugs and best practices
- **effective-python-refactor** - Refactor Python code

---

**Happy Code Exploring! 🚀**
