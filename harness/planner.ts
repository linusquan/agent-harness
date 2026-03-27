/**
 * Planner agent — TypeScript Claude Agent SDK implementation.
 *
 * Expands a brief product description into a full spec using the planner agent
 * defined in .claude/agents/planner.md. Optionally injects domain skills from
 * .claude/skills/ into the system prompt before running.
 *
 * IMPORTANT: Always run from the repo root so settingSources: ["project"] can
 * locate CLAUDE.md and .claude/settings.json correctly:
 *
 *   cd /path/to/SCGC
 *   npx tsx harness/planner.ts "<brief>" [--skills skill1,skill2]
 *
 * Arguments:
 *   <brief>              Required. Plain-text description of what to build.
 *   --skills <names>     Optional. Comma-separated skill names from .claude/skills/.
 *                        Each skill's markdown content is appended to the system prompt.
 *
 * Examples:
 *   npx tsx harness/planner.ts "member event booking system"
 *   npx tsx harness/planner.ts "redesign public homepage" --skills scgc-context
 *   npx tsx harness/planner.ts "flight log viewer" --skills scgc-context,some-other-skill
 *
 * Configuration (top of this file):
 *   MODEL          — Claude model to use (default: claude-opus-4-6)
 *   ALLOWED_TOOLS  — tools the agent may call
 *   MAX_TURNS      — maximum agentic turns before forced stop (default: 25)
 *
 * Output:
 *   .artifacts/spec.md            — generated product specification
 *   .artifacts/planner-trace.json — observability trace: every tool call,
 *                                   reasoning text, duration, cost, session ID
 */

import { query } from "@anthropic-ai/claude-agent-sdk";
import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync, rmSync } from "fs";
import { join, resolve } from "path";
import { randomUUID } from "crypto";

// ---------------------------------------------------------------------------
// Agent configuration — edit these to tune the planner
// ---------------------------------------------------------------------------

const MODEL = "claude-opus-4-6";

const ALLOWED_TOOLS = [
  // Write is constrained at runtime to ARTIFACTS — see buildAllowedTools()
  "Write",
  // Web research
  "WebSearch",
  "WebFetch",
  // Playwright MCP — the 8 essential inspection tools
  "mcp__playwright__browser_navigate",
  "mcp__playwright__browser_snapshot",
  "mcp__playwright__browser_take_screenshot",
  "mcp__playwright__browser_wait_for",
  "mcp__playwright__browser_resize",
  "mcp__playwright__browser_console_messages",
  "mcp__playwright__browser_network_requests",
  "mcp__playwright__browser_evaluate",
];

// Website inspection (scroll sweep + multi-page) needs ~60–80 SDK turns.
// Our display turn counter counts tool calls, not SDK turns, so logs may
// show higher numbers than this limit — that is expected behaviour.
const MAX_TURNS = 100;

// ---------------------------------------------------------------------------
// Types — observability event shapes
// ---------------------------------------------------------------------------

interface TextEvent {
  type: "text";
  turn: number;
  timestamp: string;
  content: string;
}

interface ToolCallEvent {
  type: "tool_call";
  turn: number;
  timestamp: string;
  tool: string;
  input: Record<string, unknown>;
}

interface ToolResultEvent {
  type: "tool_result";
  turn: number;
  timestamp: string;
  tool: string;
  duration_ms: number;
  /** First 500 chars of output — full output can be large */
  preview: string;
  is_error: boolean;
}

interface ErrorEvent {
  type: "error";
  turn: number;
  timestamp: string;
  message: string;
}

type ObservabilityEvent = TextEvent | ToolCallEvent | ToolResultEvent | ErrorEvent;

interface TraceSummary {
  turns_used: number;
  tool_call_counts: Record<string, number>;
  session_id: string;
  total_cost_usd: number;
  duration_ms: number;
  outcome: "success" | "error_max_turns" | "error" | "unknown";
}

