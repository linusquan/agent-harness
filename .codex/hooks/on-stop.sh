#!/bin/bash
# Codex Stop hook: signal harness task completion to the orchestrator.

set -euo pipefail

if [[ -z "${HARNESS_TASK_ID:-}" ]]; then
  jq -n '{ continue: true }'
  exit 0
fi

INPUT=$(cat)
PROJECT_DIR="$(git rev-parse --show-toplevel)"
SESSION_DIR="$PROJECT_DIR/sessions"

mkdir -p "$SESSION_DIR"

echo "$INPUT" | jq -c '{
  task_id: env.HARNESS_TASK_ID,
  role: env.HARNESS_ROLE,
  session_id: .session_id,
  turn_id: .turn_id,
  timestamp: (now | strftime("%Y-%m-%dT%H:%M:%SZ")),
  status: "done",
  last_message: .last_assistant_message
}' > "$SESSION_DIR/$HARNESS_TASK_ID.done"

SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')
if [[ -n "$SESSION_ID" ]]; then
  echo "$SESSION_ID" > "$SESSION_DIR/$HARNESS_TASK_ID.codex-session"
fi

jq -n '{ continue: true }'
