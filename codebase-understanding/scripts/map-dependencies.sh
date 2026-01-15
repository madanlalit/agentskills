#!/bin/bash
# Dependency Mapping Script
# Usage: ./map-dependencies.sh /path/to/codebase

set -e

CODEBASE_DIR="${1:-.}"

if [ ! -d "$CODEBASE_DIR" ]; then
    echo "Error: Directory '$CODEBASE_DIR' does not exist"
    exit 1
fi

echo "═══════════════════════════════════════════════════"
echo "  Dependency Mapping Analysis"
echo "═══════════════════════════════════════════════════"
echo "Target: $CODEBASE_DIR"
echo ""

cd "$CODEBASE_DIR"

# ==================== EXTERNAL DEPENDENCIES ====================
echo "📦 EXTERNAL DEPENDENCIES"
echo "---------------------------------------------------"

# Node.js / JavaScript / TypeScript
if [ -f "package.json" ]; then
    echo "Node.js Dependencies (package.json):"
    echo ""
    
    if command -v jq &> /dev/null; then
        echo "Production Dependencies:"
        jq -r '.dependencies // {} | to_entries[] | "  \(.key)@\(.value)"' package.json 2>/dev/null | sort
        
        echo ""
        echo "Development Dependencies:"
        jq -r '.devDependencies // {} | to_entries[] | "  \(.key)@\(.value)"' package.json 2>/dev/null | sort
    else
        echo "  (Install 'jq' for detailed dependency listing)"
        grep -A 999 '"dependencies"' package.json | grep '":' | head -20
    fi
    
    echo ""
    
    # Check for lock files
    if [ -f "package-lock.json" ]; then
        echo "✓ Locked: package-lock.json"
    elif [ -f "yarn.lock" ]; then
        echo "✓ Locked: yarn.lock"
    elif [ -f "pnpm-lock.yaml" ]; then
        echo "✓ Locked: pnpm-lock.yaml"
    else
        echo "⚠️  No lock file found"
    fi
    
    echo ""
fi

# Python
if [ -f "requirements.txt" ]; then
    echo "Python Dependencies (requirements.txt):"
    echo ""
    grep -v '^#' requirements.txt | grep -v '^$' | sort | sed 's/^/  /'
    echo ""
fi

if [ -f "setup.py" ]; then
    echo "Python Setup Dependencies (setup.py):"
    echo ""
    grep -A 20 'install_requires' setup.py | grep -v 'install_requires' | grep -v '\[' | grep -v '\]' | sed 's/^/  /'
    echo ""
fi

if [ -f "pyproject.toml" ]; then
    echo "Python Dependencies (pyproject.toml):"
    echo ""
    grep -A 999 '^\[tool.poetry.dependencies\]' pyproject.toml | grep '=' | grep -v '^\[' | sed 's/^/  /' || true
    echo ""
fi

# Go
if [ -f "go.mod" ]; then
    echo "Go Module Dependencies (go.mod):"
    echo ""
    MODULE=$(grep '^module' go.mod | awk '{print $2}')
    echo "Module: $MODULE"
    echo ""
    echo "Direct Dependencies:"
    grep -v '^//' go.mod | grep -E '^\s+[a-z]' | grep -v 'indirect' | sed 's/^/  /'
    echo ""
    
    INDIRECT_COUNT=$(grep -c 'indirect' go.mod 2>/dev/null || echo 0)
    if [ "$INDIRECT_COUNT" -gt 0 ]; then
        echo "Indirect Dependencies: $INDIRECT_COUNT"
        echo ""
    fi
fi

# Rust
if [ -f "Cargo.toml" ]; then
    echo "Rust Crate Dependencies (Cargo.toml):"
    echo ""
    
    # Extract dependencies section
    sed -n '/^\[dependencies\]/,/^\[/p' Cargo.toml | grep -v '^\[' | grep '=' | sed 's/^/  /'
    
    echo ""
    
    # Dev dependencies if present
    if grep -q '^\[dev-dependencies\]' Cargo.toml; then
        echo "Development Dependencies:"
        sed -n '/^\[dev-dependencies\]/,/^\[/p' Cargo.toml | grep -v '^\[' | grep '=' | sed 's/^/  /'
        echo ""
    fi
    
    if [ -f "Cargo.lock" ]; then
        echo "✓ Locked: Cargo.lock"
        echo ""
    fi