interface Trace {
  run_id: string;
  started_at: string;
  brief: string;
  skills_injected: string[];
  events: ObservabilityEvent[];
  summary: TraceSummary | null;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const REPO_ROOT = resolve(import.meta.dirname, "..");
const ARTIFACTS = join(REPO_ROOT, ".artifacts");
const AGENTS_DIR = join(REPO_ROOT, ".claude", "agents");
const SKILLS_DIR = join(REPO_ROOT, ".claude", "skills");

function now(): string {
  return new Date().toISOString();
}

/** Strip YAML frontmatter (--- ... ---) from a markdown file. */
function stripFrontmatter(content: string): string {
  return content.replace(/^---[\s\S]*?---\n?/, "").trim();
}

/** Load agent system prompt from .claude/agents/<name>.md */
function loadAgentPrompt(name: string): string {
  const path = join(AGENTS_DIR, `${name}.md`);
  if (!existsSync(path)) throw new Error(`Agent definition not found: ${path}`);
  return stripFrontmatter(readFileSync(path, "utf-8"));
}

/** Load a skill from .claude/skills/<name>/SKILL.md */
function resolveSkillPath(name: string): string | null {
  const path = join(SKILLS_DIR, name, "SKILL.md");
  return existsSync(path) ? path : null;
}

function loadSkill(name: string): string {
  const path = resolveSkillPath(name);
  if (!path) throw new Error(`Skill not found: ${name}`);
  return readFileSync(path, "utf-8").trim();
}

/** Parse --skills flag from argv: "skill1,skill2" → ["skill1", "skill2"] */
function parseSkillsArg(argv: string[]): string[] {
  const idx = argv.indexOf("--skills");
  if (idx === -1) return [];
  const val = argv[idx + 1];
  if (!val || val.startsWith("--")) return [];
  return val.split(",").map((s) => s.trim()).filter(Boolean);
}

/** Count tool calls by tool name from events. */
function countToolCalls(events: ObservabilityEvent[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const e of events) {
    if (e.type === "tool_call") {
      counts[e.tool] = (counts[e.tool] ?? 0) + 1;
    }
  }
  return counts;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const args = process.argv.slice(2);
  const brief = args.find((a) => !a.startsWith("--"));

  if (!brief) {
    console.error('Usage: npx tsx planner.ts "<brief>" [--skills skill1,skill2]');
    process.exit(1);
  }

  const skillNames = parseSkillsArg(args);

  // Validate all skill files exist before doing anything else
  const missingSkills = skillNames.filter((name) => !resolveSkillPath(name));
  if (missingSkills.length > 0) {
    console.error(`Error: skill(s) not found in ${SKILLS_DIR}:`);
    missingSkills.forEach((s) => console.error(`  - ${s}.md`));
    const available = readdirSync(SKILLS_DIR).filter((entry) =>
      existsSync(join(SKILLS_DIR, entry, "SKILL.md"))
    );
    if (available.length > 0) {
      console.error(`\nAvailable skills: ${available.join(", ")}`);
    } else {
      console.error(`\nNo skills found in ${SKILLS_DIR}`);
    }
    process.exit(1);
  }

  mkdirSync(ARTIFACTS, { recursive: true });

  // Build system prompt: agent base + any injected skills
  let systemPrompt = loadAgentPrompt("planner");
  // Pin the absolute artifacts path so the agent never guesses a wrong path
  systemPrompt += `\n\nWrite all output files to: ${ARTIFACTS}/ (absolute path — use this, not a relative path)`;
  if (skillNames.length > 0) {
    const skillBlocks = skillNames.map((name) => {
      const content = loadSkill(name);
      return `\n\n## Skill: ${name}\n\n${content}`;
    });
    systemPrompt += "\n\n---\n# Injected Skills" + skillBlocks.join("");
  }

  const trace: Trace = {
    run_id: randomUUID(),
    started_at: now(),
    brief,
    skills_injected: skillNames,
    events: [],
    summary: null,
  };

  console.log("═══ PLANNER: starting ═══");
  console.log(`Run ID:  ${trace.run_id}`);
  console.log(`Brief:   ${brief}`);
  if (skillNames.length) console.log(`Skills:  ${skillNames.join(", ")}`);
  console.log("");

  const startMs = Date.now();

  // Tracks the last pending tool_call event so we can pair it with its result
  const pendingToolCalls = new Map<string, { event: ToolCallEvent; startMs: number }>();
  let turnCounter = 0;
  let sessionId = "";
  let totalCost = 0;
  let outcome: TraceSummary["outcome"] = "unknown";

  try {
    // Build Write permission with the resolved absolute artifacts path
    const allowedTools = ALLOWED_TOOLS.map((t) =>
      t === "Write" ? `Write(${ARTIFACTS}/*)` : t
    );

    for await (const msg of query({
      prompt: `${systemPrompt}\n\nBrief: ${brief}`,
      options: {
        model: MODEL,
        allowedTools,
        maxTurns: MAX_TURNS,
        permissionMode: "bypassPermissions",
        settingSources: ["project"],
      },
    })) {
      // The SDK yields messages of various types. We inspect content blocks
      // on assistant messages for tool_use and text, and tool_result messages
      // for results.

      if (msg.type === "assistant") {
        turnCounter++;
        const content = (msg as any).message?.content ?? [];

        for (const block of content) {
          if (block.type === "text" && block.text?.trim()) {
            const event: TextEvent = {
              type: "text",
              turn: turnCounter,
              timestamp: now(),
              content: block.text.trim(),
            };
            trace.events.push(event);
            // Print a short preview so the terminal stays informative
            const preview = block.text.trim().split("\n")[0].slice(0, 120);
            console.log(`[turn ${turnCounter}] ${preview}`);
          }

          if (block.type === "tool_use") {
            const event: ToolCallEvent = {
              type: "tool_call",
              turn: turnCounter,
              timestamp: now(),
              tool: block.name,
              input: block.input ?? {},
            };
            trace.events.push(event);
            pendingToolCalls.set(block.id, { event, startMs: Date.now() });
            console.log(`[turn ${turnCounter}] → ${block.name}(${summariseInput(block.input)})`);
          }
        }
      }

      // Tool results come back as "user" messages with tool_result content blocks
      if (msg.type === "user") {
        const userMsg = msg as any;
        const blocks: unknown[] = Array.isArray(userMsg.message?.content)
          ? userMsg.message.content
          : [];

        for (const block of blocks) {
          if ((block as any).type !== "tool_result") continue;
          const tr = block as any;
          const id: string = tr.tool_use_id ?? "";
          const pending = pendingToolCalls.get(id);
          const toolName = pending?.event.tool ?? "unknown";
          const durationMs = pending ? Date.now() - pending.startMs : 0;
          pendingToolCalls.delete(id);

          const rawContent = tr.content ?? "";
          const text =
            typeof rawContent === "string"
              ? rawContent
              : JSON.stringify(rawContent);

          const event: ToolResultEvent = {
            type: "tool_result",
            turn: turnCounter,
            timestamp: now(),
            tool: toolName,
            duration_ms: durationMs,
            preview: text.slice(0, 500),
            is_error: tr.is_error ?? false,
          };
          trace.events.push(event);
          console.log(
            `[turn ${turnCounter}] ← ${toolName} (${durationMs}ms)${event.is_error ? " ERROR" : ""}`
          );
        }
      }

      if (msg.type === "result") {
        const result = msg as any;
        sessionId = result.session_id ?? "";
        totalCost = result.total_cost_usd ?? 0;
        outcome =
          result.subtype === "success"
            ? "success"
            : result.subtype === "error_max_turns"
            ? "error_max_turns"
            : "error";
      }
    }
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    trace.events.push({
      type: "error",
      turn: turnCounter,
      timestamp: now(),
      message,
    });
    outcome = "error";
    console.error(`\nAgent error: ${message}`);
  }

  trace.summary = {
    turns_used: turnCounter,
    tool_call_counts: countToolCalls(trace.events),
    session_id: sessionId,
    total_cost_usd: totalCost,
    duration_ms: Date.now() - startMs,
    outcome,
  };

  // Write trace
  const tracePath = join(ARTIFACTS, "planner-trace.json");
  writeFileSync(tracePath, JSON.stringify(trace, null, 2));

  // Clean up Playwright screenshots captured during analysis
  const screenshotDir = join(REPO_ROOT, ".tmp", "playwright-site-inspector");
  if (existsSync(screenshotDir)) {
    rmSync(screenshotDir, { recursive: true, force: true });
    console.log(`Screenshots cleaned up: ${screenshotDir}`);
  }

  console.log("");
  console.log("═══ PLANNER: done ═══");
  console.log(`Spec:        ${join(ARTIFACTS, "spec.md")}`);
  console.log(`Trace:       ${tracePath}`);
  console.log(`Session:     ${sessionId}`);
  console.log(`Cost:        $${totalCost.toFixed(4)}`);
  console.log(`Turns used:  ${turnCounter}`);
  console.log(`Duration:    ${((Date.now() - startMs) / 1000).toFixed(1)}s`);
  console.log(`Outcome:     ${outcome}`);
  console.log("");
  console.log("Tool call breakdown:");
  for (const [tool, count] of Object.entries(countToolCalls(trace.events))) {
    console.log(`  ${tool.padEnd(30)} ${count}`);
  }
}

/** Produce a compact one-line summary of a tool's input for console output. */
function summariseInput(input: Record<string, unknown>): string {
  if (!input) return "";
  const val = input.query ?? input.url ?? input.path ?? input.command ?? input.pattern;
  if (val) return String(val).slice(0, 80);
  return Object.keys(input).join(", ");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
