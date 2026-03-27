# Controlling Claude agents with Playwright MCP for website inspection

**The key to reliable website inspection with a Claude planner agent is combining `browser_snapshot` as the primary inspection tool, `browser_wait_for` with text-based waits (not arbitrary timeouts), and a phased prompt structure that explicitly forces multi-page exploration.** Without structured prompts, Claude defaults to shallow single-page checks. The official Microsoft Playwright MCP exposes ~36 tools, but only 8 matter for inspection workflows. Accessibility snapshots cost **10–100× fewer tokens** than screenshots while providing actionable element references. The user's suggested prompt addition captures the right intent but uses incorrect tool names, relies on fixed timeouts instead of content-aware waits, and lacks the structured phases needed for thorough analysis.

---

## The right tool for each inspection task

The official `@playwright/mcp` package (Microsoft) provides three distinct tools for understanding page content, each serving a different purpose. Choosing wrong burns tokens and produces worse results.

**`browser_snapshot`** is the primary inspection tool and should be your default. It returns the page's accessibility tree as structured text — headings, links, buttons, forms, and their hierarchical relationships, each with a `ref` identifier (e.g., `- button "Submit" [ref=e21]`). The official README describes it as *"better than screenshot."* A typical snapshot costs **500–5,000 tokens** depending on page complexity. It captures semantic structure invisible in screenshots: heading hierarchy, ARIA roles, form labels, navigation landmarks, and interactive element states (disabled, expanded, checked). For a planner agent analyzing site architecture, this is exactly what you need — structure, not pixels.

**`browser_take_screenshot`** (note: not `browser_screenshot`) captures a pixel-perfect PNG/JPEG. Use it only for visual evidence: color schemes, layout spacing, visual regression documentation, and canvas/WebGL content the accessibility tree cannot represent. A 1280×720 screenshot costs **~1,229 tokens** via Claude's vision processing (formula: `width × height / 750`). Full-page screenshots with `fullPage: true` cost **~3,400+ tokens**. The official docs explicitly state: *"You can't perform actions based on the screenshot, use browser_snapshot for actions."*

**`browser_get_visible_text` does not exist** in the official Microsoft Playwright MCP. It only exists in the third-party `@executeautomation/playwright-mcp-server` fork. For text extraction, use `browser_snapshot` or run custom JavaScript via `browser_evaluate`.

The optimal pattern for a planner agent is **snapshot-first, screenshot-for-evidence**: use `browser_snapshot` to understand structure and identify elements, then `browser_take_screenshot` with `fullPage: true` to capture visual appearance for the planning report. This balances comprehension with token efficiency.

| Tool | Returns | Token cost | Best for |
|------|---------|-----------|----------|
| `browser_snapshot` | Accessibility tree (text) | 500–5,000 | Structure analysis, navigation mapping, element identification |
| `browser_take_screenshot` | PNG/JPEG image | 1,200–3,400 | Visual evidence, color schemes, layout documentation |
| `browser_evaluate` | JS execution result | Minimal | Custom data extraction, framework detection, computed styles |

---

## Handling pages that don't load instantly

There is **no `browser_wait_for_load_state`** and **no `browser_wait_for_timeout`** in Playwright MCP. The single wait tool is `browser_wait_for`, which accepts three parameters:

```
browser_wait_for({ time: 5 })           // Wait 5 seconds
browser_wait_for({ text: "Dashboard" }) // Wait for text to appear
browser_wait_for({ textGone: "Loading..." }) // Wait for text to disappear
```

**Fixed timeouts are the worst strategy.** The user's suggestion of "wait for 5 seconds for each page load" wastes time on fast pages and may not be enough for slow ones. The far better approach is content-aware waiting — wait for specific content to appear or loading indicators to disappear. For SPAs and dynamically loaded content, this distinction is critical because SPAs don't trigger traditional page load events, and `networkidle` is unreliable due to background analytics and WebSocket connections.

The recommended wait strategy for a planner agent, in order of preference:

1. **Snapshot verification** — after navigating, take a `browser_snapshot`. If the snapshot shows meaningful content (headings, navigation elements), the page is ready. If it shows only a loading spinner or skeleton, wait and re-snapshot.
2. **Text-based waits** — use `browser_wait_for({ textGone: "Loading" })` or `browser_wait_for({ text: "Welcome" })` to wait for specific content signals.
3. **Timed fallback** — use `browser_wait_for({ time: 2 })` only as a last resort when you cannot identify content markers.

