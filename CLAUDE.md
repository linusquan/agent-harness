# Agent Harness

This repository is a Claude Code orchestration harness. It is Claude-only.

The coordinator session (`claude --agent coordinator`, usually started via `./start-coordinator.sh`) delegates through the official Agent tool to project subagents in `.claude/agents/`:

- `planner` — writes `.artifacts/plans/<slug>/plan.md` (skill: `abcd-planner`)
- `builder` — implements the plan and writes `.artifacts/buildlog/<slug>.yaml` (skill: `abcd-developer`)
- `checker` — scores the build and writes `.artifacts/evaluations/<slug>.yaml` (skill: `abcd-checker`)

Pipeline: plan → build → check → retry builder on fail. Circuit breaker after 3 build-check cycles.

Do not use `dispatch.sh`, `poll.sh`, tmux child panes, or Codex. Those paths are gone.
