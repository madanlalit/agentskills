#!/bin/bash
# Codebase Structure Analysis Script
# Usage: ./analyze-structure.sh /path/to/codebase

set -e

CODEBASE_DIR="${1:-.}"

if [ ! -d "$CODEBASE_DIR" ]; then
    echo "Error: Directory '$CODEBASE_DIR' does not exist"
    exit 1
fi

echo "═══════════════════════════════════════════════════"
echo "  Codebase Structure Analysis"
echo "═══════════════════════════════════════════════════"
echo "Target: $CODEBASE_DIR"
echo ""

# Change to target directory
cd "$CODEBASE_DIR"

# ==================== FILE STATISTICS ====================
echo "📊 FILE STATISTICS"
echo "---------------------------------------------------"

# Count files by extension
echo "Files by type:"
find . -type f -not -path '*/\.*' -not -path '*/node_modules/*' -not -path '*/venv/*' -not -path '*/vendor/*' -not -path '*/build/*' -not -path '*/dist/*' | \
    sed 's/.*\.//' | sort | uniq -c | sort -rn | head -20 | \
    awk '{printf "  %-15s %6s files\n", $2, $1}'

echo ""

# Total counts
TOTAL_FILES=$(find . -type f -not -path '*/\.*' -not -path '*/node_modules/*' -not -path '*/venv/*' -not -path '*/vendor/*' | wc -l | tr -d ' ')
TOTAL_DIRS=$(find . -type d -not -path '*/\.*' -not -path '*/node_modules/*' -not -path '*/venv/*' -not -path '*/vendor/*' | wc -l | tr -d ' ')

echo "Total: $TOTAL_FILES files in $TOTAL_DIRS directories"
echo ""

# ==================== PROJECT TYPE ====================
echo "🏗️  PROJECT TYPE DETECTION"
echo "---------------------------------------------------"

# Language detection
if [ -f "package.json" ]; then
    echo "✓ JavaScript/TypeScript (Node.js)"
    if grep -q '"type": "module"' package.json 2>/dev/null; then
        echo "  - ES Modules"
    else
        echo "  - CommonJS"
    fi
fi

if [ -f "requirements.txt" ] || [ -f "setup.py" ] || [ -f "pyproject.toml" ]; then
    echo "✓ Python"
fi

if [ -f "go.mod" ]; then
    echo "✓ Go"
    MODULE_NAME=$(grep '^module' go.mod | awk '{print $2}')
    echo "  - Module: $MODULE_NAME"
fi

if [ -f "Cargo.toml" ]; then
    echo "✓ Rust"
    CRATE_NAME=$(grep '^\[package\]' -A 1 Cargo.toml | grep '^name' | cut -d'"' -f2)
    echo "  - Crate: $CRATE_NAME"
fi

if [ -f "pom.xml" ] || [ -f "build.gradle" ]; then
    echo "✓ Java"
fi

if [ -f "composer.json" ]; then
    echo "✓ PHP"
fi

if [ -f "Gemfile" ]; then
    echo "✓ Ruby"
fi

echo ""

# Framework detection
echo "Frameworks/Libraries detected:"
if [ -f "package.json" ]; then
    if grep -q '"react"' package.json; then echo "  - React"; fi
    if grep -q '"vue"' package.json; then echo "  - Vue"; fi
    if grep -q '"angular"' package.json; then echo "  - Angular"; fi
    if grep -q '"next"' package.json; then echo "  - Next.js"; fi
    if grep -q '"express"' package.json; then echo "  - Express"; fi
    if grep -q '"nestjs"' package.json; then echo "  - NestJS"; fi
fi

if command -v rg &> /dev/null; then
    rg -l "from django" 2>/dev/null | head -1 | grep -q . && echo "  - Django"
    rg -l "from flask" 2>/dev/null | head -1 | grep -q . && echo "  - Flask"
    rg -l "from fastapi" 2>/dev/null | head -1 | grep -q . && echo "  - FastAPI"
    rg -l "@SpringBootApplication" 2>/dev/null | head -1 | grep -q . && echo "  - Spring Boot"
fi

echo ""

# ==================== ENTRY POINTS ====================
echo "🚪 ENTRY POINTS"
echo "---------------------------------------------------"

# Common entry point files
ENTRY_POINTS=$(find . -maxdepth 3 \( -name "main.*" -o -name "index.*" -o -name "app.*" -o -name "__main__.py" \) -type f -not -path '*/node_modules/*' -not -path '*/venv/*' 2>/dev/null)

if [ -n "$ENTRY_POINTS" ]; then
    echo "$ENTRY_POINTS" | while read -r file; do
        echo "  $file"
    done
else
    echo "  (None found with common names)"
fi

echo ""

# ==================== DIRECTORY STRUCTURE ====================
echo "📁 DIRECTORY STRUCTURE"
echo "---------------------------------------------------"

if command -v tree &> /dev/null; then
    tree -L 2 -d -I 'node_modules|venv|vendor|build|dist|__pycache__|.git' | head -40
else
    find . -maxdepth 2 -type d -not -path '*/\.*' -not -path '*/node_modules/*' -not -path '*/venv/*' -not -path '*/vendor/*' -not -path '*/build/*' -not -path '*/dist/*' | sort
