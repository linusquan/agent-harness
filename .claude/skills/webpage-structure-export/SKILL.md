---
name: webpage-structure-export
description: Exports the content structure of a website as a YAML content map — routes, sections, and what each section contains — using the standard webpage-structure schema. Use this skill whenever the user wants to document, map, or export the structure of an existing website, whether they provide a URL, a site-inspector report, screenshots, or a verbal description. Trigger on phrases like "export the site structure", "map the pages", "document the website layout", "generate a content map", "create a structure export", "describe the pages as YAML", or when someone says they want a design agent or LLM to understand the site layout. Also trigger when the user has just run site-inspector and asks "now export this" or similar.
---

Your job is to produce a clean YAML content map of a website following the schema below. The output is meant to be consumed by a design agent — it must be accurate, readable, and focused on what a visitor sees, not implementation details.

## Output Schema

```yaml
site:
  name: "Site Name"
  url: "https://example.com"

routes:
  - path: "/"
    name: "Homepage"
    page_type: landing        # landing | content | listing | detail | form | auth | error | utility
    purpose: "One sentence: what is this page trying to achieve?"

    sections:
      - name: "Section Name"
        position: header      # header | main | sidebar | footer
        content:
          - Plain-language description of each visible element
          - "Headline (h1): the actual text or a summary of it"
          - "CTA button: label text"
          - "3-column grid of feature cards, each with: icon + title + short paragraph"
```

**Page type guide:**
- `landing` — selling something; has hero, CTAs, social proof
- `content` — long-form reading: blog post, docs, help article
- `listing` — a collection: blog index, product catalog, team page
- `detail` — single item deep view: case study, job posting, product page
- `form` — primary purpose is input: contact, application, survey
- `auth` — login, signup, password reset
- `error` — 404, 500, maintenance
- `utility` — legal pages, settings, terms of service

**Content descriptions — the right level of detail:**
- Name the element, note its role, summarise what it says or shows
- Good: `Headline (h1): value proposition about team productivity`
- Good: `3 testimonial cards: photo + quote + name/title`
- Too vague: `Text`, `Button`, `Image`
- Too detailed: exact pixel sizes, hex colours, font weights

Shorthands that work well:
- `Logo bar: 6 client logos`
- `Accordion with 8 FAQ items`
- `Nav links: Products, Pricing, About, Contact`
- `Form fields: name, email, message, submit button`

---

## Workflow

### If given a URL

Use Playwright browser tools to inspect the site, then produce the YAML.

1. **Navigate and inspect each page:**
   ```
   browser_navigate: <url>
   browser_snapshot          ← accessibility tree shows headings, links, buttons
   browser_evaluate: () => window.scrollTo(0, 500)  ← scroll to trigger lazy-loaded content
   browser_evaluate: () => window.scrollTo(0, 0)
   browser_snapshot          ← definitive snapshot after scroll sweep
   ```

2. **Follow all primary navigation links** — do not stop at the homepage. Visit header nav links, then footer links for secondary pages.

3. **For each page**, record:
   - The URL path
   - The page's apparent purpose
   - Every visible section from top to bottom
   - What's in each section, described informally

4. After visiting all pages, compile and output the YAML.

**Use `browser_snapshot` (accessibility tree) as your primary tool** — it reveals heading hierarchy, nav landmarks, buttons, and forms more reliably than screenshots. Use `browser_take_screenshot` only if you need to verify visual layout or colours.

### If given a site-inspector report or description

Read the provided material and map what you find into the schema. If something is ambiguous, make a reasonable inference and note it with a comment in the YAML (`# inferred`).

### If given screenshots or mockups

Describe what you see section by section and map it to the schema.

---

## Output format

Output the YAML as a fenced code block. After the block, add a brief plain-language summary (2–4 sentences) of the site's structure — number of routes, main page types, any patterns worth noting for a design agent.

Use `(same as homepage)` for repeated shared sections like nav and footer to avoid duplication. Mark dynamic route templates with `dynamic: true`.

---

## What to include and exclude

**Include:**
- Every route a visitor can reach via navigation
- Sections in top-to-bottom order
- The actual content visible on the page (not code, not CMS fields)

**Exclude:**
- Implementation details (CSS classes, component names, database fields)
- Hidden or admin-only pages
- Exact copy unless it's a short label like a CTA button or heading
