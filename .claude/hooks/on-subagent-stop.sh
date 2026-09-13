#!/bin/bash
# Notify when a planner/builder/checker subagent finishes.
# Replaces the old poll.sh completion ping.

set -euo pipefail

INPUT=$(cat)
AGENT_TYPE=$(echo "$INPUT" | jq -r '.agent_type // .agent_id // "agent"' 2>/dev/null || echo "agent")

case "$AGENT_TYPE" in
  planner|builder|checker) ;;
  *) exit 0 ;;
esac

ROLE_TITLE=$(echo "$AGENT_TYPE" | awk '{print toupper(substr($0,1,1)) substr($0,2)}')
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/../../scripts/notify.sh" "$AGENT_TYPE" "$AGENT_TYPE finished" "$ROLE_TITLE done" 2>/dev/null || true
