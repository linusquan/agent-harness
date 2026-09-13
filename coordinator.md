# Coordinator

The live coordinator agent is [`.claude/agents/coordinator.md`](.claude/agents/coordinator.md).

Start it with:

```bash
./start-coordinator.sh
```

That launches Claude Code as `claude --agent coordinator`. The coordinator delegates to project subagents (`planner`, `builder`, `checker`) via the Agent tool. It does not run `dispatch.sh` or `poll.sh`.