Playwright MCP also has built-in auto-wait behavior: the underlying Playwright engine waits for elements to be visible, enabled, and stable before performing actions. The default navigation timeout is **60 seconds** (`--timeout-navigation`), and the default action timeout is **5 seconds** (`--timeout-action`). These handle most standard page loads automatically — explicit waits are only needed for lazy-loaded or dynamically rendered content.

A robust prompt instruction for page loading looks like this:

```markdown
## Page Load Protocol
- After navigating to any URL, immediately take a browser_snapshot
- If the snapshot shows a loading indicator, skeleton screen, or minimal content:
  - Use browser_wait_for with textGone for the loading indicator
  - Then take another browser_snapshot to verify content loaded
- If no loading indicator is identifiable, use browser_wait_for with time: 3 as fallback
- Never proceed to analysis until the snapshot shows substantive page content
```

---

## Writing prompts that force systematic multi-page inspection

Without explicit structure, Claude will inspect the homepage and stop. The most effective pattern discovered across community implementations combines **persona engineering, phased instructions, and non-negotiable rules**. Here is the anatomy of a thorough inspection prompt, drawing from proven real-world examples.

**Persona framing changes Claude's behavior fundamentally.** The "Quinn" QA engineer pattern (from alexop.dev) gives Claude a testing philosophy — *"Trust nothing. Users are creative. Edge cases are where bugs hide."* — that makes it actively seek issues rather than passively describe what it sees. For a planner agent, the persona should be a senior web analyst or UX auditor rather than a QA tester.

**Phased structure is non-negotiable for thoroughness.** The most effective pattern breaks inspection into five explicit phases:

```markdown
## Phase 1: Homepage Discovery
Navigate to the homepage. Take a snapshot to understand page structure.
Catalog ALL navigation links (header, footer, sidebar). Take a full-page screenshot.
Check console messages for errors.

## Phase 2: Multi-Page Exploration
Visit EVERY page linked from the main navigation. For each page:
take a snapshot, record the URL and title, note the page template type,
check for console errors. After primary pages, check footer links for
additional pages (privacy policy, sitemap, etc.).

## Phase 3: Responsive Behavior
For each unique page template found, test at three viewpoints:
- Mobile: browser_resize({ width: 375, height: 667 })
- Tablet: browser_resize({ width: 768, height: 1024 })
- Desktop: browser_resize({ width: 1440, height: 900 })
Take a screenshot at each breakpoint. Note layout changes, navigation
behavior (hamburger menu?), content reflow, touch target sizes.

## Phase 4: Interactive Elements & Technology
Test all forms, buttons, and interactive elements found.
Run browser_network_requests to identify API calls and technology stack.
Run browser_console_messages to find JavaScript errors.
Use browser_evaluate to check for framework globals (React, Vue, Next.js).

## Phase 5: Structured Report
Compile all findings into the report template below.
```

**Anti-superficiality rules prevent shortcuts.** Include explicit constraints like: *"CONTINUE AFTER ISSUES — finding a problem does not end the inspection"*, *"VISIT ALL NAVIGATION LINKS — do not stop at the homepage"*, and *"SCROLL FULLY — use fullPage: true on screenshots to capture below-the-fold content."*

The key prompt patterns that distinguish thorough from superficial inspection are: explicit page counts ("visit at minimum 5 pages"), enumerated deliverables ("produce screenshots at 3 breakpoints per template"), and phase gates ("do not proceed to Phase 3 until Phase 2 is complete for all pages").

---

## Console and network tools reveal the technology stack

**`browser_console_messages`** returns all console output accumulated since page load, filtered by severity level (`error`, `warning`, `info`, `debug`). This catches JavaScript errors, deprecation warnings, and framework-specific messages that indicate what the site is built with. React development builds emit distinctive warnings; Next.js logs hydration mismatches; Angular logs change detection cycles.

**`browser_network_requests`** returns all HTTP requests since page load. With `includeStatic: false` (the default), it filters to API calls and failed requests — exactly what a planner needs to understand data architecture. With `includeStatic: true`, it reveals the full resource loading pattern including framework bundles.

For technology detection, the most reliable approach combines three signals:

**Network URL patterns** are the strongest indicators. Next.js sites make requests to `/_next/data/*.json` and load chunks from `/_next/static/`. Gatsby uses `/__gatsby/` paths. Vue/Nuxt applications show `/__nuxt/` patterns. WordPress loads from `/wp-content/` and `/wp-json/`. These patterns survive production builds that strip debug globals.

**JavaScript globals via `browser_evaluate`** provide direct confirmation. A detection script like `() => ({ react: !!document.querySelector('[data-reactroot]'), nextjs: !!document.querySelector('#__next'), vue: !!window.__VUE__, angular: !!window.ng })` can identify the major frameworks in one call.

