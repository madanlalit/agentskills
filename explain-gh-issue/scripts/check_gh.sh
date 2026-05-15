#!/bin/bash
set -euo pipefail

# explain-gh-issue prerequisite check
# Usage: scripts/check_gh.sh

show_help() {
    cat <<'EOF'
Usage: scripts/check_gh.sh

Checks that the gh CLI is installed, authenticated, and able to access GitHub.
Outputs results in plain text for maximum token efficiency.
No sensitive data (tokens, credentials) is ever printed.

Exit codes:
  0   All checks passed.
  1   gh CLI not installed.
  2   gh CLI not authenticated.
  3   Cannot communicate with GitHub API.
EOF
}

if [[ $# -gt 0 && "$1" == "--help" ]]; then
    show_help
    exit 0
fi

# --- Check 1: gh CLI installed ---
if ! command -v gh &> /dev/null; then
    echo "Error: gh CLI is not installed." >&2
    echo "Install from: https://cli.github.com/" >&2
    exit 1
fi

GH_VERSION=$(gh --version | head -n 1 | awk '{print $3}')

# --- Check 2: gh CLI authenticated ---
RAW_AUTH=$(GH_PROMPT_DISABLED=1 gh auth status 2>&1) || RAW_AUTH=""

if [[ -z "$RAW_AUTH" ]] || echo "$RAW_AUTH" | grep -q "not logged"; then
    echo "Error: gh CLI ($GH_VERSION) is installed but not authenticated." >&2
    echo "Run: gh auth login" >&2
    exit 2
fi

# Extract hostname, user, and scopes
AUTH_HOST=$(echo "$RAW_AUTH" | grep -oE 'Logged in to [^[:space:]]+' | awk '{print $4}' | head -n 1)
AUTH_USER=$(echo "$RAW_AUTH" | grep -oE 'account [^[:space:]]+' | awk '{print $2}' | head -n 1)
AUTH_SCOPES=$(echo "$RAW_AUTH" | grep -oE 'Token scopes: .*' | sed 's/Token scopes: //' | head -n 1)

# --- Check 3: Can reach GitHub API ---
API_PING=$(GH_PROMPT_DISABLED=1 gh api /user &> /dev/null && echo "ok" || echo "fail")
if [[ "$API_PING" != "ok" ]]; then
    echo "Error: Authenticated as $AUTH_USER on $AUTH_HOST with scopes [$AUTH_SCOPES], but cannot reach GitHub API." >&2
    exit 3
fi

# --- Success ---
cat <<EOF
GH_CLI: $GH_VERSION
HOST: $AUTH_HOST
USER: $AUTH_USER
SCOPES: $AUTH_SCOPES
API: reachable
STATUS: OK
EOF

exit 0
