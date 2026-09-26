#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

mode="semiauto"
codex_args=()
codex_arg_count=0
while (($#)); do
  case "$1" in
    --mode)
      if (($# < 2)); then
        echo "--mode requires auto or semiauto" >&2
        exit 2
      fi
      mode="$2"
      shift 2
      ;;
    --mode=*)
      mode="${1#--mode=}"
      shift
      ;;
    *)
      codex_args+=("$1")
      codex_arg_count=$((codex_arg_count + 1))
      shift
      ;;
  esac
done

case "$mode" in
  auto|semiauto) ;;
  *) echo "Invalid mode: $mode (expected auto or semiauto)" >&2; exit 2 ;;
esac

export HARNESS_MODE="$mode"
prompt="\$abcd-coordinator Run this session in $mode mode. Store ABCD work artifacts in one child page per feature slug under https://app.notion.com/p/Engineering-Work-Artifacts-3e63381a46dd8009a5c4f439abd54345. Use Plan, Build Log, and Evaluation sections and pass the feature page URL to each role. This user instruction overrides local artifact paths in the workflow skills. Do not write new ABCD artifacts under src/.artifacts/. If Notion is unavailable, report the connection blocker. Wait for my task."
if ((codex_arg_count > 0)); then
  exec codex --sandbox workspace-write --ask-for-approval never "${codex_args[@]}" "$prompt"
else
  exec codex --sandbox workspace-write --ask-for-approval never "$prompt"
fi