**Console messages** provide supplementary signals — React development mode warnings, Angular's `platform-browser` messages, or framework-specific error formats all identify the stack.

For planning improvements, the network request data is particularly valuable: it reveals API endpoints (suggesting backend architecture), third-party service integrations (analytics, CDN, payment processors), failed requests (broken functionality), and resource loading performance (which assets are heaviest). This information directly feeds into improvement specifications.

---

## Structured output that serves the planner

The output format matters because the planner agent will use this analysis to generate improvement specifications. Based on community patterns, **a detailed Markdown report with embedded tables** works best — it's human-readable for review, parseable by downstream agents, and naturally structured.

The report should capture seven categories of information:

```markdown
# Site Analysis Report: [Site Name]

## Overview
- URL, date inspected, total pages found, technology stack detected

## Site Architecture
| Page | URL | Template Type | Key Components |
|------|-----|--------------|----------------|
(Table of all pages discovered with their structural characteristics)

## Navigation Structure
- Primary navigation items and hierarchy
- Footer navigation
- Breadcrumbs or secondary navigation
- Mobile navigation pattern (hamburger, tab bar, etc.)

## Design System Observations
- Color palette (primary, secondary, accent — captured from screenshots)
- Typography patterns (heading sizes, body font)
- Component library indicators (Material UI, Tailwind, Bootstrap patterns)
- Spacing and grid system

## Responsive Behavior
| Page Template | Mobile | Tablet | Desktop | Issues |
|--------------|--------|--------|---------|--------|
(Breakpoint testing results with specific observations)

## Technical Health
- Console errors found (with page and severity)
- Failed network requests
- Performance observations (heavy resources, slow loads)
- Accessibility issues from snapshot analysis

## Improvement Opportunities
- Prioritized list derived from all findings above
```

For programmatic downstream consumption, a JSON schema works when the planner needs to feed findings into a task generator. But for most planning workflows, Markdown strikes the right balance between structure and readability. The key principle: **capture facts, not opinions** — the planner agent should receive objective structural data and make its own improvement decisions.

---

## Prompt engineering that prevents shallow analysis

Three techniques reliably produce thorough inspection behavior, validated across multiple community implementations.

**First, restrict available tools to force browser-only interaction.** The `--allowedTools` pattern from the "Quinn" QA system limits Claude to `browser_navigate`, `browser_snapshot`, `browser_take_screenshot`, `browser_click`, `browser_type`, `browser_resize`, and `browser_wait_for`. This prevents "cheating" by reading source code directly and forces authentic user-perspective analysis. For a planner agent, add `browser_console_messages`, `browser_network_requests`, and `browser_evaluate` to enable technology detection.

**Second, use explicit checklists rather than open-ended instructions.** Instead of "inspect the website thoroughly," provide: *"For each page, record: (1) heading hierarchy from h1 through h3, (2) number of interactive elements, (3) navigation links present, (4) form fields and their types, (5) console errors, (6) screenshot at mobile and desktop breakpoints."* Checklists create accountability — Claude will work through each item.

**Third, require the agent to report its progress.** Instructions like *"After completing each phase, list which pages you have visited and which remain"* create a self-monitoring loop that prevents premature termination. This is especially important for multi-page inspection where Claude might decide after three pages that it has "enough" information.

A complete system prompt incorporating these principles:

```markdown
You are a meticulous web analyst performing a comprehensive site audit.
You MUST use Playwright MCP tools exclusively — do not read source files.

RULES:
1. Visit EVERY page linked from primary and footer navigation
2. For each page: snapshot first, then full-page screenshot
3. After navigation, verify page loaded via snapshot before analyzing
4. Test responsive behavior at 375px, 768px, and 1440px widths
5. Check console errors and network requests on every page
6. Continue inspecting even after finding issues
7. Report progress: list visited vs remaining pages after each phase

Follow the five phases below in order. Do not skip any phase.
Do not declare the inspection complete until all phases are finished.
[... phases as described in previous section ...]
```

---

## Improving the user's suggested prompt addition

The user proposes adding this to the planner system prompt:

> *"When a site is provided serve as the existing project to be analysed on. Take through look using mcp__playwright__ mcp inspecting the website. load web pages. Inspect it visually some cases it is not able to load instantly, wait for 5 seconds for each page load."*

**What's right about this:** It correctly identifies that (1) the planner should treat a provided URL as the existing project to analyze, (2) Playwright MCP should be used for inspection, (3) pages may not load instantly and need wait handling, and (4) visual inspection is important. The intent is sound.

