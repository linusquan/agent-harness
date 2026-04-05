#!/bin/bash
# Hook: signals child session completion to the orchestrator
# Only fires for child sessions (HARNESS_TASK_ID must be set)

LOG="/tmp/harness-hook.log"

if [ -z "$HARNESS_TASK_ID" ]; then
  echo "[$(date -u +%FT%TZ)] Stop hook fired but HARNESS_TASK_ID not set, skipping" >> "$LOG"
  exit 0
fi

echo "[$(date -u +%FT%TZ)] Stop hook fired for task=$HARNESS_TASK_ID role=$HARNESS_ROLE" >> "$LOG"

INPUT=$(cat)
# Always write to the project root sessions dir, not the current working dir
# (child sessions may cd into subdirectories like src/newsite/)
SESSION_DIR="$(cd "$(dirname "$0")/../.." && pwd)/sessions"

mkdir -p "$SESSION_DIR"

echo "$INPUT" | jq -c '{
  task_id: env.HARNESS_TASK_ID,
  role: env.HARNESS_ROLE,
  session_id: .session_id,
  timestamp: (now | strftime("%Y-%m-%dT%H:%M:%SZ")),
  status: "done",
  last_message: .last_assistant_message
}' > "$SESSION_DIR/$HARNESS_TASK_ID.done"

echo "[$(date -u +%FT%TZ)] Wrote sentinel: $SESSION_DIR/$HARNESS_TASK_ID.done" >> "$LOG"
