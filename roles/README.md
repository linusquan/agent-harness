# Available Roles

| Role | Skill | Purpose | When to use |
|---|---|---|---|
| planner | `/abcd-planner` | Analyzes codebase, produces structured plan in `.artifacts/plans/` | First step for any non-trivial task. Use before building. |
| builder | `/abcd-developer` | Implements a plan, writes code and build log to `.artifacts/buildlog/` | After a plan is approved or ready. |
| checker | `/abcd-checker` | Evaluates build against plan, runs Playwright tests, produces scored pass/fail report to `.artifacts/evaluations/` | After builder completes. All criteria must score >= 7/10 to pass. |
