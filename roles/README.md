# Available Roles

The **main session** is the coordinator (`CLAUDE.md` / `AGENTS.md`). It invokes these roles with the host's native subagent tool (Claude Code: Agent; Cursor: Task).

Live agent definitions: [`.claude/agents/`](../.claude/agents/). Cursor-native mirrors (same behaviour; keep in sync): [`.cursor/agents/`](../.cursor/agents/).

| Role | Claude file | Cursor mirror | Skill | Purpose | When to use |
|---|---|---|---|---|---|
| planner | `.claude/agents/planner.md` | `.cursor/agents/planner.md` | `/abcd-planner` | Analyzes codebase, produces structured plan in `.artifacts/plans/` | First step for any non-trivial task. Use before building. |
| builder | `.claude/agents/builder.md` | `.cursor/agents/builder.md` | `/abcd-developer` | Implements a plan, writes code and build log to `.artifacts/buildlog/` | After a plan is approved or ready. |
| checker | `.claude/agents/checker.md` | `.cursor/agents/checker.md` | `/abcd-checker` | Evaluates build against plan, runs Playwright tests, produces scored pass/fail report to `.artifacts/evaluations/` | After builder completes. All criteria must score >= 7/10 to pass. |

There is no working coordinator *subagent*. `.claude/agents/coordinator.md` is a compatibility alias only.

Project context shared by the role agents: [`shared/shared.md`](shared/shared.md).
