---
name: abcd-planner
description: Create a structured implementation plan before making changes. Use when tackling complex tasks, multi-file changes, or ambiguous requests. Supports two modes - autonomous (default) and interactive (with human feedback).
---

# Plan Mode

You are now in **plan mode**. You may ONLY analyze, research, and produce a plan. You must NOT write implementation code, edit files, or run commands that modify state.

## Determine Mode

Parse the first argument:
- If `$ARGUMENTS` starts with `interactive` → use **Interactive Mode**
- Otherwise → use **Autonomous Mode** (treat all of `$ARGUMENTS` as the task)

---

## Autonomous Mode

1. **Analyze** the task described in `$ARGUMENTS`
2. **Research** the codebase — read relevant files, search for patterns, understand the current state
3. **Plan** — produce `plan.md` using the Autonomous Plan Format below
4. **Supporting files** — create any additional files that strengthen the plan (schemas, diagrams, checklists — see examples below)
5. **Save** everything to `{WORK_DIR}/.artifacts/plans/<slug>/` where `<slug>` is a short kebab-case descriptor (e.g. `add-oauth-support`, `fix-race-condition`)
6. **Summarize** — tell the user the plan is saved and give a brief overview
7. **Stop** — do NOT execute. Wait for the user to approve before making any changes

---

## Interactive Mode

1. **Analyze** the task described in `$ARGUMENTS` (everything after `interactive`)
2. **Ask** 2-4 clarifying questions about:
   - Goals and success criteria
   - Constraints, existing patterns, or conventions to follow
   - Scope boundaries — what's in, what's out
   - Priority tradeoffs — speed vs thoroughness, minimal vs complete
3. **Wait** for the user's answers
4. **Research** the codebase using the answers to guide exploration
5. **Plan** — produce `plan.md` using the Interactive Plan Format below
6. **Supporting files** — create any additional files that strengthen the plan
7. **Save** everything to `{WORK_DIR}/.artifacts/plans/<slug>/`
8. **Ask**: "Would you like to refine any part of this plan, or should I proceed with implementation?"
9. **Iterate** — if the user gives feedback, revise the plan and overwrite the same files
10. **Stop** — only proceed to implementation after explicit approval

---

## Plan Formats

### Autonomous Plan Format

Use this for Mode 1. The plan must be self-contained since there was no human discussion.

````markdown
# Plan: [Title]

## Objective
[1-2 sentence summary of what this accomplishes]

## Context
[Key findings from researching the codebase. What exists today, what's relevant.
Include enough detail that someone reading this cold can understand the starting point.]

## Assumptions
[List assumptions made without human input. Flag anything uncertain.]

## Approach
[High-level strategy. Why this approach over alternatives.]

## Phases

### Phase 1: [Name]
- [ ] Step 1.1: [clear, actionable description]
- [ ] Step 1.2: [clear, actionable description]

### Phase 2: [Name]
- [ ] Step 2.1: [clear, actionable description]

## Verification
- [ ] [How to confirm the solution works]
- [ ] [Edge cases to test]

## Risks
- **[Risk]** → [Mitigation]

## Supporting Files
- [List any additional files in this directory and what they contain]
````

### Interactive Plan Format

Use this for Mode 2. Captures the human's decisions so the rationale is preserved.

````markdown
# Plan: [Title]

## Objective
[1-2 sentence summary of what this accomplishes]

## Decisions
[Summarize the key decisions made during the Q&A so future readers understand WHY.]

| Question | Decision |
|----------|----------|
| [What was asked] | [What was decided] |

## Context
[Key findings from researching the codebase, informed by the decisions above.]

## Approach
[High-level strategy. Reference the decisions that shaped this choice.]

## Phases

### Phase 1: [Name]
- [ ] Step 1.1: [clear, actionable description]
- [ ] Step 1.2: [clear, actionable description]

### Phase 2: [Name]
- [ ] Step 2.1: [clear, actionable description]

## Verification
- [ ] [How to confirm the solution works]
- [ ] [Edge cases to test]

## Risks
- **[Risk]** → [Mitigation]

## Supporting Files
- [List any additional files in this directory and what they contain]
````

---

## Supporting Files

The `plan.md` is always required. Add supporting files when they make the plan clearer or more actionable. Reference them from the "Supporting Files" section of `plan.md`.

Create supporting files when:
- A schema, data model, or API contract would clarify the plan
- A migration has a sequence that benefits from its own checklist
- There are code snippets, configs, or templates that the executor will need
- A diagram (mermaid, ASCII) would explain architecture or flow
- Research findings are long enough to clutter the plan

Do NOT create supporting files just to have them. If the plan is simple, `plan.md` alone is fine.

---

## Examples

### Example 1: Feature — notification system

```
{WORK_DIR}/.artifacts/plans/add-notifications/
├── plan.md              # Main plan with phases
├── schema.sql           # Proposed database tables
└── api-contract.md      # Endpoint specs (method, path, request/response shape)
```

### Example 2: Refactor — extract auth module

```
{WORK_DIR}/.artifacts/plans/extract-auth-module/
├── plan.md              # Main plan with phases
└── file-moves.md        # Table mapping old paths → new paths
```

### Example 3: Bug fix — race condition in queue

```
{WORK_DIR}/.artifacts/plans/fix-queue-race-condition/
└── plan.md              # Simple plan, no supporting files needed
```

### Example 4: Migration — upgrade database ORM

```
{WORK_DIR}/.artifacts/plans/upgrade-orm-v5/
├── plan.md              # Main plan with phases
├── breaking-changes.md  # List of breaking changes from changelog
├── migration-checklist.md  # File-by-file checklist of what to update
└── rollback-steps.md    # How to revert if something goes wrong
```

### Example 5: Architecture — redesign data pipeline

```
{WORK_DIR}/.artifacts/plans/redesign-data-pipeline/
├── plan.md              # Main plan with phases
├── architecture.mermaid # Diagram of new pipeline flow
├── data-flow.md         # Detailed description of each stage
└── benchmark-targets.md # Performance targets and how to measure
```

### Example 6: Infrastructure — add CI/CD pipeline

```
{WORK_DIR}/.artifacts/plans/add-ci-cd/
├── plan.md              # Main plan with phases
├── pipeline.yml         # Draft pipeline config
└── env-vars.md          # Required environment variables and secrets
```

---

## Rules

- **No implementation during planning.** Read-only operations only: read files, search, list directories. Do not edit, create, or run anything that changes state outside `{WORK_DIR}/.artifacts/plans/`.
- **Always save `plan.md`** before doing anything else.
- **One plan per directory.** If revised, overwrite files in the same directory.
- **Keep steps actionable.** Each step is a clear action, not a paragraph.
- **Name directories descriptively.** `fix-auth-token-refresh` not `plan-1`.
- **Create parent directories** if they don't exist (`{WORK_DIR}/.artifacts/plans/`).