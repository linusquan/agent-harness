# SCGC Codex workspace

- This repository is the ABCD agent harness. The application monorepo is `src/`, which has its own Git repository and its own `AGENTS.md`. Read `src/AGENTS.md` when working on application code.
- For a coordinated feature workflow, use `$abcd-coordinator` or `./start-codex-coordinator.sh`. Its planner, builder, and checker profiles live in `.codex/agents/`; their skills live in `.agents/skills/`.
- Store Codex ABCD plans, build logs, and evaluations in the [Engineering Work Artifacts Notion page](https://app.notion.com/p/Engineering-Work-Artifacts-3e63381a46dd8009a5c4f439abd54345). Create one child page per feature slug with Plan, Build Log, and Evaluation sections. Pass that page's URL between agents. Do not create new Codex ABCD artifacts under `src/.artifacts/`.
- Keep the Claude harness in `.claude/` intact. Change Codex files independently unless the user asks to synchronize both.
