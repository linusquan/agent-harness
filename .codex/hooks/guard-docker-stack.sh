#!/usr/bin/env bash
# Guard the primary src repository's deployment stack on main branches.
set -euo pipefail

input="$(cat)"
tool="$(jq -r '.tool_name // ""' <<<"$input")"
payload="$(jq -r '.tool_input.command // .tool_input.file_path // ""' <<<"$input")"

[[ "$payload" == *docker-stack.yml* || "$payload" == *docker-stack.yaml* ]] || exit 0

# apply_patch is a write. Let simple Bash reads of the stack file proceed.
if [[ "$tool" == "Bash" ]]; then
  if ! grep -Eq '(^|[[:space:];|])(sed|perl|python3?|ruby|node|tee|cp|mv|rm|touch|truncate|install|git[[:space:]]+apply|apply_patch)([[:space:];|]|$)|(^|[^<])>[>]?|--in-place|-i([[:space:]]|$)' <<<"$payload"; then
    exit 0
  fi
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
project_src="$repo_root/src"
[[ -d "$project_src/.git" ]] || exit 0

# A separate deployment worktree has its own checkout and hook config.
cwd="$(jq -r '.cwd // ""' <<<"$input")"
case "$cwd" in
  "$repo_root"|"$repo_root"/*) ;;
  *) exit 0 ;;
esac

branch="$(git -C "$project_src" branch --show-current 2>/dev/null || true)"
case "$branch" in
  main|main-v2)
    echo "BLOCKED: edit src/docker-stack.yml on deploy-test or deploy-prod, not $branch. See src/.artifacts/infra/vps-deployment-strategy.md." >&2
    exit 2
    ;;
esac
