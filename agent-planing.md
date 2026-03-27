# Building a reusable multi-agent coding harness with Claude Code

**A three-agent loop — planner, generator, evaluator — dramatically outperforms solo agent coding.** Anthropic's own engineering team published this exact architecture in March 2026, showing that while a single agent produced broken features in 20 minutes ($9), the full harness delivered a working, feature-rich application in 6 hours ($200). The key insight: separating creation from evaluation, inspired by GANs, prevents the self-congratulatory hallucination that plagues single-agent systems. This guide covers every layer of configuration, orchestration, and team packaging needed to build and share this harness using Claude Code's CLI, Agent SDK, and MCP ecosystem.

## Claude Code's headless mode and the Agent SDK power the automation layer

Claude Code's non-interactive mode uses the `-p` / `--print` flag (colloquially called "headless mode" — there is no separate `--headless` flag). It sends a prompt, executes, streams the result to stdout, and exits. Combined with `--output-format json`, it becomes a scriptable building block for multi-agent pipelines.

**Critical flags for agentic operation:**

| Flag | Purpose |
|------|---------|
| `-p` / `--print` | Non-interactive mode: send prompt, get response, exit |
| `--bare` | Skip hooks, MCP auto-discovery, CLAUDE.md — fastest for scripting |
| `--output-format json` | Return structured JSON with `result`, `session_id`, `cost` fields |
| `--max-turns N` | Cap agentic turns to prevent runaway loops |
| `--allowedTools "Read,Write,Bash(git *)"` | Pre-approve tools without interactive prompts |
| `--system-prompt "..."` | Replace the entire system prompt |
| `--append-system-prompt "..."` | Add to the default system prompt (preserves built-in capabilities) |
| `--dangerously-skip-permissions` | Skip ALL permission prompts (sandboxed environments only) |
| `--json-schema '{...}'` | Enforce structured JSON output conforming to a schema |
| `--continue` / `-c` | Continue the most recent conversation in the current directory |
| `--resume SESSION_ID` | Resume a specific session by ID |

For most agent harness work, **use `--append-system-prompt`** rather than `--system-prompt` — it preserves Claude Code's built-in tool capabilities while injecting your agent persona. The `--bare` flag is recommended for scripted/SDK calls because it skips auto-discovery overhead and will become the default for `-p` in a future release.

**The Claude Agent SDK** (`@anthropic-ai/claude-agent-sdk` for TypeScript, `claude-agent-sdk` for Python) exposes the same harness powering Claude Code as a programmable library. It was renamed from `@anthropic-ai/claude-code` — migration requires only an import rename. The SDK's `query()` function is an async generator that streams messages as Claude works, supports subagent definitions, custom MCP tools, structured outputs, and session management. Unlike the CLI, the SDK does **not** auto-load CLAUDE.md — you must explicitly set `settingSources: ['project']`.

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Implement the auth module per spec.md",
  options: {
    model: "opus",
    allowedTools: ["Read", "Write", "Edit", "Bash", "Glob", "Agent"],
    maxTurns: 50,
    permissionMode: "acceptEdits",
    settingSources: ["project"],  // required to load CLAUDE.md
  }
})) {
  if (message.type === "result") {
    console.log(`Done: ${message.result}`);
    console.log(`Session: ${message.session_id}`);
  }
}
```

## The planner agent expands a brief into a full product spec

Anthropic's engineering blog reveals the planner's core design principle: **stay at the product level, not the technical level**. If the planner specifies granular technical details and gets something wrong, errors cascade into downstream implementation. The planner should be ambitious about scope and produce a structured spec that the generator can work through incrementally.

A planner agent is configured either via `--append-system-prompt` on the CLI or as a custom agent definition in `.claude/agents/planner.md`:

```markdown
# .claude/agents/planner.md
---
name: planner
description: Expands brief prompts into detailed product specifications
model: opus
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - WebSearch
  - WebFetch
---

You are a product planner. When given a brief description:

1. Research the domain to understand best practices and prior art
2. Expand the brief into a comprehensive product specification
3. Define 8-16 features organized into prioritized implementation sprints
4. Stay at the product/UX level — do NOT specify implementation details
5. For each feature, describe the user experience and acceptance criteria
6. Write the complete spec to spec.md

Output structure:
- Product Overview (what and why)
- Target Users
- Feature List (prioritized, with sprint assignments)
- Design Language (visual direction, not CSS)
- Success Criteria (what "done" looks like for each feature)
```

In shell orchestration, the planner runs as a standalone headless invocation:

```bash
claude -p "You are a product planner. Take this brief and expand it into a
detailed product specification. Be ambitious about scope. Focus on product
context and high-level design, NOT granular technical details. Write the
spec to .artifacts/spec.md.

