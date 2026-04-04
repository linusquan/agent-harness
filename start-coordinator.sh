#!/bin/bash
# Start the central coordinator Claude Code session
# Usage: ./start-coordinator.sh [--mode auto|semiauto] [--model <model>]
set -euo pipefail

# ── Defaults ──
MODE="semiauto"
MODEL="sonnet"

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)   MODE="$2"; shift 2 ;;
    --model)  MODEL="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

if [[ "$MODE" != "auto" && "$MODE" != "semiauto" ]]; then
  echo "Error: --mode must be 'auto' or 'semiauto'" >&2
  exit 1
fi

if ! command -v tmux &>/dev/null; then
  echo "Error: tmux is not installed" >&2
  exit 1
fi

if [ -n "${TMUX:-}" ]; then
  echo "Error: already inside a tmux session. Run this from outside tmux." >&2
  exit 1
fi

tmux kill-session -t coordinator 2>/dev/null || true

# ── Start artifact browser ───────────────────────────────────────────────────
ARTIFACT_BROWSER_PORT="${ARTIFACT_BROWSER_PORT:-28080}"
node "$PROJECT_DIR/scripts/artifact-browser.js" &
ARTIFACT_BROWSER_PID=$!

# Give it 500 ms to fail fast (e.g. port already in use)
sleep 0.5
if ! kill -0 "$ARTIFACT_BROWSER_PID" 2>/dev/null; then
  echo "Warning: artifact browser failed to start" >&2
else
  echo "Artifact browser started on http://localhost:$ARTIFACT_BROWSER_PORT"
fi

# Kill the browser when this shell exits (tmux new-session blocks until session ends)
trap 'kill "$ARTIFACT_BROWSER_PID" 2>/dev/null || true' EXIT
# ────────────────────────────────────────────────────────────────────────────

tmux new-session -s coordinator -c "$PROJECT_DIR" \
  -e "HARNESS_MODE=$MODE" \
  "claude --model $MODEL --append-system-prompt-file ./coordinator.md"
