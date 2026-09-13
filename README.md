# ABCD Agent Harness

**A**rchitect. **B**uild. **C**heck. **D**eploy.

A multi-agent orchestration harness for **Claude Code** and **Cursor**. Open the repo — the main session is the coordinator. It delegates to official project subagents, then loops until the feature passes evaluation.

```
                 ┌──────────────┐
                 │  A: Architect│
                 └──────┬───────┘
                        │
  ┌─────────┐   ┌──────┴───────┐
  │  Human  │───│ Coordinator  │
  └─────────┘   └──┬───────┬───┘
                   │       │
            ┌──────┴──┐ ┌──┴──────┐
            │C: Check │ │B: Build │
            └─────────┘ └─────────┘
                    D: Deploy (planned)
```

| Phase | Role | What it does |
|---|---|---|
| **A** — Architect | planner | Analyses codebase, produces structured implementation plan |
| **B** — Build | builder | Implements the plan, writes code and build log |
| **C** — Check | checker | Evaluates build against plan, scores 6 criteria (>= 7/10 to pass) |
| **D** — Deploy | deployer | Ships the verified build to target environment *(planned)* |

## Quick Start

Open this repository in **Cursor Agent** or **Claude Code**. The main chat is already the coordinator:

- Cursor loads [`AGENTS.md`](AGENTS.md) (and [`.cursor/rules/abcd-coordinator.mdc`](.cursor/rules/abcd-coordinator.mdc))
- Claude Code loads [`CLAUDE.md`](CLAUDE.md)

Those two files define the **same role** and must stay in sync. Give the main session a task:

```
add an Express hello world server to src/
```

The coordinator will:

1. Delegate to the **planner** subagent to produce a plan
2. Wait for completion, review the plan
3. Delegate to the **builder** to implement it
4. Delegate to the **checker** to evaluate the build (scored 1-10 per criterion)
5. If evaluation fails, resume the builder with feedback
6. Report when done

No special entrypoint is required for the happy path.

### Optional: Claude Code launcher

```bash
# Start a tmux-backed Claude Code session (default: sonnet, semiauto mode)
./start-coordinator.sh

# Or customise
./start-coordinator.sh --mode auto              # no approval checkpoints
./start-coordinator.sh --model opus              # use opus for coordinator
./start-coordinator.sh --mode auto --model opus  # both
```

`start-coordinator.sh` still launches `claude --agent coordinator` for people who want that entrypoint. [`.claude/agents/coordinator.md`](.claude/agents/coordinator.md) is a thin alias that points at `CLAUDE.md` / `AGENTS.md`. Prefer opening the project.

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) and/or [Cursor](https://cursor.com)
- [tmux](https://github.com/tmux/tmux) (only if you use `./start-coordinator.sh`)
- Node.js (for coordinator session names and the artifact browser, if you use the launcher)

```bash
npm install
```

## Official subagents

Only **planner**, **builder**, and **checker** are working subagents. The main session is the coordinator and must not implement features itself.

Claude Code reads [`.claude/agents/`](.claude/agents/). Cursor also reads that directory, and prefers [`.cursor/agents/`](.cursor/agents/) when names collide. The Cursor files are thin mirrors — keep them in sync with the Claude agents.

Matching skills under `.claude/skills/` are unchanged (`abcd-planner`, `abcd-developer`, `abcd-checker`).

| Agent | Claude file | Cursor mirror | Preloaded skill | Writes |
|---|---|---|---|---|
| *(main session)* | `CLAUDE.md` | `AGENTS.md` | — | nothing (orchestrates only) |
| planner | `.claude/agents/planner.md` | `.cursor/agents/planner.md` | `abcd-planner` | `.artifacts/plans/<slug>/plan.md` |
| builder | `.claude/agents/builder.md` | `.cursor/agents/builder.md` | `abcd-developer` | code under `src/`, `.artifacts/buildlog/<slug>.yaml` |
| checker | `.claude/agents/checker.md` | `.cursor/agents/checker.md` | `abcd-checker` | `.artifacts/evaluations/<slug>.yaml` |

Re-dispatch of the same role for the same slug **resumes** the existing subagent so it keeps context (Claude Code: SendMessage; Cursor: Task `resume`).

You can still run a Claude role directly, for example `claude --agent planner`.

## Operating Modes

| Mode | Behaviour |
|---|---|
| `semiauto` (default) | Stops at each phase for user approval |
| `auto` | Runs full pipeline, stops only on errors or circuit breaker |

Switch modes mid-session by typing `auto` or `semiauto`.

If you use `start-coordinator.sh`, `$HARNESS_MODE` is set by the launcher. Otherwise the coordinator defaults to semiauto. Checkpoints and circuit-breaker pauses call `./scripts/notify.sh`. Completions are notified by the `SubagentStop` hook.

## Circuit breaker

After 3 build → check cycles for the same slug, the coordinator stops and asks you what to do, in both auto and semiauto.

## Scripts

### `notify.sh`

Send a push notification (ntfy).

```bash
./scripts/notify.sh <role> <message> [title]
```

### `cleanup.sh`

Wipe runtime state for a fresh test.

```bash
./cleanup.sh
```

The optional coordinator tmux session is only a launcher — child work no longer opens extra panes or writes `sessions/*.done` sentinels.