Brief: $USER_BRIEF" \
  --allowedTools "Read,Write,Bash,WebSearch,WebFetch" \
  --max-turns 20 \
  --output-format json \
  --dangerously-skip-permissions > .artifacts/planner-output.json
```

The planner's output — `spec.md` — becomes the **sole input** to the generator phase, establishing a clean contract between agents.

## Playwright MCP gives the evaluator real browser testing capabilities

The Playwright MCP server (`@playwright/mcp`) from Microsoft is the evaluator's primary tool. It exposes **34+ browser automation tools** through the Model Context Protocol, letting Claude navigate pages, click elements, fill forms, take screenshots, and check accessibility — all by referencing structured accessibility snapshots rather than raw pixels.

**Installation is a single command:**

```bash
claude mcp add playwright npx @playwright/mcp@latest
```

For team sharing, add it to `.mcp.json` at the project root (version-controlled):

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--headless", "--browser", "chromium"]
    }
  }
}
```

The key tools the evaluator uses are `browser_navigate` to open the running app, **`browser_snapshot`** to read the page structure as an accessibility tree (far cheaper than screenshots at ~120 tokens vs ~1,500), `browser_click` and `browser_type` for interaction, `browser_console_messages` to check for errors, and `browser_network_requests` to verify API calls. Enable `--caps=testing` in the MCP args to unlock assertion tools like `browser_verify_element_visible` and `browser_verify_text_visible`.

**Important gotcha**: explicitly say "Use Playwright MCP" in your evaluator prompt, otherwise Claude may try to run Playwright via the Bash tool instead of using the MCP tools.

The evaluator agent definition wires these tools to a grading rubric:

```markdown
# .claude/agents/evaluator.md
---
name: evaluator
description: QA evaluator that tests running applications against specs
model: opus
allowed-tools:
  - Read
  - Bash
  - mcp__playwright__*
---

You are a QA evaluator. For each sprint:

1. Read the spec at .artifacts/spec.md and the sprint contract
2. Start the application if not running (npm run dev)
3. Use Playwright MCP to navigate to the app and test each feature
4. Grade against four criteria (1-10 scale):
   - Product depth: Does the feature match the spec's intent?
   - Functionality: Does it work without errors?
   - Visual design: Is the UI polished and consistent?
   - Code quality: Are there console errors or broken network requests?
5. If ANY criterion falls below 6, the sprint FAILS
6. Write detailed feedback to .artifacts/feedback.md with specific issues
7. End with a clear PASS or FAIL verdict
```

## Context resets with file-based handoffs keep each agent focused

Anthropic's harness research found that **context resets outperform context compaction**. When agents accumulate a long conversation history, they exhibit "context anxiety" — rushing to wrap up or losing coherence. The solution: each agent phase starts as a **fresh `claude -p` session** and receives only the structured artifacts it needs.

The handoff mechanism uses **files on disk** as the communication channel:

```
.artifacts/
├── spec.md              # Planner → Generator (product specification)
├── sprint-contract-N.md # Generator ↔ Evaluator (what "done" means)
├── feedback-N.md        # Evaluator → Generator (what failed and why)
├── build-summary.md     # Generator → Evaluator (what was built)
└── final-report.md      # Evaluator output (all sprints graded)
```

The `--continue` flag resumes the most recent conversation with full context — useful for iterating within a single agent phase but **not recommended** for cross-agent handoffs. For the planner→generator→evaluator pipeline, each phase should be a **new session** that reads only its input files. Session IDs can be extracted from JSON output for programmatic tracking:

```bash
session_id=$(claude -p "Start review" --output-format json | jq -r '.session_id')
# Later, within the same agent phase:
claude -p "Continue review" --resume "$session_id"
```

For more structured handoff, the Agent SDK supports **structured outputs** that guarantee JSON schema conformance — pipe the planner's structured spec directly into the generator:

```typescript
const planSchema = {
  type: "object",
  properties: {
    features: { type: "array", items: { type: "object", properties: {
      name: { type: "string" },
      sprint: { type: "number" },
      acceptance_criteria: { type: "array", items: { type: "string" } }
    }}},
    design_language: { type: "string" }
  }
};

let spec;
for await (const msg of query({
  prompt: `Expand this brief into a product spec: ${userBrief}`,
  options: { outputFormat: { type: "json_schema", schema: planSchema } }
})) {
  if (msg.type === "result") spec = msg.structured_output;
}

// Generator receives structured spec
for await (const msg of query({
  prompt: `Implement sprint 1 of this spec:\n${JSON.stringify(spec)}`,
  options: { allowedTools: ["Read", "Write", "Edit", "Bash"], permissionMode: "acceptEdits" }
})) { /* ... */ }
```

## Packaging for team reuse requires four committed artifacts

Claude Code's settings hierarchy is designed for team sharing. **Four files** committed to version control give every team member the same harness:

