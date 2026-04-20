#!/bin/bash
# Run an interactive Codex task in a tmux pane. Normal completion is emitted by the Codex Stop hook.
# Usage: ./scripts/run-codex-task.sh <task-id> <role> <model> <role-file> <prompt> [--resume-session <id>]

set -euo pipefail

TASK_ID="${1:?Usage: run-codex-task.sh <task-id> <role> <model> <role-file> <prompt> [--resume-session <id>]}"
ROLE="${2:?Usage: run-codex-task.sh <task-id> <role> <model> <role-file> <prompt> [--resume-session <id>]}"
MODEL="${3:?Usage: run-codex-task.sh <task-id> <role> <model> <role-file> <prompt> [--resume-session <id>]}"
ROLE_FILE="${4:?Usage: run-codex-task.sh <task-id> <role> <model> <role-file> <prompt> [--resume-session <id>]}"
PROMPT="${5:?Usage: run-codex-task.sh <task-id> <role> <model> <role-file> <prompt> [--resume-session <id>]}"

RESUME_SESSION_ID=""
if [[ "${6:-}" == "--resume-session" && -n "${7:-}" ]]; then
  RESUME_SESSION_ID="$7"
fi

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SESSION_DIR="$PROJECT_DIR/sessions"
SENTINEL_FILE="$SESSION_DIR/$TASK_ID.done"
SESSION_ID_FILE="$SESSION_DIR/$TASK_ID.codex-session"
HISTORY_FILE="${CODEX_HOME:-$HOME/.codex}/history.jsonl"

mkdir -p "$SESSION_DIR"
rm -f "$SENTINEL_FILE"

COMBINED_PROMPT=$(mktemp)
trap 'rm -f "$COMBINED_PROMPT"' EXIT

cat > "$COMBINED_PROMPT" <<EOF
Follow the role instructions below exactly.

--- ROLE INSTRUCTIONS ---
$(cat "$ROLE_FILE")

--- USER TASK ---
$PROMPT
EOF

set +e
cd "$PROJECT_DIR"
if [[ -n "$RESUME_SESSION_ID" ]]; then
  codex resume "$RESUME_SESSION_ID" \
    -c features.codex_hooks=true \
    --model "$MODEL" \
    --cd "$PROJECT_DIR" \
    --sandbox workspace-write \
    --full-auto \
    "$(cat "$COMBINED_PROMPT")"
  EXIT_CODE=$?
else
  codex \
    -c features.codex_hooks=true \
    --model "$MODEL" \
    --cd "$PROJECT_DIR" \
    --sandbox workspace-write \
    --full-auto \
    "$(cat "$COMBINED_PROMPT")"
  EXIT_CODE=$?
fi
set -e

# Best-effort session id persistence for later resume.
if [[ -f "$HISTORY_FILE" ]]; then
  SESSION_ID=$(tail -n 1 "$HISTORY_FILE" | jq -r '.session_id // empty' || true)
  if [[ -n "$SESSION_ID" ]]; then
    echo "$SESSION_ID" > "$SESSION_ID_FILE"
  fi
fi

# Fallback if Codex exits before the Stop hook writes the sentinel.
if [[ ! -f "$SENTINEL_FILE" ]]; then
  SESSION_ID=""
  if [[ -f "$SESSION_ID_FILE" ]]; then
    SESSION_ID=$(cat "$SESSION_ID_FILE")
  fi
  STATUS="done"
  if [[ "$EXIT_CODE" -ne 0 ]]; then
    STATUS="failed"
  fi

  jq -n \
    --arg task_id "$TASK_ID" \
    --arg role "$ROLE" \
    --arg session_id "$SESSION_ID" \
    --arg timestamp "$(date -u +%FT%TZ)" \
    --arg status "$STATUS" \
    --argjson exit_code "$EXIT_CODE" \
    '{
      task_id: $task_id,
      role: $role,
      session_id: ($session_id | if . == "" then null else . end),
      timestamp: $timestamp,
      status: $status,
      exit_code: $exit_code,
      last_message: ""
    }' > "$SENTINEL_FILE"
fi

exit "$EXIT_CODE"
