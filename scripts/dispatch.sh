#!/bin/bash
# Dispatch a child agent session with a role-specific prompt
# Usage: ./scripts/dispatch.sh <role> <complexity> <prompt> [--task-id <id>] [--agentbase claude|codex]
#
# Complexity levels:
#   simple  → haiku
#   mid     → sonnet
#   complex → opus
#
# Options:
#   --task-id <id>           Reuse an existing task ID instead of generating a new one
#   --agentbase claude|codex Override HARNESS_AGENTBASE for this dispatch
#
# Examples:
#   ./scripts/dispatch.sh planner complex "analyze the auth module"
#   ./scripts/dispatch.sh builder mid "implement the plan" --task-id builder-destiny
#   ./scripts/dispatch.sh checker complex "evaluate the build" --agentbase codex

set -euo pipefail

ROLE="${1:?Usage: dispatch.sh <role> <complexity> <prompt> [--task-id <id>]}"
COMPLEXITY="${2:?Usage: dispatch.sh <role> <complexity> <prompt> [--task-id <id>]}"
PROMPT="${3:?Usage: dispatch.sh <role> <complexity> <prompt> [--task-id <id>]}"
AGENTBASE="${HARNESS_AGENTBASE:-claude}"

resolve_model() {
  local runtime="$1"
  local requested="$2"

  if [[ "$runtime" == "codex" ]]; then
    case "$requested" in
      haiku|sonnet) echo "gpt-5.4-mini" ;;
      opus) echo "gpt-5.4" ;;
      *) echo "$requested" ;;
    esac
  else
    echo "$requested"
  fi
}

build_shell_command() {
  local cmd=""
  local arg

  for arg in "$@"; do
    printf -v cmd '%s%q ' "$cmd" "$arg"
  done

  printf '%s' "${cmd% }"
}

# Map complexity to model
case "$COMPLEXITY" in
  simple)  MODEL="haiku" ;;
  mid)     MODEL="sonnet" ;;
  complex) MODEL="opus" ;;
  *) echo "Error: complexity must be simple, mid, or complex" >&2; exit 1 ;;
esac
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Use provided task ID or generate a new one
# Parse optional flags
TASK_ID=""
REUSE_TASK=false
shift 3  # consume role, complexity, prompt — remaining are optional flags
while [[ $# -gt 0 ]]; do
  case "$1" in
    --task-id)    TASK_ID="$2"; REUSE_TASK=true; shift 2 ;;
    --agentbase)  AGENTBASE="$2"; shift 2 ;;
    *) echo "Error: unknown option $1" >&2; exit 1 ;;
  esac
done

if [[ -n "$TASK_ID" ]]; then
  # Clean up old sentinel so poll.sh can wait for the new one
  rm -f "$PROJECT_DIR/sessions/$TASK_ID.done"
  rm -f "$PROJECT_DIR/sessions/$TASK_ID.pane"
else
  TASK_ID=$(node "$PROJECT_DIR/scripts/agent-name.mjs" "$ROLE")
fi

# Validate role
if [ ! -f "$PROJECT_DIR/roles/$ROLE.md" ]; then
  echo "Error: no role file found at roles/$ROLE.md" >&2
  exit 1
fi

MODEL=$(resolve_model "$AGENTBASE" "$MODEL")

if [[ "$AGENTBASE" == "codex" ]]; then
  ROLE_FILE="./roles/$ROLE.md"
  SESSION_ID_FILE="$PROJECT_DIR/sessions/$TASK_ID.codex-session"
  if [[ -f "$SESSION_ID_FILE" ]]; then
    AGENT_CMD=$(build_shell_command \
      ./scripts/run-codex-task.sh \
      "$TASK_ID" \
      "$ROLE" \
      "$MODEL" \
      "$ROLE_FILE" \
      "$PROMPT" \
      --resume-session \
      "$(cat "$SESSION_ID_FILE")")
  else
    AGENT_CMD=$(build_shell_command \
      ./scripts/run-codex-task.sh \
      "$TASK_ID" \
      "$ROLE" \
      "$MODEL" \
      "$ROLE_FILE" \
      "$PROMPT")
  fi
else
  # Build claude command — resume if reusing a task ID, otherwise start fresh
  if [[ "$REUSE_TASK" == "true" ]]; then
    AGENT_CMD="claude \"$PROMPT\" --model $MODEL --resume $TASK_ID --append-system-prompt-file ./roles/$ROLE.md --dangerously-skip-permissions"
  else
    AGENT_CMD="claude \"$PROMPT\" --model $MODEL -n $TASK_ID --append-system-prompt-file ./roles/$ROLE.md --dangerously-skip-permissions"
  fi
fi

# Spawn child session in a horizontal split pane, capture pane ID
PANE_ID=$(tmux split-window -h -P -F "#{pane_id}" -c "$PROJECT_DIR" \
  -e "HARNESS_TASK_ID=$TASK_ID" \
  -e "HARNESS_ROLE=$ROLE" \
  -e "HARNESS_AGENTBASE=$AGENTBASE" \
  "$AGENT_CMD")

# Save pane ID so poll.sh can close it
mkdir -p "$PROJECT_DIR/sessions"
echo "$PANE_ID" > "$PROJECT_DIR/sessions/$TASK_ID.pane"

echo "Dispatched: role=$ROLE task=$TASK_ID pane=$PANE_ID agentbase=$AGENTBASE"
echo "Poll with: ./scripts/poll.sh $TASK_ID"
