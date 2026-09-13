# Verification: Cursor main-session coordinator port

- **Repo:** `linusquan/agent-harness`
- **Branch verified:** `cursor/main-session-coordinator-03b9` (`02138b6`)
- **PR:** https://github.com/linusquan/agent-harness/pull/2
- **Base:** `main` (`645818c`)
- **Verified at:** 2026-09-13T23:14:00Z
- **Verifier session:** Cursor Cloud agent (https://cursor.com/agents/bc-ca75529a-2953-53c2-9a24-812cea924aa4)
- **Scope:** SPEC checklist + coordinator-discipline smoke. No product feature implemented. Nothing merged.

**Overall verdict: `MEETS_WITH_GAPS`**

The PR does make opening the repo the happy-path coordinator in both Claude Code (`CLAUDE.md`) and Cursor (`AGENTS.md` + always-on rule + `.cursor/agents/` mirrors). The plan → build → check Task path worked in this cloud session. Residual gaps are small and listed in §C.

---

## A. Static checklist

Each SPEC item is `PASS` / `FAIL` / `PARTIAL` with file evidence.

### 1. Opening the repo: main session IS the ABCD coordinator

**PASS**

Happy path does not require `claude --agent coordinator` or `./start-coordinator.sh`.

| File | Evidence |
|---|---|
| `CLAUDE.md` / `AGENTS.md` L3 | “You are the **ABCD coordinator**. Opening this repository is enough: the main session already has this role. You do not need `claude --agent coordinator` or `./start-coordinator.sh` for the happy path.” |
| `README.md` L31–51 | “Open this repository in **Cursor Agent** or **Claude Code**. The main chat is already the coordinator” … “No special entrypoint is required for the happy path.” |
| `coordinator.md` L3 | “The main session **is** the coordinator. Open this repository in Claude Code or Cursor Agent and give it a task — no special entrypoint needed.” |
| `start-coordinator.sh` L1–3 | “Optional Claude Code launcher. The default path is opening this repo — CLAUDE.md / AGENTS.md already make the main session the coordinator.” |

`CLAUDE.md` and `AGENTS.md` are byte-identical (`diff` empty). README documents Cursor loading `AGENTS.md` + `.cursor/rules/abcd-coordinator.mdc` and Claude Code loading `CLAUDE.md`.

### 2. Working subagents are only planner, builder, checker

**PASS** (with a visibility note; see gap G1)

Documented working set is exactly those three. Live agent files:

| Host | Files present |
|---|---|
| Claude Code | `.claude/agents/{planner,builder,checker}.md` plus a **non-working** `coordinator.md` alias |
| Cursor | `.cursor/agents/{planner,builder,checker}.md` only — no Cursor coordinator agent file |

Quotes:

- `CLAUDE.md` / `AGENTS.md` L9–13: “Working subagents (only these three): `planner` … `builder` … `checker`”
- `roles/README.md` L13: “There is no working coordinator *subagent*. `.claude/agents/coordinator.md` is a compatibility alias only.”
- `README.md` L79: “Only **planner**, **builder**, and **checker** are working subagents.”

**Note:** This Cursor Cloud session still listed `coordinator` in `available_subagent_types` (sourced from `.claude/agents/coordinator.md`, which Cursor also reads). Docs say not to dispatch it. That is a leak of *visibility*, not of the documented working set.

### 3. CLAUDE.md / AGENTS.md encode coordinator behaviour

**PASS**

Required behaviours are present in both files (identical text):

| Behaviour | Where |
|---|---|
| Dispatch only; do not plan/implement/evaluate in main | L7, L177–182: “You do **not** plan, implement, or evaluate features yourself.” / “Never write code or plans yourself — delegate to the right role” |
| Pipeline plan → build → check → retry builder | L15, L69–162 |
| semiauto / auto | L46–67; default SEMIAUTO when `$HARNESS_MODE` unset |
| Circuit breaker at 3 | L15, L164: “After 3 build-check cycles for the same slug, STOP” |
| Pass user task verbatim to planner | L87–93: “Pass the user's task description exactly as they gave it.” |
| Resume same subagent on re-dispatch | L166–175: Claude Code `SendMessage`; Cursor `Task` + `resume` |
| Do not implement features in main session | L7, L179, L182 |

Softening (not a SPEC fail; see G2): “Work on your own” (L203–205) allows small file edits after asking in SEMIAUTO; “Exceptions” (L207–217) skip the pipeline for simple troubleshooting / doc updates.

### 4. `.cursor/agents/` mirrors with Cursor frontmatter

**PASS**

All three mirrors exist. Cursor frontmatter on each: `name`, `description`, `model: inherit`, `readonly`, `is_background: false`.

| File | Frontmatter / role |
|---|---|
| `.cursor/agents/planner.md` | `name: planner`, `readonly: false` |
| `.cursor/agents/builder.md` | `name: builder`, `readonly: false` |
| `.cursor/agents/checker.md` | `name: checker`, `readonly: false` |

Each states it is the Cursor-native mirror of the matching `.claude/agents/*` file and that Cursor prefers `.cursor/agents/` on name collision.

Claude counterparts gained a one-line pointer to the Cursor mirror (`git diff main...HEAD` +2 lines each). That is sync glue, not a behaviour change.

### 5. `.cursor/rules/abcd-coordinator.mdc` reinforces main = coordinator

**PASS**

File exists with `alwaysApply: true`:

> “You are the ABCD coordinator. The live spec is `AGENTS.md` (same role as `CLAUDE.md`).”
>
> “For non-trivial feature work, always delegate in order: `planner` → `builder` → `checker`. Do not implement the feature yourself. Pass the user's task to the planner verbatim. Resume the same subagent on re-dispatch when possible. Circuit breaker after 3 build-check cycles.”
>
> “Do not dispatch a `coordinator` subagent — the main session already is the coordinator.”

### 6. Thin coordinator aliases; start-coordinator.sh optional

**PASS**

| File | Role |
|---|---|
| `coordinator.md` (13 lines) | Pointer to `CLAUDE.md` / `AGENTS.md`; “no special entrypoint needed” |
| `.claude/agents/coordinator.md` (~15 lines) | “Compatibility alias only. Prefer opening the main session… Do not dispatch this subagent.” |
| `start-coordinator.sh` | Still launches `claude --agent coordinator` inside an optional tmux session; header calls it optional |

README L53–65 documents the launcher as “Optional: Claude Code launcher”.

### 7. `.artifacts/` contracts and abcd-* skills unchanged in substance

**PASS**

```
git diff main...HEAD -- .claude/skills/
```

is empty. Skills still present and used:

- `.claude/skills/abcd-planner/SKILL.md` → `.artifacts/plans/<slug>/`
- `.claude/skills/abcd-developer/SKILL.md` → `.artifacts/buildlog/`
- `.claude/skills/abcd-checker/SKILL.md` → `.artifacts/evaluations/`

`.artifacts/` itself is gitignored (`.gitignore` L7 and L10) and is not a committed tree on `main` either. Contract lives in the skills, not in tracked files. No skill content changed on this PR.

Pre-existing (not a regression): `abcd-developer` still describes `.artifacts/specs/feature-NNN-*.md` as its primary input, while the coordinator pipeline feeds `.artifacts/plans/<slug>/plan.md`. Unchanged vs `main`.

### 8. No dispatch.sh / poll.sh / tmux child model revived

**PASS**

- `scripts/` contains only `notify.sh`, `artifact-browser.js`, `agent-name.mjs`. No `dispatch.sh`, no `poll.sh`.
- Mentions of those names are prohibitions only (`CLAUDE.md` / `AGENTS.md` L17, L185; `coordinator.md` L12; `.claude/agents/coordinator.md` L15).
- `.claude/hooks/on-subagent-stop.sh` L3: “Replaces the old poll.sh completion ping.”
- `README.md` L129: “child work no longer opens extra panes or writes `sessions/*.done` sentinels.”
- `start-coordinator.sh` still uses tmux for the **coordinator session itself** (optional launcher). That is not a child-pane / poll-sentinel model.

### 9. Planner/checker Cursor mirrors writable; prompts forbid app source edits

**PASS**

Cursor `readonly: true` would block `.artifacts/` writes, so both stay writable and say so:

`.cursor/agents/planner.md` L23:

> “Cursor `readonly: true` blocks all file writes, including `.artifacts/`, so this agent stays writable. Do not edit application source.”

`.cursor/agents/checker.md` L24: same sentence.

Planner also: “Write only under `.artifacts/plans/<slug>/`” and “Do NOT implement anything”.
Checker also: “Do NOT modify any source code — read-only analysis and testing only” and “Write only the evaluation report to `.artifacts/evaluations/<slug>.yaml`”.

Builder is writable as specified (must edit app source when the plan says so).

---

## B. Behavioural smoke (coordinator discipline)

### Method

This cloud session acted as the **main-session coordinator** (AUTO for this exercise: the verification request already asked for plan → build → check). `$HARNESS_MODE` was unset (would default SEMIAUTO); the user had already authorized the full pipeline, so checkpoints were not re-asked.

**Coordinator did not edit application / harness source.** Delegation used Cursor `Task` with `subagent_type` `planner` | `builder` | `checker` — the path `AGENTS.md` L36–42 specifies:

> “Cursor | **Task** | `subagent_type`: role name | **Task** with `resume` set to the recorded agent id”

Subagent tool **was available**. This was not a role-simulation fallback.

Toy task passed **verbatim** to planner (plus the required save path, per `AGENTS.md` L87–91):

```
Create a VERIFY.md stub file under .artifacts/ only. Save plan to .artifacts/plans/cursor-port-smoke/plan.md
```

### Dispatches (ids recorded for resume)

| Role | First dispatch | Agent id |
|---|---|---|
| planner | `Task` `subagent_type=planner` | `bc-cae8f3bf-39ee-5a2e-8839-1b639ea700dc` |
| builder | `Task` `subagent_type=builder` | `bc-d0b31a73-164d-5315-a494-549ef87a050d` |
| checker | `Task` `subagent_type=checker` | `bc-316ffbed-626a-5eb3-84a2-0fc4ae15e1ae` |

No re-dispatch was needed (checker passed). Resume path was not exercised this run; the wiring (`Task` + `resume`) is specified in `AGENTS.md` L41–42 and L166–175.

### Artifacts produced

| Stage | Path | Result |
|---|---|---|
| Plan | `.artifacts/plans/cursor-port-smoke/plan.md` | Written by planner. Two phases; fences builder away from `src/`, `.gitignore`, and force-add. |
| Build | `.artifacts/VERIFY.md` + `.artifacts/buildlog/cursor-port-smoke.yaml` | Stub only. `commitHash`/`commitMessage` null (gitignore). No tracked-file change. |
| Check | `.artifacts/evaluations/cursor-port-smoke.yaml` | **pass**, 58/60, no criterion &lt; 7. |

Checker scorecard (smoke): spec 10, functional 9, quality 9, security 10, performance 10, build-log 10.

### Coordinator discipline checks

| Check | Result |
|---|---|
| Main session did not write the plan / stub / smoke eval | Pass — those files came from the three subagents |
| Main session did not edit `src/`, `.cursor/`, `.claude/`, or other harness source for the smoke | Pass |
| User task passed verbatim (no architecture added by coordinator) | Pass |
| Sequential foreground pipeline | Pass |
| Circuit breaker N/A (1 cycle, pass) | n/a |

Limitation: this is a Cloud Agent parent, not a Cursor IDE chat. `AGENTS.md` / the always-apply rule were followed here, but IDE “open repo → main chat is coordinator” was inferred from files, not clicked in the desktop app.

---

## C. Verdict, gaps, recommended PR fixes

**Verdict: `MEETS_WITH_GAPS`**

The nine SPEC items pass. The PR is the intended Cursor/Claude twin of “main session = coordinator; only planner/builder/checker work.” Gaps below are residual leaks or prompt friction, not a failed port.

### Gaps

**G1 — `coordinator` is still a Cursor-visible subagent.**
`.claude/agents/coordinator.md` remains a Claude alias (required by SPEC 6). Cursor also reads `.claude/agents/`, and this session listed `coordinator` as a `subagent_type`. Docs and `.cursor/rules/abcd-coordinator.mdc` say not to dispatch it, but a parent *can*. There is no `.cursor/agents/coordinator.md` to override the Claude file.

**G2 — Main session may still edit / skip the pipeline.**
`CLAUDE.md` / `AGENTS.md` “Work on your own” (L203–205) and “Exceptions” (L207–217) allow small edits and skip plan → build → check for “simple document update”. That is reasonable, but it weakens “never write code or plans yourself” if read loosely.

**G3 — Builder prompt example hardcodes `src/`.**
`AGENTS.md` L113: “Write code to src/”. The smoke planner had to override the builder default (`.cursor/agents/builder.md` L22: “Write application code under `src/` unless the plan specifies otherwise”). Easy to over-build on artifacts-only tasks.

**G4 — Resume-on-re-dispatch not exercised.**
Specified correctly; this smoke passed on cycle 1. No failed-check → resume-builder loop was run.

**G5 — Context only, not a PR regression.**
`.artifacts/` is gitignored, so pipeline outputs are invisible unless force-added. `abcd-developer` still talks about `.artifacts/specs/feature-NNN`. Both pre-exist on `main`.

### Recommended fixes (specific)

1. **G1** — Add `.cursor/agents/coordinator.md` as a Cursor override: same “compatibility alias / do not dispatch / do not implement” body as `.claude/agents/coordinator.md`, plus `is_background: false`. Cursor prefers `.cursor/agents/` on collision, so this makes the Cursor-facing description unambiguously “not a working subagent.” Optionally add one line to `.cursor/rules/abcd-coordinator.mdc`: “Never set `subagent_type` to `coordinator`.”

2. **G2** — In `CLAUDE.md` and `AGENTS.md` (keep them twins), narrow “Work on your own” to: harness-admin / git / notify only; still no feature code, no plans, no evaluations. Keep Exceptions, but say they do not apply to anything that would land under `src/`.

3. **G3** — Change the builder prompt example in both twins from `Write code to src/` to `Follow the plan's output paths (application code only if the plan says so). Write build log to .artifacts/buildlog/<slug>.yaml.`

4. **G4** (optional) — One sentence in README “How to try it”: after a failed check, the parent must `Task` with `resume` set to the recorded builder id, not spawn a new builder.

Do **not** revive `dispatch.sh` / `poll.sh`. Do **not** fold coordinator logic back into a required `--agent coordinator` happy path.

---

## Appendix: files read

`CLAUDE.md`, `AGENTS.md`, `README.md`, `coordinator.md`, `start-coordinator.sh`, `roles/README.md`, `roles/{planner,builder,checker}.md`, `.claude/agents/{planner,builder,checker,coordinator}.md`, `.cursor/agents/{planner,builder,checker}.md`, `.cursor/rules/abcd-coordinator.mdc`, `.claude/skills/abcd-{planner,developer,checker}/SKILL.md`, `.claude/hooks/on-subagent-stop.sh`, `cleanup.sh`, `.gitignore`, `scripts/` listing.

PR diff vs `main`: 17 files, +609 / −242. Skills untouched.
