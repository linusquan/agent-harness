#!/bin/bash
# Run the interactive Codex coordinator session and persist its session id after exit.
# Usage: ./scripts/run-codex-interactive.sh <session-name> <model> <prompt-file> [--resume-session <id>]

set -euo pipefail

SESSION_NAME="${1:?Usage: run-codex-interactive.sh <session-name> <model> <prompt-file> [--resume-session <id>]}"
MODEL="${2:?Usage: run-codex-interactive.sh <session-name> <model> <prompt-file> [--resume-session <id>]}"
PROMPT_FILE="${3:?Usage: run-codex-interactive.sh <session-name> <model> <prompt-file> [--resume-session <id>]}"

RESUME_SESSION_ID=""
if [[ "${4:-}" == "--resume-session" && -n "${5:-}" ]]; then
  RESUME_SESSION_ID="$5"
fi

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SESSION_DIR="$PROJECT_DIR/sessions"
SESSION_ID_FILE="$SESSION_DIR/$SESSION_NAME.codex-session"
HISTORY_FILE="${CODEX_HOME:-$HOME/.codex}/history.jsonl"

mkdir -p "$SESSION_DIR"

if [[ -n "$RESUME_SESSION_ID" ]]; then
  codex resume "$RESUME_SESSION_ID" \
    -c features.codex_hooks=true \
    --model "$MODEL" \
    --cd "$PROJECT_DIR" \
    --sandbox workspace-write \
    --full-auto
else
  codex \
    -c features.codex_hooks=true \
    --model "$MODEL" \
    --cd "$PROJECT_DIR" \
    --sandbox workspace-write \
    --full-auto \
    "$(cat "$PROMPT_FILE")"
fi

if [[ -f "$HISTORY_FILE" ]]; then
  LAST_SESSION_ID=$(tail -n 1 "$HISTORY_FILE" | jq -r '.session_id // empty' || true)
  if [[ -n "$LAST_SESSION_ID" ]]; then
    echo "$LAST_SESSION_ID" > "$SESSION_ID_FILE"
  fi
fi
