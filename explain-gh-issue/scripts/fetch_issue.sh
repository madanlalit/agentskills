#!/bin/bash
set -euo pipefail

# Fetch and format a GitHub issue for explain-gh-issue skill
# Usage: scripts/fetch_issue.sh <owner/repo> <issue-number> [--comments-tail N] [--include-linked-prs]

show_help() {
    cat <<'EOF'
Usage: scripts/fetch_issue.sh <owner/repo> <issue-number> [options]

Fetches a GitHub issue with all comments and formats it for agent consumption.
Outputs in plain text for maximum token efficiency.

Arguments:
  owner/repo          Repository identifier (e.g., "microsoft/vscode").
  issue-number        Issue number to fetch.

Options:
  --comments-tail N   Fetch only the last N comments.
  --include-linked-prs Fetch metadata for linked pull requests.
  --help              Show this help message.

Exit codes:
  0   Success.
  1   Missing arguments or invalid format.
  2   Issue not found or no access.
  3   gh CLI error.
EOF
}

REPO=""
ISSUE_NUM=""
COMMENTS_TAIL=0
INCLUDE_PRS=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --comments-tail)
            COMMENTS_TAIL="$2"
            shift 2
            ;;
        --include-linked-prs)
            INCLUDE_PRS=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            if [[ -z "$REPO" ]]; then
                REPO="$1"
            elif [[ -z "$ISSUE_NUM" ]]; then
                ISSUE_NUM="$1"
            else
                echo "Error: Unknown argument '$1'" >&2
                show_help
                exit 1
            fi
            shift
            ;;
    esac
done

if [[ -z "$REPO" || -z "$ISSUE_NUM" ]]; then
    echo "Error: Missing required arguments 'owner/repo' and 'issue-number'." >&2
    show_help
    exit 1
fi

if ! echo "$REPO" | grep -q '/'; then
    echo "Error: Repository must be in 'owner/repo' format. Got: $REPO" >&2
    exit 1
fi

# Fetch issue metadata
FIELDS="number,title,body,state,labels,author,createdAt,updatedAt,closedAt,comments,milestone,assignees"
if [[ "$INCLUDE_PRS" == true ]]; then
    FIELDS="$FIELDS,closedByPullRequestsReferences"
fi

ISSUE_JSON=$(GH_PROMPT_DISABLED=1 gh issue view "$ISSUE_NUM" --repo "$REPO" --json "$FIELDS" 2>/dev/null) || {
    echo "Error: Failed to fetch issue #$ISSUE_NUM from $REPO. Check permissions or if the issue exists." >&2
    exit 2
}

# Parse fields using jq
NUMBER=$(echo "$ISSUE_JSON" | jq -r '.number')
TITLE=$(echo "$ISSUE_JSON" | jq -r '.title')
BODY=$(echo "$ISSUE_JSON" | jq -r '.body // ""')
STATE=$(echo "$ISSUE_JSON" | jq -r '.state')
AUTHOR=$(echo "$ISSUE_JSON" | jq -r '.author.login // "unknown"')
CREATED=$(echo "$ISSUE_JSON" | jq -r '.createdAt')
UPDATED=$(echo "$ISSUE_JSON" | jq -r '.updatedAt')
LABELS=$(echo "$ISSUE_JSON" | jq -r '[.labels[].name] | join(", ") // "none"')
MILESTONE=$(echo "$ISSUE_JSON" | jq -r '.milestone.title // "none"')
ASSIGNEES=$(echo "$ISSUE_JSON" | jq -r '[.assignees[].login] | join(", ") // "none"')

# Tail comments if requested
if [[ "$COMMENTS_TAIL" -gt 0 ]]; then
    ISSUE_JSON=$(echo "$ISSUE_JSON" | jq --arg n "$COMMENTS_TAIL" '.comments = .comments[-($n|tonumber):]')
fi

# Count comments
COMMENT_COUNT=$(echo "$ISSUE_JSON" | jq -r '.comments | length')

# Output flat text
cat <<EOF
--- ISSUE #$NUMBER ---
TITLE: $TITLE
STATE: $STATE
AUTHOR: $AUTHOR
CREATED: $CREATED
UPDATED: $UPDATED
LABELS: $LABELS
MILESTONE: $MILESTONE
ASSIGNEES: $ASSIGNEES
COMMENTS_TOTAL: $COMMENT_COUNT
EOF

if [[ "$INCLUDE_PRS" == true ]]; then
    echo "LINKED_PRS:"
    echo "$ISSUE_JSON" | jq -c '.closedByPullRequestsReferences[]?' | while read -r pr; do
        if [[ -n "$pr" ]]; then
            P_NUM=$(echo "$pr" | jq -r '.number')
            P_TITLE=$(echo "$pr" | jq -r '.title')
            P_STATE=$(echo "$pr" | jq -r '.state')
            echo "  #$P_NUM ($P_STATE): $P_TITLE"
        fi
    done
fi

cat <<EOF

--- BODY ---
$BODY

--- COMMENTS ---
EOF

if [[ "$COMMENT_COUNT" -gt 0 ]]; then
    echo "$ISSUE_JSON" | jq -c '.comments[]' | while read -r comment; do
        C_AUTHOR=$(echo "$comment" | jq -r '.author.login // "unknown"')
        C_CREATED=$(echo "$comment" | jq -r '.createdAt')
        C_BODY=$(echo "$comment" | jq -r '.body // ""')
        cat <<EOF
[$C_AUTHOR @ $C_CREATED]
$C_BODY

EOF
    done
else
    echo "No comments."
fi
echo "--- END ---"

exit 0
