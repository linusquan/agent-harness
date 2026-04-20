#!/bin/bash
# Start the central coordinator agent session
# Usage: ./start-coordinator.sh [--mode auto|semiauto] [--model <model>] [--agentbase claude|codex]
set -euo pipefail

# ── Defaults ──
MODE="semiauto"
MODEL="sonnet"
AGENTBASE="${HARNESS_AGENTBASE:-claude}"

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Parse args ───────────────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)   MODE="$2"; shift 2 ;;
    --model)  MODEL="$2"; shift 2 ;;
    --agentbase) AGENTBASE="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

if [[ "$MODE" != "auto" && "$MODE" != "semiauto" ]]; then
  echo "Error: --mode must be 'auto' or 'semiauto'" >&2
  exit 1
fi

if [[ "$AGENTBASE" != "claude" && "$AGENTBASE" != "codex" ]]; then
  echo "Error: --agentbase must be 'claude' or 'codex'" >&2
  exit 1
fi

# ── Functions ────────────────────────────────────────────────────────────────

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

runtime_command_name() {
  if [[ "$1" == "codex" ]]; then
    echo "codex"
  else
    echo "claude"
  fi
}

start_runtime_in_session() {
  local session_name="$1"
  local runtime="$2"
  local model="$3"
  local resolved_model
  resolved_model=$(resolve_model "$runtime" "$model")

  if [[ "$runtime" == "codex" ]]; then
    local session_id_file="$PROJECT_DIR/sessions/$session_name.codex-session"
    if [[ -f "$session_id_file" ]]; then
      local resume_session_id
      resume_session_id=$(cat "$session_id_file")
      tmux send-keys -t "$session_name" \
        "./scripts/run-codex-interactive.sh '$session_name' '$resolved_model' ./coordinator.md --resume-session '$resume_session_id'" Enter
    else
      tmux send-keys -t "$session_name" \
        "./scripts/run-codex-interactive.sh '$session_name' '$resolved_model' ./coordinator.md" Enter
    fi
  else
    tmux send-keys -t "$session_name" \
      "claude --model $resolved_model -n '$session_name' --append-system-prompt-file ./coordinator.md" Enter
  fi
}

start_artifact_browser() {
  local port="${ARTIFACT_BROWSER_PORT:-28080}"

  # Kill any existing process on the port
  local existing_pid
  existing_pid=$(lsof -ti:"$port" 2>/dev/null || true)
  if [ -n "$existing_pid" ]; then
    echo "Killing existing process on port $port (PID $existing_pid)"
    kill $existing_pid 2>/dev/null || true
    sleep 0.5
  fi

  node "$PROJECT_DIR/scripts/artifact-browser.js" &
  ARTIFACT_BROWSER_PID=$!

  # Give it 500 ms to fail fast (e.g. port already in use)
  sleep 0.5
  if ! kill -0 "$ARTIFACT_BROWSER_PID" 2>/dev/null; then
    echo "Warning: artifact browser failed to start" >&2
  else
    echo "Artifact browser started on http://localhost:$port"
  fi
}

# Find all existing tmux sessions matching coordinator-*
find_coordinator_sessions() {
  tmux list-sessions -F '#{session_name}' 2>/dev/null | grep '^coordinator-' || true
}

# Interactive session picker: attach existing or create new
choose_coordinator() {
  local sessions
  sessions=$(find_coordinator_sessions)

  if [ -z "$sessions" ]; then
    echo "No existing coordinator sessions found. Creating a new one..."
    create_new_coordinator
    return
  fi

  # Build menu
  local options=()
  while IFS= read -r name; do
    options+=("$name")
  done <<< "$sessions"

  local selected=0
  local count=${#options[@]}
  local total=$((count + 1))  # +1 for "Create new"

  echo ""
  echo "  Coordinator Sessions"
  echo "  ────────────────────"

  # Draw menu and handle input
  while true; do
    # Move cursor up to redraw (except first time)
    if [ "${_drawn:-}" = "1" ]; then
      printf '\033[%dA' "$total"
    fi
    _drawn=1

    for i in $(seq 0 $((count - 1))); do
      if [ "$i" -eq "$selected" ]; then
        printf '  \033[7m ▸ %s \033[0m\n' "${options[$i]}"
      else
        printf '    %s\n' "${options[$i]}"
      fi
    done

    # "Create new" option
    if [ "$selected" -eq "$count" ]; then
      printf '  \033[7m ▸ ✚ Create new coordinator \033[0m\n'
    else
      printf '    ✚ Create new coordinator\n'
    fi

    # Read a single keypress
    IFS= read -rsn1 key
    if [[ "$key" == $'\x1b' ]]; then
      read -rsn2 rest
      key+="$rest"
    fi

    case "$key" in
      $'\x1b[A'|k)  # Up
        selected=$(( (selected - 1 + total) % total ))
        ;;
      $'\x1b[B'|j)  # Down
        selected=$(( (selected + 1) % total ))
        ;;
      "")  # Enter
        break
        ;;
      q)
        echo ""
        echo "  Cancelled."
        exit 0
        ;;
    esac
  done

  echo ""

  if [ "$selected" -eq "$count" ]; then
    create_new_coordinator
  else
    local chosen="${options[$selected]}"
    echo "Resuming session: $chosen"
    local session_agentbase="$AGENTBASE"
    local session_env
    session_env=$(tmux show-environment -t "$chosen" HARNESS_AGENTBASE 2>/dev/null || true)
    if [[ "$session_env" == HARNESS_AGENTBASE=* ]]; then
      session_agentbase="${session_env#HARNESS_AGENTBASE=}"
    fi

    local runtime_cmd
    runtime_cmd=$(runtime_command_name "$session_agentbase")
    if ! tmux list-panes -t "$chosen" -F '#{pane_current_command}' 2>/dev/null | grep -q "^${runtime_cmd}$"; then
      if [[ "$session_agentbase" == "codex" ]]; then
        start_runtime_in_session "$chosen" "$session_agentbase" "$MODEL"
      else
        local resolved_model
        resolved_model=$(resolve_model "$session_agentbase" "$MODEL")
        tmux send-keys -t "$chosen" \
          "claude --model $resolved_model --resume '$chosen' --append-system-prompt-file ./coordinator.md" Enter
      fi
    fi
    tmux attach-session -t "$chosen"
  fi
}

create_new_coordinator() {
  local session_name
  session_name=$(node "$PROJECT_DIR/scripts/agent-name.mjs" coordinator)

  echo "Creating session: $session_name (detach with Ctrl+b d to keep it alive)"
  tmux new-session -d -s "$session_name" -c "$PROJECT_DIR" \
    -e "HARNESS_MODE=$MODE" \
    -e "HARNESS_AGENTBASE=$AGENTBASE"
  start_runtime_in_session "$session_name" "$AGENTBASE" "$MODEL"
  tmux attach-session -t "$session_name"
}

start_coordinator() {
  if ! command -v tmux &>/dev/null; then
    echo "Error: tmux is not installed" >&2
    exit 1
  fi

  if [ -n "${TMUX:-}" ]; then
    echo "Error: already inside a tmux session. Run this from outside tmux." >&2
    exit 1
  fi

  choose_coordinator
}

# ── Main ─────────────────────────────────────────────────────────────────────

start_artifact_browser

# Kill the browser when this shell exits (tmux new-session blocks until session ends)
trap 'kill "$ARTIFACT_BROWSER_PID" 2>/dev/null || true' EXIT

start_coordinator
