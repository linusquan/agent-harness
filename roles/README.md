# Available Roles

Live agent definitions are in [`.claude/agents/`](../.claude/agents/). These files document purpose; the coordinator invokes them with the Agent tool.

| Role | Agent file | Skill (preloaded) | Purpose | When to use |
|---|---|---|---|---|
| planner | `.claude/agents/planner.md` | `/abcd-planner` | Analyzes codebase, produces structured plan in `.artifacts/plans/` | First step for any non-trivial task. Use before building. |
| builder | `.claude/agents/builder.md` | `/abcd-developer` | Implements a plan, writes code and build log to `.artifacts/buildlog/` | After a plan is approved or ready. |
| checker | `.claude/agents/checker.md` | `/abcd-checker` | Evaluates build against plan, runs Playwright tests, produces scored pass/fail report to `.artifacts/evaluations/` | After builder completes. All criteria must score >= 7/10 to pass. |

Project context shared by the role agents: [`shared/shared.md`](shared/shared.md).
