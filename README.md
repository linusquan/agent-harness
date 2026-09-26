# ABCD Agent Harness

**A**rchitect. **B**uild. **C**heck. **D**eploy.

A multi-agent orchestration harness for Claude Code. A central coordinator session delegates to official project subagents via the Agent tool, then loops until the feature passes evaluation.

The repository also includes a Codex version of the same workflow. Start it with `./start-codex-coordinator.sh` (or `./start-codex-coordinator.sh --mode auto`). The Claude launcher and `.claude/` files remain available.

## Codex setup

- Install the [Codex CLI](https://learn.chatgpt.com/docs/developer-commands), then run `./start-codex-coordinator.sh` from this repository. The launcher starts Codex with `--sandbox workspace-write --ask-for-approval never`; the project config and agent profiles use the same settings. Add `--model <model>` or other Codex CLI flags as needed.
- The launcher invokes `$abcd-coordinator` in an interactive Codex session. `--mode semiauto` is the default; `--mode auto` runs the full plan → build → check loop without phase checkpoints. You can switch by saying `auto` or `semiauto` during the chat.
- Project agent profiles are in [`.codex/agents/`](.codex/agents/), and the four workflow skills are in [`.agents/skills/`](.agents/skills/). The Playwright MCP server and subagent settings are in [`.codex/config.toml`](.codex/config.toml).
- Project hooks are in [`.codex/hooks.json`](.codex/hooks.json). Codex requires you to review and trust new or changed hooks with `/hooks` before they run. The stack guard watches edits to `src/docker-stack.yml` on `main` and `main-v2`; the completion hook sends the same `ntfy` messages as the Claude harness.
- The Codex launcher requests one child page per feature under [Engineering Work Artifacts](https://app.notion.com/p/Engineering-Work-Artifacts-3e63381a46dd8009a5c4f439abd54345) for the plan, build log, and evaluation. The Claude workflow stores them in `.artifacts/` at the harness root (not under `src/`). For Codex CLI, connect the configured Notion MCP server with `codex mcp login notion` before running the workflow. The nested `src/` repository has its own [instructions](src/AGENTS.md).

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

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)
- [tmux](https://github.com/tmux/tmux) (keeps the coordinator session alive)
- Node.js (for coordinator session names and the artifact browser)

```bash
npm install
```

## Quick Start

```bash
# Start the coordinator (default: sonnet, semiauto mode)
./start-coordinator.sh

# Or customise
./start-coordinator.sh --mode auto              # no approval checkpoints
./start-coordinator.sh --model opus              # use opus for coordinator
./start-coordinator.sh --mode auto --model opus  # both
```

`start-coordinator.sh` launches Claude Code as `claude --agent coordinator`. The live definition is [`.claude/agents/coordinator.md`](.claude/agents/coordinator.md).

Once inside the coordinator session, give it a task:

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

## Official subagents

Project agents live in [`.claude/agents/`](.claude/agents/). Matching skills under `.claude/skills/` are preloaded via the `skills` frontmatter field.

| Agent | File | Preloaded skill | Writes |
|---|---|---|---|
| coordinator | `.claude/agents/coordinator.md` | — | nothing (orchestrates only) |
| planner | `.claude/agents/planner.md` | `abcd-planner` | `.artifacts/plans/<slug>/plan.md` |
| builder | `.claude/agents/builder.md` | `abcd-developer` | code under `src/`, `.artifacts/buildlog/<slug>.yaml` |
| checker | `.claude/agents/checker.md` | `abcd-checker` | `.artifacts/evaluations/<slug>.yaml` |

Re-dispatch of the same role for the same slug **resumes** the existing subagent (SendMessage) so it keeps context.

You can also run a role directly, for example `claude --agent planner`.

## Operating Modes

| Mode | Behaviour |
|---|---|
| `semiauto` (default) | Stops at each phase for user approval |
| `auto` | Runs full pipeline, stops only on errors or circuit breaker |

Switch modes mid-session by typing `auto` or `semiauto`.

`$HARNESS_MODE` is set by `start-coordinator.sh`. Checkpoints and circuit-breaker pauses call `./scripts/notify.sh`. Completions are notified by the `SubagentStop` hook.

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

The coordinator tmux session is only a launcher — child work no longer opens extra panes or writes `sessions/*.done` sentinels.
