#!/usr/bin/env bash
set -euo pipefail

input="$(cat)"
agent_type="$(jq -r '.agent_type // ""' <<<"$input")"
case "$agent_type" in
  planner|builder|checker) ;;
  *) printf '{}\n'; exit 0 ;;
esac

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$script_dir/../../scripts/notify.sh" "$agent_type" "$agent_type finished" "$agent_type done" >/dev/null 2>&1 || true
printf '{}\n'
