#!/bin/bash
# Hook: signals child session completion to the orchestrator
# Only fires for child sessions (HARNESS_TASK_ID must be set)

[ -z "$HARNESS_TASK_ID" ] && exit 0

INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd // "."')
SESSION_DIR="$CWD/sessions"

mkdir -p "$SESSION_DIR"

echo "$INPUT" | jq -c '{
  task_id: env.HARNESS_TASK_ID,
  role: env.HARNESS_ROLE,
  session_id: .session_id,
  timestamp: (now | strftime("%Y-%m-%dT%H:%M:%SZ")),
  status: "done",
  last_message: .last_assistant_message
}' > "$SESSION_DIR/$HARNESS_TASK_ID.done"
