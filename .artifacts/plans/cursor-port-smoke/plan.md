# Plan: Cursor Port Smoke Test — `.artifacts/VERIFY.md` Stub

## Objective

Create a single stub file at `.artifacts/VERIFY.md` and change nothing else in the repository. This is a deliberately minimal end-to-end exercise of the Cursor-ported plan → build → check pipeline, where the artifact itself is trivial and the real subject under test is the harness.

## Context

Findings from inspecting the repository at commit `02138b6` on branch `cursor/main-session-coordinator-03b9`:

- **This is an orchestration harness, not an application.** `AGENTS.md` (Cursor) and `CLAUDE.md` (Claude Code) define the same coordinator role and must stay in sync. Working subagents are only `planner`, `builder`, and `checker`.
- **The Cursor port mirrors the Claude agents.** `.cursor/agents/` contains `planner.md`, `builder.md`, and `checker.md`, each a mirror of its `.claude/agents/` counterpart. Skills still live only under `.claude/skills/` and are referenced by absolute path from both sides, so the Cursor agents depend on the `.claude/skills/` tree remaining in place.
- **`.artifacts/` does not exist yet.** Nothing in the working tree creates it; every pipeline stage is expected to create its own subdirectory on demand (`plans/`, `buildlog/`, `evaluations/`).
- **`.artifacts/` is gitignored.** `.gitignore` lists it twice, at lines 7 and 10; `git check-ignore -v .artifacts/VERIFY.md` confirms line 10 matches. This is the single most important constraint for this task: the deliverable is intentionally untracked, so there is no commit to make and no diff to review on a branch.
- **The builder's default instinct conflicts with this task.** `.cursor/agents/builder.md` says to write application code under `src/` "unless the plan specifies otherwise", and the `abcd-developer` skill's normal workflow includes Playwright testing and a git commit producing `commitHash` / `commitMessage` in the build log. None of that applies here, so this plan overrides all three explicitly.
- **Working tree is clean**, which makes "nothing else changed" easy to verify with `git status`.

## Assumptions

- "Under `.artifacts/` only" is a scope fence, not just a path hint: the builder must not touch `src/`, `.cursor/`, `.claude/`, `.gitignore`, or any tracked file.
- The file belongs directly at `.artifacts/VERIFY.md`, not nested in a subdirectory such as `.artifacts/plans/cursor-port-smoke/`.
- "Stub" means short, human-readable placeholder content that states what the file is for. There is no prescribed schema, so the exact wording is the builder's choice within the shape suggested below.
- The gitignore status is intended and must be left alone. The builder should **not** `git add -f` the file and should **not** amend `.gitignore` to make it trackable. If the user actually wants a committed verification document, that is a different task with a different target path.
- The build log at `.artifacts/buildlog/cursor-port-smoke.yaml` is an expected, allowed side effect — it lives under `.artifacts/` and is required by the builder's own contract.

## Approach

Do the smallest correct thing and make the constraints explicit so downstream agents do not embellish. The risk in a task this small is not under-delivery but over-delivery: a builder running the full `abcd-developer` workflow could scaffold `src/`, launch a dev server, attempt Playwright checks, or force-add an ignored file — any of which would break the "under `.artifacts/` only" requirement and pollute the smoke test signal.

So the plan is one phase of file creation plus one phase of negative verification (proving nothing else moved). Alternatives considered and rejected: putting the stub somewhere tracked so the port can be reviewed in a PR (contradicts the instruction), and expanding the stub into a real verification checklist for the Cursor port (out of scope; a stub was requested).

## Phases

### Phase 1: Create the stub

- [ ] Step 1.1: Create the `.artifacts/` directory if it does not already exist.
- [ ] Step 1.2: Write `.artifacts/VERIFY.md` with a top-level heading and two or three lines of placeholder content identifying it as a smoke-test stub for the Cursor port of the ABCD harness.
- [ ] Step 1.3: Do not create, modify, or delete any other file. Specifically: no `src/` scaffolding, no `.gitignore` edits, no changes under `.cursor/` or `.claude/`.

### Phase 2: Record and verify

- [ ] Step 2.1: Write the build log to `.artifacts/buildlog/cursor-port-smoke.yaml`, creating `.artifacts/buildlog/` if needed.
- [ ] Step 2.2: In the build log, set the commit fields to `null` (or omit them) and note the reason: the deliverable is gitignored, so nothing was committed. Do not invent a commit hash.
- [ ] Step 2.3: In the build log, note that Playwright/browser testing was skipped as not applicable — there is no running application in this task.
- [ ] Step 2.4: Run `git status --short` and confirm the output is empty.

## Verification

- [ ] `.artifacts/VERIFY.md` exists, is non-empty, and is valid Markdown with at least one heading.
- [ ] The file is directly under `.artifacts/`, not nested deeper.
- [ ] `git status --short` returns no output, confirming no tracked file changed and nothing new became stageable.
- [ ] `git check-ignore -v .artifacts/VERIFY.md` still reports the `.gitignore:10:.artifacts/` rule, confirming the ignore behaviour was not subverted.
- [ ] `.gitignore` is byte-for-byte unchanged versus `HEAD`.
- [ ] No `src/` directory was created.
- [ ] `.artifacts/buildlog/cursor-port-smoke.yaml` exists and parses as YAML.

Edge cases worth checking: a pre-existing `.artifacts/VERIFY.md` (overwrite is fine, but the build log should say so), and a builder that creates `.artifacts/` but leaves it empty on failure.

## Risks

- **Builder over-builds by following the `abcd-developer` default of writing code under `src/`** → Phase 1 Step 1.3 forbids it explicitly, and the plan states the builder-agent default is overridden here.
- **Builder force-adds the ignored file or edits `.gitignore` to "fix" it** → Called out in Assumptions and re-checked in Verification via `git check-ignore` and the unchanged-`.gitignore` check.
- **Builder fabricates a commit hash to satisfy the build-log schema** → Phase 2 Step 2.2 requires null commit fields with a stated reason.
- **Checker scores this as thin or incomplete work** → The objective states that minimality is the point; the evaluation should grade harness mechanics (correct paths, correct artifacts, clean tree) rather than feature depth.
- **The stub is invisible to code review because `.artifacts/` is gitignored** → Expected and intended. Anyone verifying the smoke test must inspect the working tree on the agent VM, not a diff.

## Supporting Files

None. The task is small enough that `plan.md` alone is sufficient.
