---
name: abcd-coordinator
description: Coordinate a non-trivial SCGC feature through planning, implementation, and independent evaluation with the project planner, builder, and checker subagents. Use when asked to run the ABCD workflow or when launched by start-codex-coordinator.sh.
---

# ABCD coordinator

Coordinate work in this repository using the project agent profiles in `.codex/agents/`. Use this workflow for non-trivial features and complex fixes. Handle small troubleshooting or documentation requests directly.

## Mode

The launcher states `auto` or `semiauto` in its opening prompt. Default to `semiauto` if no mode is given. The user can switch modes during the session by saying `auto` or `semiauto`.

- `auto`: Run plan → build → check, then report. Retry failed checks up to three build/check cycles.
- `semiauto`: Show the plan before building and the build result before checking. Continue when the user approves or already instructed you to complete the whole pipeline. A specific request to run the full task authorizes its necessary phases.

Do not use checkpoints as a substitute for required safety or external action approvals. Follow the active session's permission rules for writes, commits, pushes, and deployments.

## Pipeline

1. Make a short kebab-case slug. Send the user's task verbatim to `planner`, along with the slug and `src/.artifacts/plans/<slug>/plan.md` output path. Wait for completion. Read the saved plan.
2. Summarize the plan. In `semiauto`, get user input at this checkpoint only when the next phase has not already been authorized.
3. Send `builder` the plan path, slug, and `src/.artifacts/buildlog/<slug>.yaml` output path. Wait. Read the build log and summarize the implementation.
4. In `semiauto`, get user input before evaluation only when needed under the user's instructions. Send `checker` the plan, build log, slug, and `src/.artifacts/evaluations/<slug>.yaml` output path. Wait. Read the evaluation.
5. If every criterion scores at least 7/10, report completion and the scorecard. If any criterion fails, send its `feedbackForBuilder` to the same builder agent using a follow-up task, then recheck with the same checker agent. Stop after three build/check cycles and show the remaining issues to the user.

Run dependent roles sequentially. Reuse the same role agent for revisions when available. Keep the user informed at phase changes. If a role fails or cannot produce its required artifact, explain the blocker and ask only for information actually needed to proceed.

When waiting for user input, call `./scripts/notify.sh coordinator "<short message>" "Coordinator needs input"` if notifications are available. Subagent completion notifications are handled by the Codex hook.

Application code belongs under `src/` unless the plan requires a different path. Keep artifact paths under `src/.artifacts/` consistently. Read `src/AGENTS.md` when the task concerns application code.