**What needs fixing:**

- **Tool names are vague.** `mcp__playwright__` is incomplete — specific tool names like `mcp__playwright__browser_navigate`, `mcp__playwright__browser_snapshot`, and `mcp__playwright__browser_take_screenshot` should be referenced.
- **Fixed 5-second waits waste time and may not be enough.** Replace with content-aware waits using `mcp__playwright__browser_wait_for`.
- **"Inspect it visually" is too vague.** Doesn't specify what to capture, how many pages to visit, or what output format to produce.
- **No multi-page instruction.** Without explicit direction, Claude will inspect only the homepage.
- **No structured output requirement.** The planner needs specific data to generate improvement specs.
- **No responsive testing.** Doesn't mention viewport testing, which is critical for planning.
- **No technology detection.** Missing console/network inspection for understanding the tech stack.

**Improved version:**

```markdown
## Existing Site Analysis Protocol

When a URL is provided as the existing project to analyze, perform a comprehensive
site inspection using Playwright MCP tools before planning any improvements.

### Step 1: Load and verify
- Use mcp__playwright__browser_navigate to open the provided URL
- Use mcp__playwright__browser_snapshot to verify the page loaded
- If the snapshot shows loading indicators or minimal content, use
  mcp__playwright__browser_wait_for with textGone for the loading text,
  or with time: 3 as a fallback, then snapshot again

### Step 2: Homepage analysis
- Record the full accessibility snapshot (heading hierarchy, navigation
  structure, interactive elements, content sections)
- Use mcp__playwright__browser_take_screenshot with fullPage: true for
  visual reference
- Use mcp__playwright__browser_console_messages with level: "error" to
  check for JavaScript errors
- Use mcp__playwright__browser_network_requests to identify API calls
  and technology stack

### Step 3: Multi-page exploration
- Extract all navigation links from the homepage snapshot
- Visit EACH primary navigation link using browser_navigate
- For each page: snapshot, full-page screenshot, console error check
- Record the page URL, title, template type, and key components
- Continue until all primary navigation pages are inspected

### Step 4: Responsive check
- For each unique page template found, test at:
  - Mobile: mcp__playwright__browser_resize width 375, height 667
  - Desktop: mcp__playwright__browser_resize width 1440, height 900
- Take a screenshot at each breakpoint and note layout changes

### Step 5: Technology detection
- Use mcp__playwright__browser_evaluate to check for framework globals
  (React, Vue, Angular, Next.js, WordPress indicators)
- Review network request patterns for framework-specific URLs

### Step 6: Compile findings
Produce a structured Site Analysis Report covering: site architecture,
navigation structure, design patterns, component types, technology stack,
responsive behavior, console errors, and prioritized improvement opportunities.
Use this report as the foundation for all subsequent planning.
```

This improved version transforms a vague two-sentence instruction into an actionable protocol that references **exact tool names**, uses **content-aware waits** instead of fixed delays, enforces **multi-page exploration**, includes **responsive testing** and **technology detection**, and requires **structured output** the planner can act on. The phased structure prevents Claude from doing a superficial homepage-only inspection, and the explicit tool references eliminate ambiguity about which Playwright MCP capabilities to use.

---

## Conclusion

Reliable website inspection with a Claude planner agent hinges on three architectural decisions. **Use `browser_snapshot` as the primary lens** — it provides 10–100× better token efficiency than screenshots while delivering the structural data a planner actually needs (heading hierarchy, navigation topology, component inventory, interactive element states). Reserve `browser_take_screenshot` with `fullPage: true` exclusively for visual evidence capture. **Replace fixed timeouts with content-aware waits** — `browser_wait_for({ textGone: "Loading" })` is both faster and more reliable than `browser_wait_for({ time: 5 })`, especially for SPAs. **Structure the prompt as explicit numbered phases with non-negotiable rules** — without this, Claude consistently defaults to a shallow single-page check regardless of how thoroughly you ask it to inspect.

The 8 essential tools for an inspection workflow are: `browser_navigate`, `browser_snapshot`, `browser_take_screenshot`, `browser_wait_for`, `browser_resize`, `browser_console_messages`, `browser_network_requests`, and `browser_evaluate`. Everything else is interaction tooling for testing, not analysis. For maximum efficiency in long sessions, consider the hybrid approach: use MCP for exploratory inspection (~114K tokens per task), then generate reusable Playwright scripts via the CLI for repeated analysis (~27K tokens per task, a **4× reduction**).