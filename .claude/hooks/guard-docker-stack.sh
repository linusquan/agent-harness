#!/bin/bash
# PreToolUse hook: block docker-stack.yml edits on main-v2
# The deployment model uses deploy-test/deploy-prod branches for stack changes.
# main-v2's docker-stack.yml is a reference copy only — never used for deployment.

set -e

# Read tool input from stdin
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only care about docker-stack.yml
if [[ "$FILE_PATH" != *"docker-stack.yml"* ]] && [[ "$FILE_PATH" != *"docker-stack.yaml"* ]]; then
  exit 0
fi

# Only guard the primary worktree (project src/). Other worktrees — e.g. a
# temporary /tmp/... checkout of deploy-test/deploy-prod — are by definition
# already on a deploy branch and should be allowed through.
PROJECT_SRC="${CLAUDE_PROJECT_DIR:-/Users/liquan/code/SCGC}/src"
case "$FILE_PATH" in
  "$PROJECT_SRC"/*) ;;   # inside primary worktree — continue checking
  *) exit 0 ;;            # other worktree — allow
esac

# Check current branch
CURRENT_BRANCH=$(cd "$PROJECT_SRC" && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

if [[ "$CURRENT_BRANCH" == "main-v2" ]] || [[ "$CURRENT_BRANCH" == "main" ]]; then
  cat <<EOF
BLOCKED: docker-stack.yml should NOT be edited on the $CURRENT_BRANCH branch.

Deployment model (see .artifacts/infra/vps-deployment-strategy.md):
  - main-v2/docker-stack.yml is a reference copy, NOT used for deployment
  - deploy-test branch: stack file for srv3 (test server)
  - deploy-prod branch: stack file for srv2 (production)

To make stack changes:
  1. git checkout deploy-test
  2. Edit docker-stack.yml there (uses absolute paths)
  3. Commit and push
  4. Repeat for deploy-prod if needed
  5. Return to main-v2: git checkout main-v2
EOF
  exit 2
fi

exit 0
