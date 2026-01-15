#!/bin/bash

# Code Review Discovery Scan
# Automates the regex patterns defined in SKILL.md using ripgrep (rg).

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Starting Code Review Discovery Scan...${NC}\n"

# Check for ripgrep
if ! command -v rg &> /dev/null; then
    echo -e "${RED}Error: ripgrep (rg) is not installed.${NC}"
    echo "This script requires 'rg' for fast searching."
    echo "Install it via: brew install ripgrep (macOS) or apt-get install ripgrep (Linux)"
    exit 1
fi

# Function to run a search and print results nicely
run_check() {
    local title="$1"
    local pattern="$2"
    shift 2 # Remaining args are passed to rg

    echo -e "${YELLOW}👉 Checking: $title${NC}"
    # Run rg, capture output.
    # -n: line number
    # --heading: group matches by file
    # --color=always: keep colors for display
    output=$(rg -n --heading --color=always "$pattern" "$@" 2>/dev/null)

    if [ -z "$output" ]; then
        echo -e "${GREEN}   No issues found.${NC}"
    else
        echo "$output"
    fi
    echo "" # Newline
}

# --- Priority 1: Security ---

run_check "Potential Hardcoded Secrets" \
    "(password|secret|api[_-]?key|token|credential)\s*=\s*['\"][^'\"]{8,}['"]" \
    --type-add 'code:*.{py,js,ts,go,rb,java,c,cpp,rs,php,json,yaml,yml,xml,properties,toml}' -t code

run_check "Dangerous Functions (eval, exec, shell)" \
    "\b(eval|exec|os\.system|shell=True|dangerouslySetInnerHTML)\b"

run_check "SQL Injection Patterns (Concatenation)" \
    "(SELECT|INSERT|UPDATE|DELETE).*\".*\"|f\".*SELECT|\`\\\${.*}.*SELECT"

# --- Priority 3: Maintainability ---

run_check "TODOs and FIXMEs" \
    "(TODO|FIXME|HACK|XXX|BUG):"

# --- Language Specific ---

run_check "Broad Exception Catching (Py/JS/Java)" \
    "except\s*(Exception|BaseException)?\s*:|catch\s*\(\s*(e|err|error)?\s*\)|catch\s*\(\s*Exception\s+"

run_check "C/C++ Legacy Memory/String Ops" \
    "(strcpy|strcat|sprintf|gets)|(malloc|free|new|delete)" \
    --type cpp

# --- Test Coverage Heuristic ---

echo -e "${YELLOW}👉 Checking: Missing Tests (Heuristic for Python/JS)${NC}"
# Simple check: if src/foo.py exists, look for tests/test_foo.py or similar
found_missing=0
# Python check
if [ -d "src" ] || [ -d "app" ] || [ -d "lib" ]; then
    # Find python files, ignore __init__.py
    find . -type f -name "*.py" -not -name "__init__.py" -not -path "*/tests/*" -not -path "*/venv/*" | while read -r file; do
        filename=$(basename "$file")
        # Check for test_filename.py in the project
        if ! find . -name "test_$filename" -o -name "${filename%.*}_test.py" | grep -q .; then
             echo "   ❓ Possible missing test for: $file"
             found_missing=1
        fi
    done
fi
if [ "$found_missing" -eq 0 ]; then
     echo -e "${GREEN}   No obvious missing tests found (or src structure not detected).${NC}"
fi
echo ""

echo -e "${BLUE}✅ Scan complete.${NC}"
