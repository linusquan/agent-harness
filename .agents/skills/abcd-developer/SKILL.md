---
name: abcd-developer
description: Implement an ABCD plan for SCGC, verify the changed behavior, and write a YAML build log to src/.artifacts/buildlog/<slug>.yaml. Use for the builder phase after a plan exists.
---

# ABCD builder

Implement the plan at `src/.artifacts/plans/<slug>/plan.md` supplied by the coordinator. Read `src/AGENTS.md` for application work. Keep the plan's objective and verification criteria in view; document justified deviations in the build log.

1. Read the plan and relevant source. Identify the files to change and the checks that demonstrate the result.
2. Implement the feature under `src/` unless the plan specifies another path. Follow existing patterns and handle relevant failure cases.
3. Verify the primary flow and meaningful edge or error cases. For a running web UI, use the configured Playwright MCP when available. For non-UI work, run suitable tests or commands. Record tests that cannot run and why.
4. Write `src/.artifacts/buildlog/<slug>.yaml` with the schema below. Use the same slug as the plan. Do not claim a test passed unless you ran it.

```yaml
feature: "<slug>"
description: "What was built"
filesChanged:
  - path: "src/path/to/file"
    action: created | modified | deleted
    summary: "What changed"
mainImplementationStrategy: |
  Implementation approach and any plan deviations.
assumptionsMade:
  - "Relevant assumption, if any"
testsPerformed:
  - id: "T-01"
    type: happy-path | edge-case | error-handling
    description: "Test and expected result"
    result: pass | fail | blocked
    failureReason: "Include for fail or blocked"
commitHash: null
commitMessage: null
notes: |
  Blockers, caveats, or follow-up work.
```

If a commit is requested and authorized, record its hash and message. Otherwise leave both fields `null`. Return the build log path and a concise implementation summary.
