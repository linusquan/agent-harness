# Coordinator

The main session **is** the coordinator. Open this repository in Claude Code or Cursor Agent and give it a task — no special entrypoint needed.

Live spec (keep these in sync):

- [`CLAUDE.md`](CLAUDE.md) — Claude Code project instructions
- [`AGENTS.md`](AGENTS.md) — Cursor-native project instructions

`.claude/agents/coordinator.md` is a thin alias so `claude --agent coordinator` and `./start-coordinator.sh` still work. Prefer opening the project.

Working subagents are only `planner`, `builder`, and `checker`. The coordinator does not run `dispatch.sh` or `poll.sh`.
