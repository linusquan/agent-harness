---
name: site-inspector
description: Comprehensive website inspection using Playwright MCP — performs a systematic multi-page audit covering structure, navigation, responsive behaviour, technology stack, and visual design. Use this skill whenever a URL is provided and the user wants to analyse, audit, understand, or plan improvements for an existing website. Trigger on phrases like "inspect this site", "analyse the website", "look at this URL", "audit the site", "what does this site look like", "check the existing site", or when a URL is mentioned alongside words like improve, redesign, plan, or audit.
---

You are conducting a thorough website inspection using Playwright MCP browser tools.
Do NOT read source code files — use browser tools exclusively for authentic user-perspective analysis.

The 8 tools you use: `browser_navigate`, `browser_snapshot`, `browser_take_screenshot`,
`browser_wait_for`, `browser_resize`, `browser_console_messages`, `browser_network_requests`,
`browser_evaluate`.

**Why `browser_snapshot` over screenshots:** Snapshots return the accessibility tree as
structured text — headings, links, buttons, forms, each with a `ref` identifier. They cost
500–5,000 tokens vs 1,200–3,400 for a screenshot, and they capture semantic structure
(ARIA roles, heading hierarchy, nav landmarks) that screenshots cannot. Use screenshots
only for visual evidence: colour schemes, layout spacing, animation state.

**Why content-aware waits over fixed delays:** `browser_wait_for({ textGone: "Loading" })`
is both faster and more reliable than `browser_wait_for({ time: 5 })`, especially for SPAs
where traditional page-load events don't fire.

---

## Phase 1 — Load and verify

```
browser_navigate: <url>
browser_snapshot           ← verify page loaded
```

If the snapshot shows a loading spinner, skeleton screen, or minimal content:
- `browser_wait_for({ textGone: "<loading text>" })` — preferred
- `browser_wait_for({ time: 3 })` — fallback only
- Then snapshot again before proceeding.

---

## Phase 2 — Homepage analysis with scroll sweep

Pages with scroll-triggered animations (content that animates in as you scroll) will be
**missing from a snapshot taken only at the top**. The scroll sweep fires those triggers
so everything is in the DOM before the definitive snapshot.

```
// 1. Get total page height
browser_evaluate: () => document.body.scrollHeight

// 2. Scroll through in 500px increments, pausing for animations
browser_evaluate: () => window.scrollTo(0, 500)
browser_wait_for: { time: 1 }
browser_evaluate: () => window.scrollTo(0, 1000)
browser_wait_for: { time: 1 }
// ... continue until scrollHeight reached

// 3. Return to top
browser_evaluate: () => window.scrollTo(0, 0)
browser_wait_for: { time: 1 }

// 4. Definitive snapshot — all scroll-triggered content now in DOM
browser_snapshot
browser_take_screenshot: { fullPage: true }
browser_console_messages: { level: "error" }
browser_network_requests
```

Record from the snapshot: heading hierarchy (h1–h3), primary navigation items,
interactive elements, content sections, footer links.

---

## Phase 3 — Multi-page exploration

Extract every navigation link from the homepage snapshot (header, footer, sidebar).
Visit each one:

```
browser_navigate: <page-url>
[scroll sweep if page is long]
browser_snapshot
browser_take_screenshot: { fullPage: true }
browser_console_messages: { level: "error" }
```

For each page record: URL, title, template type (landing, list, detail, form, etc.),
key components present.

After primary nav pages, check footer links for additional pages (privacy policy,
sitemap, contact, etc.).

**Do not stop at the homepage.** Report progress after this phase:
list all pages visited and any links not yet visited.

---

## Phase 4 — Responsive check

For each unique page template found, test two breakpoints:

```
browser_resize: { width: 375, height: 667 }   ← mobile
browser_take_screenshot: { fullPage: true }

browser_resize: { width: 1440, height: 900 }  ← desktop
browser_take_screenshot: { fullPage: true }
```

Note: navigation pattern change (hamburger menu?), content reflow, touch target sizes,
any layout breakage.

---

## Phase 5 — Technology detection

```
browser_evaluate: () => ({
  react:   !!document.querySelector('[data-reactroot]'),
  nextjs:  !!document.querySelector('#__next'),
  vue:     !!window.__VUE__,
  angular: !!window.ng,
  jquery:  !!window.jQuery,
  wp:      !!document.querySelector('link[href*="wp-content"]')
})
```

Also review:
- Network URL patterns: `/_next/` → Next.js, `/wp-content/` → WordPress,
  `/__nuxt/` → Nuxt, `/static/js/main.` → Create React App
- Console messages for framework-specific warnings

---

## Phase 6 — Compile Site Analysis Report

```markdown
# Site Analysis Report: <Site Name>
Inspected: <date> | URL: <url> | Pages found: <N> | Stack: <detected>

## Site Architecture
| Page | URL | Template | Key Components |
|------|-----|----------|----------------|

## Navigation Structure
- Primary nav: ...
- Footer nav: ...
- Mobile pattern: ...

## Design System Observations
- Colour palette: ...
- Typography: ...
- Component library indicators: ...

## Responsive Behaviour
| Template | Mobile | Desktop | Issues |
|----------|--------|---------|--------|

## Technical Health
- Console errors: ...
- Failed network requests: ...
- Performance observations: ...


```

---

## Non-negotiable rules

- **Continue after finding issues** — a bug or broken page does not end the inspection
- **Visit all navigation links** — do not stop at the homepage
- **Scroll sweep every long page** — scroll-triggered content will be invisible otherwise
- **Report progress** — after each phase, list pages visited and pages remaining
- **No source file access** — browser tools only; source code is not available to you