fi

# Java (Maven)
if [ -f "pom.xml" ]; then
    echo "Maven Dependencies (pom.xml):"
    echo ""
    grep -A 2 '<dependency>' pom.xml | grep '<groupId>\|<artifactId>\|<version>' | \
        sed 's/.*<groupId>//;s/<\/groupId>//;s/.*<artifactId>//;s/<\/artifactId>//;s/.*<version>//;s/<\/version>//' | \
        paste - - - | sed 's/^/  /' | head -20
    echo ""
fi

# Java (Gradle)
if [ -f "build.gradle" ] || [ -f "build.gradle.kts" ]; then
    echo "Gradle Dependencies:"
    echo ""
    grep -E '(implementation|api|compile)' build.gradle build.gradle.kts 2>/dev/null | \
        grep -v '^\s*//' | sed 's/^/  /' | head -20
    echo ""
fi

# Ruby
if [ -f "Gemfile" ]; then
    echo "Ruby Gems (Gemfile):"
    echo ""
    grep "^gem " Gemfile | sed 's/^/  /'
    echo ""
    
    if [ -f "Gemfile.lock" ]; then
        echo "✓ Locked: Gemfile.lock"
        echo ""
    fi
fi

# PHP
if [ -f "composer.json" ]; then
    echo "PHP Composer Dependencies:"
    echo ""
    
    if command -v jq &> /dev/null; then
        jq -r '.require // {} | to_entries[] | "  \(.key): \(.value)"' composer.json
    else
        grep -A 999 '"require"' composer.json | grep '":' | head -20
    fi
    
    echo ""
    
    if [ -f "composer.lock" ]; then
        echo "✓ Locked: composer.lock"
        echo ""
    fi
fi

# ==================== INTERNAL DEPENDENCIES ====================
echo ""
echo "🔗 INTERNAL MODULE STRUCTURE"
echo "---------------------------------------------------"

# Python packages
if [ -f "setup.py" ] || [ -f "pyproject.toml" ] || find . -name "__init__.py" -type f 2>/dev/null | head -1 | grep -q .; then
    echo "Python Packages:"
    find . -name "__init__.py" -type f -not -path '*/venv/*' -not -path '*/.venv/*' -not -path '*/node_modules/*' 2>/dev/null | \
        sed 's/__init__.py$//' | sed 's|^\./||' | sort | sed 's/^/  /'
    echo ""
fi

# Go packages
if [ -f "go.mod" ]; then
    echo "Go Packages:"
    find . -name "*.go" -type f -not -path '*/vendor/*' 2>/dev/null | \
        xargs dirname | sort -u | sed 's|^\./||' | sed 's/^/  /'
    echo ""
fi

# Node.js modules (if using workspace/monorepo)
if [ -f "package.json" ]; then
    if grep -q '"workspaces"' package.json; then
        echo "Workspace Packages:"
        if command -v jq &> /dev/null; then
            jq -r '.workspaces[]? // empty' package.json | sed 's/^/  /'
        fi
        echo ""
    fi
fi

# Rust workspace
if [ -f "Cargo.toml" ] && grep -q '^\[workspace\]' Cargo.toml; then
    echo "Rust Workspace Members:"
    sed -n '/^\[workspace\]/,/^\[/p' Cargo.toml | grep 'members' -A 10 | grep '"' | sed 's/.*"\(.*\)".*/  \1/'
    echo ""
fi

# ==================== IMPORT ANALYSIS ====================
echo "📥 IMPORT PATTERNS"
echo "---------------------------------------------------"