fi

echo ""

# ==================== CONFIGURATION FILES ====================
echo "⚙️  CONFIGURATION FILES"
echo "---------------------------------------------------"

CONFIG_FILES=$(find . -maxdepth 3 \( \
    -name "*.config.*" -o \
    -name "*rc" -o \
    -name "*.yml" -o \
    -name "*.yaml" -o \
    -name "*.toml" -o \
    -name ".env*" -o \
    -name "Dockerfile*" -o \
    -name "docker-compose.*" \
    \) -type f -not -path '*/node_modules/*' -not -path '*/venv/*' 2>/dev/null | sort)

if [ -n "$CONFIG_FILES" ]; then
    echo "$CONFIG_FILES" | while read -r file; do
        echo "  $file"
    done
else
    echo "  (None found)"
fi

echo ""

# ==================== DEPENDENCIES ====================
echo "📦 DEPENDENCIES"
echo "---------------------------------------------------"

if [ -f "package.json" ]; then
    echo "Node.js dependencies:"
    DEP_COUNT=$(cat package.json | grep -A 999 '"dependencies"' | grep -c '":' 2>/dev/null || echo 0)
    DEV_DEP_COUNT=$(cat package.json | grep -A 999 '"devDependencies"' | grep -c '":' 2>/dev/null || echo 0)
    echo "  - Production: $DEP_COUNT"
    echo "  - Development: $DEV_DEP_COUNT"
fi

if [ -f "requirements.txt" ]; then
    echo "Python dependencies:"
    DEP_COUNT=$(grep -v '^#' requirements.txt | grep -v '^$' | wc -l | tr -d ' ')
    echo "  - $DEP_COUNT packages"
fi

if [ -f "go.mod" ]; then
    echo "Go dependencies:"
    DEP_COUNT=$(grep -c '^\s*[a-z]' go.mod 2>/dev/null || echo 0)
    echo "  - $DEP_COUNT modules"
fi

if [ -f "Cargo.toml" ]; then
    echo "Rust dependencies:"
    DEP_COUNT=$(grep -A 999 '^\[dependencies\]' Cargo.toml | grep -c '=' 2>/dev/null || echo 0)
    echo "  - $DEP_COUNT crates"
fi

echo ""

# ==================== TESTS ====================
echo "🧪 TESTS"
echo "---------------------------------------------------"

TEST_FILES=$(find . -type f \( \
    -name "*test*" -o \
    -name "*spec*" \
    \) -not -path '*/node_modules/*' -not -path '*/venv/*' -not -path '*/vendor/*' 2>/dev/null | wc -l | tr -d ' ')

echo "Test files found: $TEST_FILES"

# Test frameworks
if [ -f "pytest.ini" ] || grep -q "pytest" requirements.txt 2>/dev/null; then
    echo "  - pytest (Python)"
fi

if grep -q '"jest"' package.json 2>/dev/null; then
    echo "  - Jest (JavaScript)"
fi

if grep -q '"mocha"' package.json 2>/dev/null; then
    echo "  - Mocha (JavaScript)"
fi

if command -v rg &> /dev/null; then
    rg -l "testing\.T|testify" 2>/dev/null | head -1 | grep -q . && echo "  - Go testing"
    rg -l "#\[cfg\(test\)\]" 2>/dev/null | head -1 | grep -q . && echo "  - Rust tests"
fi

echo ""

# ==================== BUILD & CI/CD ====================
echo "🔧 BUILD & CI/CD"
echo "---------------------------------------------------"

if [ -f "Makefile" ]; then echo "✓ Makefile"; fi
if [ -f "Dockerfile" ]; then echo "✓ Dockerfile"; fi
if [ -f "docker-compose.yml" ] || [ -f "docker-compose.yaml" ]; then echo "✓ Docker Compose"; fi
if [ -d ".github/workflows" ]; then 
    echo "✓ GitHub Actions"
    WORKFLOW_COUNT=$(find .github/workflows -name "*.yml" -o -name "*.yaml" | wc -l | tr -d ' ')
    echo "  - $WORKFLOW_COUNT workflows"
fi
if [ -f ".gitlab-ci.yml" ]; then echo "✓ GitLab CI"; fi
if [ -f ".travis.yml" ]; then echo "✓ Travis CI"; fi
if [ -f "Jenkinsfile" ]; then echo "✓ Jenkins"; fi

echo ""

# ==================== DOCUMENTATION ====================
echo "📚 DOCUMENTATION"
echo "---------------------------------------------------"

DOC_FILES=$(find . -maxdepth 2 -type f \( \
    -name "README*" -o \
    -name "CONTRIBUTING*" -o \
    -name "CHANGELOG*" -o \
    -name "LICENSE*" \
    \) 2>/dev/null)

if [ -n "$DOC_FILES" ]; then
    echo "$DOC_FILES" | while read -r file; do
        echo "  $file"
    done
fi

if [ -d "docs" ]; then
    DOC_COUNT=$(find docs -type f -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
    echo "  docs/ directory ($DOC_COUNT markdown files)"
fi

echo ""
echo "═══════════════════════════════════════════════════"
echo "Analysis complete!"
echo "═══════════════════════════════════════════════════"
