#!/bin/bash
# Dispatch a child Claude Code session with a role-specific prompt
# Usage: ./scripts/dispatch.sh <role> <complexity> <prompt> [--task-id <id>]
#
# Complexity levels:
#   simple  → haiku
#   mid     → sonnet
#   complex → opus
#
# Options:
#   --task-id <id>   Reuse an existing task ID instead of generating a new one
#
# Examples:
#   ./scripts/dispatch.sh planner complex "analyze the auth module"
#   ./scripts/dispatch.sh builder mid "implement the plan" --task-id builder-destiny

set -euo pipefail

ROLE="${1:?Usage: dispatch.sh <role> <complexity> <prompt> [--task-id <id>]}"
COMPLEXITY="${2:?Usage: dispatch.sh <role> <complexity> <prompt> [--task-id <id>]}"
PROMPT="${3:?Usage: dispatch.sh <role> <complexity> <prompt> [--task-id <id>]}"

# Map complexity to model
case "$COMPLEXITY" in
  simple)  MODEL="haiku" ;;
  mid)     MODEL="sonnet" ;;
  complex) MODEL="opus" ;;
  *) echo "Error: complexity must be simple, mid, or complex" >&2; exit 1 ;;
esac
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Use provided task ID or generate a new one
TASK_ID=""
if [[ "${4:-}" == "--task-id" && -n "${5:-}" ]]; then
  TASK_ID="$5"
  # Clean up old sentinel so poll.sh can wait for the new one
  rm -f "$PROJECT_DIR/sessions/$TASK_ID.done"
  rm -f "$PROJECT_DIR/sessions/$TASK_ID.pane"
else
  TASK_ID=$(node "$PROJECT_DIR/scripts/agent-name.mjs" "$ROLE")
fi

# Validate role
if [ ! -f "$PROJECT_DIR/roles/$ROLE.md" ]; then
  echo "Error: no prompt file found at roles/$ROLE.md" >&2
  exit 1
fi

# Spawn child session in a horizontal split pane, capture pane ID
PANE_ID=$(tmux split-window -h -P -F "#{pane_id}" -c "$PROJECT_DIR" \
  -e "HARNESS_TASK_ID=$TASK_ID" \
  -e "HARNESS_ROLE=$ROLE" \
  "claude \"$PROMPT\" --model $MODEL --name $TASK_ID --permission-mode bypassPermissions --append-system-prompt-file ./roles/$ROLE.md")

# Save pane ID so poll.sh can close it
mkdir -p "$PROJECT_DIR/sessions"
echo "$PANE_ID" > "$PROJECT_DIR/sessions/$TASK_ID.pane"

echo "Dispatched: role=$ROLE task=$TASK_ID pane=$PANE_ID"
echo "Poll with: ./scripts/poll.sh $TASK_ID"
