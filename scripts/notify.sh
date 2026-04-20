#!/bin/bash
# Send a push notification via ntfy.sh
# Usage: ./scripts/notify.sh <role> <message> [title]
#
# All notifications go to a single topic: lquan-agent-harness
# role is shown in the title so you know which agent fired it.
#
# Exits silently on failure — never breaks the pipeline.

ROLE="${1:-agent}"
MESSAGE="${2:-Done}"
TITLE="${3:-$(echo "$ROLE" | awk '{print toupper(substr($0,1,1)) substr($0,2)}')}"

NTFY_URL="https://ntfy.sh/lquan-agent-harness"

curl -s -o /dev/null \
  -H "Title: $TITLE" \
  -d "$MESSAGE" \
  "$NTFY_URL" 2>/dev/null || true