if command -v rg &> /dev/null; then
    # Python imports
    if find . -name "*.py" -type f 2>/dev/null | head -1 | grep -q .; then
        echo "Top Python imports (external):"
        rg "^(import|from) " --type py -I 2>/dev/null | \
            sed 's/from //' | sed 's/import //' | awk '{print $1}' | \
            grep -v '^\.' | sort | uniq -c | sort -rn | head -10 | \
            awk '{printf "  %3d  %s\n", $1, $2}'
        echo ""
    fi
    
    # JavaScript/TypeScript imports
    if find . -name "*.js" -o -name "*.ts" -o -name "*.jsx" -o -name "*.tsx" -type f 2>/dev/null | head -1 | grep -q .; then
        echo "Top JavaScript/TypeScript imports:"
        rg "^import.*from ['\"]" --type js --type ts -I 2>/dev/null | \
            sed "s/.*from ['\"]//;s/['\"].*//" | \
            grep -v '^\.' | grep -v '^@/' | sort | uniq -c | sort -rn | head -10 | \
            awk '{printf "  %3d  %s\n", $1, $2}'
        echo ""
    fi
fi

# ==================== DEPENDENCY HEALTH ====================
echo "🏥 DEPENDENCY HEALTH CHECKS"
echo "---------------------------------------------------"

# Check for outdated patterns
echo "Potential Issues:"
echo ""

# Check for version wildcards
if [ -f "package.json" ]; then
    WILDCARDS=$(grep -c '"\*"' package.json 2>/dev/null || echo 0)
    if [ "$WILDCARDS" -gt 0 ]; then
        echo "  ⚠️  Found $WILDCARDS wildcard (*) versions in package.json"
    fi
fi

if [ -f "requirements.txt" ]; then
    UNPINNED=$(grep -v '^#' requirements.txt | grep -v '==' | grep -v '^$' | wc -l | tr -d ' ')
    if [ "$UNPINNED" -gt 0 ]; then
        echo "  ⚠️  Found $UNPINNED unpinned dependencies in requirements.txt"
    fi
fi

# Check for security files
echo ""
echo "Security Considerations:"
if [ -f ".snyk" ] || [ -f "snyk.json" ]; then
    echo "  ✓ Snyk configuration found"
fi

if [ -f ".dependabot/config.yml" ] || [ -d ".github/dependabot.yml" ]; then
    echo "  ✓ Dependabot configuration found"
fi

if [ -f "renovate.json" ]; then
    echo "  ✓ Renovate configuration found"
fi

# ==================== CIRCULAR DEPENDENCY CHECK ====================
echo ""
echo "🔄 CIRCULAR DEPENDENCY DETECTION"
echo "---------------------------------------------------"

if command -v rg &> /dev/null; then
    # Simple circular dependency check for Python
    if find . -name "*.py" -type f 2>/dev/null | head -1 | grep -q .; then
        echo "Checking Python imports..."
        
        # This is a simplified check - would need proper graph analysis for complete detection
        PYTHON_FILES=$(find . -name "*.py" -type f -not -path '*/venv/*' -not -path '*/.venv/*' 2>/dev/null)
        
        if [ -n "$PYTHON_FILES" ]; then
            # Look for relative imports that might indicate circular deps
            RELATIVE_IMPORTS=$(echo "$PYTHON_FILES" | xargs grep -l "^from \." 2>/dev/null | wc -l | tr -d ' ')
            echo "  Files with relative imports: $RELATIVE_IMPORTS"
            echo "  (Manual review recommended for circular dependencies)"
        fi
    fi
    
    # Simple check for JavaScript
    if find . -name "*.js" -o -name "*.ts" -type f 2>/dev/null | head -1 | grep -q .; then
        echo ""
        echo "Checking JavaScript/TypeScript imports..."
        echo "  (Use tools like madge or dependency-cruiser for detailed analysis)"
    fi
else
    echo "  (Install ripgrep 'rg' for import analysis)"
fi

echo ""
echo "═══════════════════════════════════════════════════"
echo "Dependency analysis complete!"
echo "═══════════════════════════════════════════════════"
echo ""
echo "💡 Tips:"
echo "  - Review unpinned/wildcard versions for reproducibility"
echo "  - Check for unused dependencies"
echo "  - Consider using dependency scanning tools:"
echo "    • npm audit / yarn audit (Node.js)"
echo "    • pip-audit / safety (Python)"
echo "    • cargo audit (Rust)"
echo "    • snyk / dependabot (Multi-language)"