**1. `CLAUDE.md`** (project root) — team-wide coding standards and architecture context. Keep it under **200 lines** — research shows frontier models reliably follow ~150-200 instructions, and Claude Code's system prompt already consumes ~50 slots. Use progressive disclosure: brief descriptions in CLAUDE.md that reference detailed docs in separate files.

**2. `.claude/settings.json`** — team permissions, hooks, and environment:

```json
{
  "permissions": {
    "allow": ["Read", "Write", "Edit", "Bash(npm run *)", "Bash(git *)",
              "mcp__playwright__*"],
    "deny": ["Read(.env)", "Read(.env.*)", "Bash(rm -rf *)"]
  },
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write",
      "hooks": [{ "type": "command", "command": "npx prettier --write \"$CLAUDE_FILE_PATH\"" }]
    }]
  },
  "env": { "BASH_DEFAULT_TIMEOUT_MS": "60000" }
}
```

**3. `.mcp.json`** (project root) — shared MCP server definitions. When teammates clone the repo, they're prompted to approve servers once:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@0.0.64", "--headless", "--browser", "chromium"]
    }
  }
}
```

**4. `.claude/agents/`** — team agent definitions as markdown files with YAML frontmatter. Each file defines an agent persona: `planner.md`, `generator.md`, `evaluator.md`.

Personal overrides go in `.claude/settings.local.json` (auto-gitignored) and `CLAUDE.local.md`. The merge strategy: **array fields concatenate** across scopes (so team deny rules combine with personal deny rules), while scalar fields use the higher-priority scope.

Claude Code does **not** natively orchestrate a multi-agent pipeline — it supports subagents within a session and experimental Agent Teams, but the planner→generator→evaluator loop requires either shell scripts or Agent SDK code to drive the sequential phases.

## A complete working setup brings all the pieces together

Here is the full directory structure and orchestration code for a reusable three-agent harness:

```
my-project/
├── CLAUDE.md                         # Team coding standards (committed)
├── .mcp.json                         # Playwright MCP config (committed)
├── .claude/
│   ├── settings.json                 # Team permissions and hooks (committed)
│   ├── agents/
│   │   ├── planner.md                # Planner agent persona
│   │   ├── generator.md              # Generator agent persona
│   │   └── evaluator.md              # Evaluator agent persona
│   └── commands/
│       └── build-app.md              # Slash command to kick off the harness
├── harness/
│   ├── orchestrate.sh                # Shell-based orchestration script
│   └── orchestrate.ts                # SDK-based orchestration script
├── .artifacts/                       # Handoff artifacts (gitignored)
│   ├── spec.md
│   ├── sprint-contract-*.md
│   ├── feedback-*.md
│   └── build-summary.md
└── src/                              # Generated application code
```

**Shell orchestration (`harness/orchestrate.sh`):**

```bash
#!/bin/bash
set -euo pipefail

BRIEF="$1"
ARTIFACTS=".artifacts"
MAX_RETRIES=3
mkdir -p "$ARTIFACTS"

echo "═══ PHASE 1: PLANNING ═══"
claude -p "$(cat .claude/agents/planner.md | tail -n +10)

Brief: $BRIEF" \
  --append-system-prompt "Write the spec to $ARTIFACTS/spec.md" \
  --allowedTools "Read,Write,Glob,WebSearch,WebFetch" \
  --max-turns 25 \
  --dangerously-skip-permissions \
  --output-format json > "$ARTIFACTS/planner-result.json"

SPRINTS=$(jq -r '.result' "$ARTIFACTS/planner-result.json" | grep -c "Sprint" || echo "5")
echo "Planned $SPRINTS sprints"

