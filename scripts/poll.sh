#!/bin/bash
# Poll for a sentinel file and return its contents when ready
# Usage: ./scripts/poll.sh <task-id> [timeout_seconds]
#
# Exits 0 and prints sentinel JSON when done
# Exits 1 on timeout

set -euo pipefail

TASK_ID="${1:?Usage: poll.sh <task-id> [timeout_seconds]}"
TIMEOUT="${2:-600}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SENTINEL="$PROJECT_DIR/sessions/$TASK_ID.done"

elapsed=0
while [ ! -f "$SENTINEL" ]; do
  if [ "$elapsed" -ge "$TIMEOUT" ]; then
    echo "Timeout after ${TIMEOUT}s waiting for $TASK_ID" >&2
    exit 1
  fi
  sleep 3
  elapsed=$((elapsed + 3))
done

cat "$SENTINEL"

# Close the child pane after a short delay
PANE_FILE="$PROJECT_DIR/sessions/$TASK_ID.pane"
if [ -f "$PANE_FILE" ]; then
  PANE_ID=$(cat "$PANE_FILE")
  sleep 5
  tmux kill-pane -t "$PANE_ID" 2>/dev/null || true
  rm -f "$PANE_FILE"
fi
