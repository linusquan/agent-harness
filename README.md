# ABCD Agent Harness

**A**rchitect. **B**uild. **C**heck. **D**eploy.

A multi-agent orchestration harness for Claude Code or Codex. A central coordinator dispatches specialised agent sessions via tmux, then loops until the feature passes evaluation.

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

## Prerequisites

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) or `codex`
- [tmux](https://github.com/tmux/tmux)
- Node.js (for agent name generation)

```bash
npm install
```

## Quick Start

```bash
# Start the coordinator (default: sonnet, semiauto mode, Claude backend)
./start-coordinator.sh

# Or customise
./start-coordinator.sh --mode auto              # no approval checkpoints
./start-coordinator.sh --model opus              # use opus for coordinator
./start-coordinator.sh --mode auto --model opus  # both
./start-coordinator.sh --agentbase codex         # use Codex instead of Claude
```

Once inside the coordinator session, give it a task:

```
add an Express hello world server to src/
```

The coordinator will:
1. Dispatch a **planner** (split pane) to produce a plan
2. Wait for completion, review the plan
3. Dispatch a **builder** to implement it
4. Dispatch a **checker** to evaluate the build (scored 1-10 per criterion)
5. If evaluation fails, loop back to builder with feedback
6. Report when done

## Operating Modes

| Mode | Behaviour |
|---|---|
| `semiauto` (default) | Stops at each phase for user approval |
| `auto` | Runs full pipeline, stops only on errors or circuit breaker |

Switch modes mid-session by typing `auto` or `semiauto`.

## Scripts

### `dispatch.sh`

Spawn a child agent session.

```bash
./scripts/dispatch.sh <role> <complexity> <prompt> [--task-id <id>]
```

- `complexity`: `simple` (haiku), `mid` (sonnet), `complex` (opus)
- `--task-id`: reuse an existing task ID (for re-dispatch after failed check)
- Auto-generates a friendly name (e.g. `planner-kristen`, `builder-destiny`)
- Backend comes from `HARNESS_AGENTBASE` set by `start-coordinator.sh`
- For `codex`, completion signaling uses the repo-local `Stop` hook in `.codex/hooks.json`
- For `codex`, child panes are interactive sessions; `poll.sh` closes the pane after the `Stop` hook writes the sentinel

### `poll.sh`

Block until a child session completes.

```bash
./scripts/poll.sh <task-id> [timeout_seconds]
```

- Default timeout: 600s (10 min)
- Returns sentinel JSON on completion
- Auto-closes the child tmux pane after 3 seconds

### `cleanup.sh`

Wipe runtime state for a fresh test.

```bash
./cleanup.sh
```