for sprint in $(seq 1 "$SPRINTS"); do
  echo "═══ PHASE 2: GENERATING SPRINT $sprint ═══"
  retry=0
  while [ $retry -lt $MAX_RETRIES ]; do
    claude -p "Read $ARTIFACTS/spec.md. Implement Sprint $sprint.
    $([ -f "$ARTIFACTS/feedback-$sprint.md" ] && echo "Previous feedback: $(cat $ARTIFACTS/feedback-$sprint.md)")
    After implementing, write a summary to $ARTIFACTS/build-summary-$sprint.md.
    Commit changes with a descriptive message." \
      --allowedTools "Read,Write,Edit,Bash,Glob,Grep" \
      --max-turns 50 \
      --dangerously-skip-permissions \
      --output-format json > "$ARTIFACTS/gen-$sprint-$retry.json"

    echo "═══ PHASE 3: EVALUATING SPRINT $sprint ═══"
    EVAL=$(claude -p "Read $ARTIFACTS/spec.md and $ARTIFACTS/build-summary-$sprint.md.
    Start the app with 'npm run dev' and use Playwright MCP to test Sprint $sprint features.
    Grade on: functionality, design, completeness, code quality (1-10 each).
    If any score < 6, write feedback to $ARTIFACTS/feedback-$sprint.md and say FAIL.
    If all pass, say PASS." \
      --allowedTools "Read,Bash,Grep,mcp__playwright__*" \
      --max-turns 30 \
      --dangerously-skip-permissions \
      --output-format json)

    if echo "$EVAL" | jq -r '.result' | grep -q "PASS"; then
      echo "✅ Sprint $sprint PASSED"
      break
    else
      retry=$((retry + 1))
      echo "❌ Sprint $sprint FAILED (attempt $retry/$MAX_RETRIES)"
    fi
  done
done
echo "═══ HARNESS COMPLETE ═══"
```

**SDK orchestration (`harness/orchestrate.ts`):**

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";
import { readFileSync, writeFileSync, existsSync } from "fs";

async function runAgent(prompt: string, tools: string[], maxTurns = 30) {
  let result = "";
  let sessionId = "";
  for await (const msg of query({
    prompt,
    options: {
      model: "opus",
      allowedTools: tools,
      maxTurns,
      permissionMode: "acceptEdits",
      settingSources: ["project"],
    },
  })) {
    if (msg.type === "result" && msg.subtype === "success") {
      result = msg.result;
      sessionId = msg.session_id;
    }
  }
  return { result, sessionId };
}

async function main() {
  const brief = process.argv[2];

  // Phase 1: Plan
  console.log("═══ PLANNING ═══");
  await runAgent(
    `You are a product planner. Expand this brief into a full spec.
     Be ambitious. Stay at product level, not technical details.
     Write to .artifacts/spec.md.\n\nBrief: ${brief}`,
    ["Read", "Write", "Glob", "WebSearch", "WebFetch"],
    25
  );

  const spec = readFileSync(".artifacts/spec.md", "utf-8");
  const sprintCount = (spec.match(/Sprint \d+/g) || []).length || 5;

  for (let sprint = 1; sprint <= sprintCount; sprint++) {
    for (let attempt = 0; attempt < 3; attempt++) {
      // Phase 2: Generate
      console.log(`═══ GENERATING SPRINT ${sprint} (attempt ${attempt + 1}) ═══`);
      const feedback = existsSync(`.artifacts/feedback-${sprint}.md`)
        ? readFileSync(`.artifacts/feedback-${sprint}.md`, "utf-8") : "";

      await runAgent(
        `Read .artifacts/spec.md. Implement Sprint ${sprint}.
         ${feedback ? `Fix these issues from QA:\n${feedback}` : ""}
         Write summary to .artifacts/build-summary-${sprint}.md. Commit changes.`,
        ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
        50
      );

      // Phase 3: Evaluate
      console.log(`═══ EVALUATING SPRINT ${sprint} ═══`);
      const { result } = await runAgent(
        `Read .artifacts/spec.md and .artifacts/build-summary-${sprint}.md.
         Start the app (npm run dev). Use Playwright MCP to test Sprint ${sprint}.
         Grade: functionality, design, completeness, code quality (1-10 each).
         Threshold: all must be >= 6. Write feedback to .artifacts/feedback-${sprint}.md.
         End with PASS or FAIL.`,
        ["Read", "Bash", "Grep", "mcp__playwright__browser_navigate",
         "mcp__playwright__browser_snapshot", "mcp__playwright__browser_click",
         "mcp__playwright__browser_type", "mcp__playwright__browser_console_messages"],
        30
      );

      if (result.includes("PASS")) {
        console.log(`✅ Sprint ${sprint} passed`);
        break;
      }
      console.log(`❌ Sprint ${sprint} failed, retrying...`);
    }
  }
}
main();
```

## Conclusion

The planner→generator→evaluator pattern works because it mirrors how effective human teams operate: one person defines the vision, another builds it, and a third tests it ruthlessly. **Three architectural decisions matter most**: fresh context windows per agent phase (not `--continue`), file-based handoffs as the sole communication channel, and a skeptical evaluator with real browser access via Playwright MCP.

The Agent SDK (`@anthropic-ai/claude-agent-sdk`) provides the cleanest programmatic path, with `query()` calls piped sequentially and structured JSON schemas ensuring type-safe handoffs. For teams that prefer shell scripts, `claude -p` with `--output-format json` and `--dangerously-skip-permissions` delivers the same pipeline with less code. Either way, the four committed artifacts — `CLAUDE.md`, `.claude/settings.json`, `.mcp.json`, and `.claude/agents/*.md` — ensure every team member runs the identical harness from day one.

Anthropic's own data shows that model improvements may simplify the harness over time (Opus 4.6 eliminated the need for sprint decomposition), but the separated evaluator consistently adds value regardless of model capability. The self-praise problem — agents rating their own work as excellent when it clearly isn't — appears to be a fundamental property of current LLMs, making the independent evaluator the single most important component of the architecture.