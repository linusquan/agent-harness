---
name: coordinator
description: Compatibility alias only. Prefer opening the main session — CLAUDE.md / AGENTS.md already make you the coordinator. Do not dispatch this subagent. Do not use for implementation yourself.
tools: Agent(planner, builder, checker), Read, Grep, Glob, Bash, Write, Edit, SendMessage, TodoWrite
model: inherit
color: purple
---

# Coordinator alias

The default path is opening this repository: the main session **is** the coordinator.

Follow **`CLAUDE.md`** (same role as **`AGENTS.md`**). Those files are the live orchestration spec: dispatch only; plan → build → check; semiauto/auto; circuit breaker at 3; pass the user task verbatim to planner; resume the same subagent on re-dispatch when possible.

This file exists so `claude --agent coordinator` and `./start-coordinator.sh` still work. Prefer the main session. Do not implement features yourself. Do not use `dispatch.sh`, `poll.sh`, tmux child panes, or Codex.
