# Brief v2: Paper Triage single page, redesigned to DESIGN.md (Airtable system)

Status: ready for planner + frontend-builder. Author: designer, 2026-10-01.
Sources: DESIGN.md (active spec, Airtable), PRODUCT.md, specs/001-paper-triage/contracts/api.md,
current `src/paper_triage/static/` (read only; old Apple-style look is replaced, not polished).

Every implementable item is tagged `[FE] Dn`. Items that need backend work are tagged
`NEEDS-BE Bn` (section 9); the planner turns those into tasks. FE must not invent the BE contract.

---

## 0. Job, mode, direction

- **Who:** one researcher skimming a pile of new papers, locally. Goal: cut the list to the few worth opening.
- **Mode:** Operate (tool UI). Task, state, and scanability outrank expression.
- **Direction:** Airtable editorial calm translated to a tool. White canvas, ink type at modest weights,
  near-black primary button, hairline rules instead of boxed cards. Brand voltage is spent on exactly
  three surfaces, all full-surface (never small accents): the **cream** working card (triage running),
  the **cream** chat refusal, the **coral** triage-failure card.
- **Anti-goals:** gradient hero, centered marketing hero, card-grid-of-everything, chat-bubble AI gloss,
  progress bars or percentages that imply backend progress we do not have, emoji.

### Deliberate deviations from DESIGN.md (all for tool use or a11y)

| DESIGN.md says | Brief does | Why |
|---|---|---|
| Haas Grotesk / Haas Groot Disp fonts | System stack, Helvetica Neue first (D2) | No external fonts. Helvetica derives from Neue Haas Grotesk; closest installed match on macOS. |
| `description` says "pill CTA" | Primary button uses `--radius-lg` 12px | Components section and Don'ts forbid pill outside pricing. Components win. |
| 96px section rhythm | 32 / 48px rhythm | Tool UI, one screen of work. 96px would push results below the fold. |
| Inputs: `hairline` #dddddd border | Input/secondary-button edge `--color-edge-input` #8e939c | Hairline is 1.36:1, `border-strong` is 2.93:1. WCAG 1.4.11 needs 3:1. #8e939c is 3.09:1 (derived neutral, not an accent). |
| `body-md` line-height 1.25 | Multi-line prose uses 1.5 (`--leading-prose`) | 1.25 is for single UI lines; paragraphs at 1.25 are hard to read. |
| No error color | Errors use `signature-coral` as full surface or as text | Coral on white 6.8:1, white on coral 6.8:1. No new hue added. |
| No hover states | No hover styling. Default, active, focus-visible, disabled only. | Follows DESIGN.md. Cursor changes only. |
| Animation out of scope | Motion tokens defined in D1, used only by D14/D20/D25 | Needed for the running indicator. |
| `text-link` no underline | Inline links inside prose are underlined; standalone links (D10) are not | Link blue vs body text is 2.0:1; WCAG 1.4.1 needs underline for in-prose links. |

---

## 1. Tokens

### [FE] D1 — CSS custom properties (replace the whole `:root` block in `app.css`)

Every DESIGN.md token maps to one property. Unused tokens are still declared so the mapping is complete;
they are marked `unused`.

**Color** (`--color-<token>`)

| DESIGN token | Property | Value | Use here |
|---|---|---|---|
| primary | `--color-primary` | #181d26 | primary button bg |
| primary-active | `--color-primary-active` | #0d1218 | primary button `:active` |
| ink | `--color-ink` | #181d26 | headings, titles, rank number |
| body | `--color-body` | #333840 | running text |
| muted | `--color-muted` | #41454d | meta, captions, authors |
| hairline | `--color-hairline` | #dddddd | row dividers, panel borders (decorative only) |
| border-strong | `--color-border-strong` | #9297a0 | disabled secondary button edge |
| canvas | `--color-canvas` | #ffffff | page |
| surface-soft | `--color-surface-soft` | #f8fafc | chat panel, fetch-notes box, details body |
| surface-strong | `--color-surface-strong` | #e0e2e6 | chips, rank meter track |
| surface-dark | `--color-surface-dark` | #181d26 | unused |
| surface-dark-elevated | `--color-surface-dark-elevated` | #1d1f25 | unused |
| signature-coral | `--color-coral` | #aa2d00 | triage-failure card, error text, Failed chip |
| signature-forest | `--color-forest` | #0a2e0e | unused |
| signature-cream | `--color-cream` | #f5e9d4 | working card, refusal, new-row and cited-row flash |
| signature-peach | `--color-peach` | #fcab79 | unused |
| signature-mint | `--color-mint` | #a8d8c4 | unused |
| signature-yellow | `--color-yellow` | #f4d35e | unused |
| signature-mustard | `--color-mustard` | #d9a441 | unused |
| on-primary | `--color-on-primary` | #ffffff | text on primary / coral |
| on-dark | `--color-on-dark` | #ffffff | unused |
| link | `--color-link` | #1b61c9 | paper links, citation focus |
| link-active | `--color-link-active` | #1a3866 | link `:active` |
| info | `--color-info` | #254fad | mock-mode badge text |
| info-border | `--color-info-border` | #458fff | focus ring, focused input border, mock badge edge |
| success | `--color-success` | #006400 | unused |
| success-border | `--color-success-border` | #39bf45 | unused |
| pricing-ink | `--color-pricing-ink` | #1d1f25 | unused |
| (derived) | `--color-edge-input` | #8e939c | input + secondary-button 1px edge (3.09:1) |

**Typography.** Each role becomes a `font` shorthand plus a tracking property:
`--type-<role>: <weight> <size>/<line-height> var(--font-<text|display>)` and `--tracking-<role>`.

| DESIGN role | Property | Shorthand | Tracking | Use here |
|---|---|---|---|---|
| display-xl | `--type-display-xl` | 500 48px/1.1 display | 0 | unused |
| display-lg | `--type-display-lg` | 400 40px/1.2 display | 0 | unused |
| display-md | `--type-display-md` | 400 32px/1.2 display | 0 | h1 (desktop), rank number (desktop) |
| title-lg | `--type-title-lg` | 400 24px/1.35 text | 0.12px | results h2, h1 (mobile) |
| title-md | `--type-title-md` | 400 20px/1.5 display | 0 | chat h2 |
| title-sm | `--type-title-sm` | 500 18px/1.4 text | 0 | paper title, working verb, empty-state title |
| label-md | `--type-label-md` | 500 16px/1.4 text | 0 | brand wordmark, chat question, refusal heading |
| button | `--type-button` | 500 16px/1.4 text | 0 | all buttons |
| body-md | `--type-body-md` | 400 14px/1.25 text | 0 | single-line UI text |
| caption | `--type-caption` | 500 14px/1.35 text | 0.16px | meta, counts, links row, section labels |
| legal | `--type-legal` | 600 13.12px/1.2 text | 0 | unused |
| pricing-display / pricing-section / pricing-card-title | `--type-pricing-*` | as DESIGN.md, `--font-pricing` | 0 | unused (pricing sub-system) |
| (derived) | `--leading-prose` | 1.5 | — | reason, summary, critique, chat answers |
| (derived) | `--type-reason` | 400 16px/1.5 text | 0 | rank reason (at-a-glance line; "bigger before bolder") |
| (derived) | `--type-chip` | 500 13px/1.2 text | 0 | flags, citation chips, mock badge |
| (derived) | `--font-mono` | `ui-monospace, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace` | — | paper ids |

**Radius** (`--radius-<token>`): `--radius-xs` 2px (unused), `--radius-sm` 6px (inputs, chips),
`--radius-md` 10px (working card, refusal, notes box, coral card), `--radius-lg` 12px (buttons, chat panel),
`--radius-pill` 9999px (unused, pricing only), `--radius-full` 9999px (glyph container only).

**Spacing** (`--space-<token>`): `--space-xxs` 4px, `--space-xs` 8px, `--space-sm` 12px, `--space-md` 16px,
`--space-lg` 24px, `--space-xl` 32px, `--space-xxl` 48px, `--space-section` 96px (unused, see deviations).

**Elevation** (from DESIGN.md "Elevation & Depth"; values derived, alphas low):
- `--shadow-button`: `0 1px 2px rgba(24,29,38,.12), 0 2px 6px rgba(27,97,201,.10)` — primary button rest.
- `--ring-focus`: `0 0 0 2px var(--color-canvas), 0 0 0 4px var(--color-info-border)` — see D3.
- No other shadows anywhere. Cards are flat.

**Motion** (derived; DESIGN.md has none):
`--ease-out: cubic-bezier(.2,.7,.2,1)`, `--dur-fast: 150ms`, `--dur-base: 200ms`, `--dur-flash: 1600ms`.

**Layout:** `--nav-h: 64px`, `--page-max: 1280px`, `--chat-w: 384px`, `--measure: 72ch`.

### [FE] D2 — Font stacks (no `@font-face`, no network)

```css
--font-text: "Neue Haas Grotesk Text Pro", "Neue Haas Grotesk Text", "Haas Grotesk", "Helvetica Neue",
  -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans",
  "Droid Sans", Arial, sans-serif;
--font-display: "Neue Haas Grotesk Display Pro", "Neue Haas Grotesk Display", "Haas Groot Disp",
  "Helvetica Neue", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell,
  "Fira Sans", "Droid Sans", Arial, sans-serif;
--font-pricing: "Inter Display", system-ui, sans-serif; /* unused */
```

Haas names only resolve if the user has them installed locally; otherwise Helvetica Neue (macOS) or Segoe UI
(Windows). Body: `font: var(--type-body-md); color: var(--color-body); -webkit-font-smoothing: antialiased`.
All numbers that change (rank, counts, elapsed time) use `font-variant-numeric: tabular-nums`.
Max weight anywhere is 500. No 600/700 (remove the old `<strong>` bolding; use 500 via a class).

### [FE] D3 — Base, focus, forced colors

- Remove the old `letter-spacing: -0.374px` body tracking and the blue `::selection`. Selection:
  `background: var(--color-cream); color: var(--color-ink)`.
- Focus: `:focus-visible { outline: 2px solid var(--color-info-border); outline-offset: 2px; }`
  (3.17:1 on canvas, 3.03:1 on surface-soft). On coral surfaces use `outline-color: var(--color-on-primary)`.
  Primary button may use `box-shadow: var(--ring-focus)` instead of outline (DESIGN "Button focus").
- Keep the existing `forced-colors: active` block, updated to the new selectors (badges, chips, cards get
  `border: 1px solid CanvasText`; working glyph uses `CanvasText`).
- Keep `.sr-only` and the skip link; skip link styled as button-secondary, `--radius-sm`.

---

## 2. Page layout

### [FE] D4 — Shell and grid

```
┌ top-nav (64px, canvas, hairline bottom) ───────────────────────────────┐
│ Paper Triage                                  Model: … [Mock mode]     │
├ query band (canvas) ───────────────────────────────────────────────────┤
│ h1 Find the papers worth reading.                                      │
│ lead                                                                   │
│ [ input ........................................ ] [Triage papers]     │
│ help                                                                   │
├ workspace ─────────────────────────────────────────────────────────────┤
│ results column (1fr)                    │ chat panel (384px, sticky)   │
│  header, working card / alert, list,    │  surface-soft, radius-lg     │
│  load-more                              │                              │
└─────────────────────────────────────────┴──────────────────────────────┘
```

- Container: `max-width: var(--page-max)`, centered, horizontal padding `--space-xxl` (desktop),
  `--space-lg` (tablet), `--space-md` (mobile).
- Workspace ≥1024px: `display: grid; grid-template-columns: minmax(0,1fr) var(--chat-w); gap: var(--space-xxl);`
  padding-block `--space-xl` top, `--space-xxl` bottom.
- Query band and workspace are both canvas; separate them with one 1px `--color-hairline` rule, full container width.
- Skip links (top-left, visually hidden until focus): "Skip to results" (`#results-heading`) and
  "Skip to chat" (`#chat-heading`).

### [FE] D5 — Top nav (`header.global-nav`)

- 64px tall, `--color-canvas`, 1px `--color-hairline` bottom border, not sticky.
  (The old black bar goes; DESIGN.md: nav stays light.)
- Left: wordmark "Paper Triage", `--type-label-md`, ink.
- Right cluster, gap `--space-sm`: `#model` ("Model: claude-…", `--type-caption`, muted, ellipsis at 32ch,
  hidden < 768px) then `#mock-label` (D32).

### [FE] D6 — Query band (`section.intro`)

- Left-aligned (not centered), max-width 880px inside the container. Padding-block `--space-xxl` top,
  `--space-xl` bottom.
- h1 `--type-display-md`, ink: "Find the papers worth reading."
- Lead uses `--type-reason` (16/1.5), muted, margin-top `--space-xs`:
  "Rank a pile of papers by relevance, with a skeptical critique of each."
- Form row, margin-top `--space-lg`: `display:flex; gap: var(--space-sm)`.
  - Input (`#query`, type search): flex 1, height 48px (DESIGN says 44; raised to match the button),
    padding `12px 16px`, `--type-body-md` at 16px size (prevents iOS zoom), `--radius-sm`,
    1px `--color-edge-input`. Focus: border `--color-info-border` plus D3 outline.
    Read-only while a triage is running.
  - Button (`#submit`): button-primary. bg `--color-primary`, text `--color-on-primary`, `--type-button`,
    padding `12px 24px`, min-height 48px, `--radius-lg`, `--shadow-button`. `:active` bg `--color-primary-active`.
    Disabled: bg `--color-primary`, opacity .55, `cursor: progress` while running.
- Help text below (`#query-help`), `--type-caption` weight 400, muted, margin-top `--space-xs`. Copy unchanged.
- Keyboard: `/` focuses `#query` when focus is not in an input or textarea (D35).

---

## 3. Results column

### [FE] D7 — Results header

- h2 `#results-heading`, `--type-title-lg`, ink. Copy: `Ranked papers for “<topic>”`; no topic → "Ranked papers".
- Under it, one `--type-caption` muted line (`#results-count`, new):
  `10 papers · sorted by relevance` / `15 papers · sorted by relevance within each batch` (after load more) /
  `Showing 8 stored papers from your last run` (on load from `/api/papers`). Append ` · 1 could not be processed`
  when failures exist.
- `#status` stays (role=status, aria-live=polite) but becomes `.sr-only`; it carries announcements only
  (D16, D20). Visible counts live in `#results-count`.

### [FE] D8 — Paper row (`li.paper`)

Ruled list, not boxed cards. Each `li.paper`: `display:grid; grid-template-columns: 72px minmax(0,1fr);
column-gap: var(--space-lg); padding-block: var(--space-lg); border-top: 1px solid var(--color-hairline)`.
First row has no top border. `tabindex="-1"`, `id="paper-<id>"`, `scroll-margin-top: var(--space-lg)`.

Body order (top to bottom), the at-a-glance part first:

1. **Title** `h3.paper__title`, `--type-title-sm`, ink, max 3 lines then natural wrap (no clamp; titles matter).
2. **Authors** `p.paper__authors`, `--type-caption` weight 400, muted, margin-top `--space-xxs`. Max 3 + "et al." (unchanged).
3. **Reason** `p.paper__reason`, `--type-reason`, `--color-body`, max-width `--measure`, margin-top `--space-sm`.
4. **Meta + links row** `div.paper__meta`, margin-top `--space-sm`, `display:flex; flex-wrap:wrap;
   align-items:center; gap: var(--space-xs) var(--space-md)`:
   left group: paper id (`--font-mono` 13px, muted) and flags (D11); right group, pushed with
   `margin-left:auto`: links (D10). On wrap the links drop to their own line, left-aligned.
5. **Disclosure** `details` (D12), margin-top `--space-sm`.

### [FE] D9 — Rank block (`div.rank`)

- Number: `--type-display-md`, ink, tabular-nums, e.g. `8`. Then `/10` in `--type-caption`, muted,
  `aria-hidden="true"`. Keep the existing `aria-label="Rank 8 of 10"` on the number.
- Meter under the number, margin-top `--space-xs`: 48×4px bar, `--radius-sm`, track `--color-surface-strong`,
  fill `--color-ink` at `width: calc(rank * 10%)`. `aria-hidden="true"` (the number carries the meaning).
- Failed paper: number `–` (en dash), `aria-label="No rank"`, no meter.
- No color tiers by score. Emphasis is size, not hue.

### [FE] D10 — Paper links (new)

- Two standalone text links in the meta row right group: **"arXiv page"** and **"PDF"**, each followed by an
  inline 12px "arrow up-right" SVG (`aria-hidden="true"`, `stroke: currentColor`, 1.5px).
- Style: `--type-caption`, `--color-link`, no underline (standalone, not in prose); `:active` `--color-link-active`.
  Hit area: `padding: 6px 4px; margin: -6px -4px` so the target is at least 24×24px.
- Attributes: `target="_blank" rel="noopener noreferrer"`,
  `aria-label="arXiv page: <title> (opens in new tab)"` / `aria-label="PDF: <title> (opens in new tab)"`.
  The label starts with the visible text (WCAG 2.5.3).
- URLs:
  - `source === "arxiv"`: abs `https://arxiv.org/abs/<paper_id>`; PDF `r.pdf_url` if present, else
    `https://arxiv.org/pdf/<paper_id>`. Encode with `encodeURIComponent` per path segment (old-style ids have `/`).
  - `source === "pdf"`: one link only, "PDF", to `r.pdf_url`. Until B1 ships the API has no `pdf_url`;
    then render no link for pdf-source rows.
  - Prefer `r.abs_url` / `r.pdf_url` from the API when present (B1).
  - Only set `href` when the URL parses with `new URL()` and protocol is `http:` or `https:`. Otherwise omit the link.
- Failed rows still get links (the user may want to read it themselves).

### [FE] D11 — Flags and failed rows

- Chip base `.flag`: `--type-chip`, padding `2px 8px`, `--radius-sm`.
  - "Abstract only": bg `--color-surface-strong`, text `--color-ink` (14:1).
  - "Failed": bg canvas, 1px `--color-coral` border, text `--color-coral`.
- Failed reason: `--type-reason`, `--color-coral`, copy = `r.error` or "This paper could not be processed."

### [FE] D12 — Summary and critique disclosure

- `summary` text: "Summary and critique" (or "Summary"). `--type-caption`, ink, with a 10px chevron SVG
  before it that rotates 90° when open (`--dur-base`, `--ease-out`; none under reduced motion).
  Hit area min 32px tall. Focus per D3.
- Open body: bg `--color-surface-soft`, `--radius-md`, padding `--space-md` `--space-lg`, margin-top `--space-xs`,
  max-width `--measure`.
  - Basis line first, `--type-caption` weight 400, muted.
  - Section h4s ("Summary", "Contributions", "Weak claims", "Overclaims", "Missing baselines"):
    `--type-caption`, ink, margin-top `--space-md`.
  - Body text `--type-body-md` with `line-height: var(--leading-prose)`, `--color-body`. Lists: 16px left indent,
    `list-style: disc`, `--space-xxs` between items. "Evidence gap:" prefix muted. "Not stated" muted, no italic.
  (Heading level: change the inner section headings from h3 to h4 so they nest under the h3 title.)

### [FE] D13 — Fetch notes (`#notes`)

- Shown above the list when `errors[]` is non-empty. Box: `--color-surface-soft`, 1px `--color-hairline`,
  `--radius-md`, padding `--space-md`.
- Heading line `--type-caption` ink: "Could not fetch 2 inputs". Items `--type-body-md`, body color:
  "`<input>`: <reason>" (input in `--font-mono`).

---

## 4. Running indicator (triage in progress)

FE-only. No progress endpoint exists, so the indicator shows **activity and elapsed time, never progress**:
no percentages, no progress bar, no stage checkmarks.

### [FE] D14 — Working card (`#working`, new; replaces the old status sentence)

Placement: in the results column directly under the results header, above the list. Shown 300ms after submit
(no flash in mock mode, which often returns faster).

```
┌ cream card, radius-md, padding 24 ──────────────────────────────────────┐
│ ✻  Summarizing abstracts…                                        1:42   │
│    Live runs take 1 to 3 minutes for up to 10 papers.                   │
└─────────────────────────────────────────────────────────────────────────┘
```

- Surface: `--color-cream`, `--radius-md`, padding `--space-lg`, no border, no shadow.
- Row 1 (`display:flex; align-items:center; gap: var(--space-sm)`):
  - **Glyph** `svg.working__glyph`, 20×20, `aria-hidden="true"`, `color: var(--color-ink)`.
    Eight rays at 45° steps, each a line from radius 3.5 to radius 9 around center (12,12) in a 24 viewBox,
    `stroke-width: 2.25; stroke-linecap: round; stroke: currentColor`.
  - **Verb** `span.working__verb`, `--type-title-sm`, ink, `aria-hidden="true"`.
  - **Elapsed** `span.working__time`, `margin-left:auto`, `--type-caption`, muted, tabular-nums, format `m:ss`
    (`0:07`, `1:42`, `12:03`), updated every 1s from `performance.now()` at submit. `aria-hidden="true"`.
- Row 2: **Note** `p.working__note`, `--type-body-md`, muted, padding-left 32px (aligns under verb).

Motion (default):
- Rays: `@keyframes ray { 0%,100% { opacity:.25 } 50% { opacity:1 } }`, 1.2s `ease-in-out` infinite,
  `animation-delay: calc(var(--i) * 150ms)` for ray i = 0..7 (a sweep, like a thinking pulse).
- Glyph wrapper: `@keyframes breathe { 0%,100% { transform: scale(.9) } 50% { transform: scale(1) } }`, 2.4s infinite.
- Verb change: old verb fades out `opacity 1→0, translateY(0→-4px)` over `--dur-fast`; new verb fades in
  `opacity 0→1, translateY(4px→0)` over `--dur-base`, `--ease-out`. Only `opacity` and `transform` animate.

### [FE] D15 — Copy and timing

Verb loop (pipeline vocabulary, rotates every 2.4s, loops; it is activity, not a step counter):
1. "Fetching papers…"  2. "Reading full text…"  3. "Summarizing abstracts…"  4. "Looking for weak claims…"
5. "Checking for missing baselines…"  6. "Weighing overclaims…"  7. "Ranking by relevance…"

ID-only or URL-only queries use the same loop. Note line by elapsed time:
- 0–89s: "Live runs take 1 to 3 minutes for up to 10 papers." In mock mode instead: "Mock mode: canned responses, usually a few seconds."
- 90–179s: "Still working. Papers are processed in parallel; results appear when all are ranked."
- ≥180s: "Taking longer than usual. The request has not failed; you can keep waiting."
Load-more runs (D19) use the same loop with note "Triaging 5 more papers. This can take a minute or two."

### [FE] D16 — Screen-reader behaviour

- Verb, glyph and timer are `aria-hidden`; they would be noisy in a live region.
- `#status` (polite) announces: on start "Triage started. This can take 1 to 3 minutes." (mock: "Triage started.");
  at each full minute "Still working, 2 minutes elapsed."; on success "10 papers ranked. Results below."
  (with ", 1 could not be processed" when relevant); on zero results "No papers found."
- Results section `aria-busy="true"` while running. `#working` gets `role="group" aria-label="Triage in progress"`.
- Errors go to `#alert` (role=alert), D31.

### [FE] D17 — Reduced motion

`@media (prefers-reduced-motion: reduce)`: rays static at full opacity, no breathe, no verb transition;
verb still changes but every 5s, instantly. Timer still ticks. Also disables D12 chevron rotation transition,
D20/D25 cream flash (replaced by the static treatments named there), and `scroll-behavior: smooth`.

### [FE] D18 — Busy state of the rest of the page

- `#submit`: disabled, label "Triaging…". `#query`: `readonly` (keep it focusable, keep its text).
- Existing list (from a previous run): stays rendered under the working card, `inert` + `opacity: .4`.
  On success it is replaced; on error it returns to normal (no `inert`, opacity 1).
- Chat stays usable during a run (it answers over already-stored papers).
- Load-more button (D19) is hidden during a full triage run.

---

## 5. "Load 5 more"

Requires B2. FE builds the UI against the B2 contract; until B2 lands, the button is not rendered.

### [FE] D19 — Placement and states

Placement: directly after the last `li.paper`, inside the results column, left-aligned, margin-top `--space-lg`.
Shown only when: the current run has a non-empty topic, the list has ≥1 row, and the source is not exhausted.
Hidden for ID/URL-only runs (topic `""`).

| State | Visual | Copy |
|---|---|---|
| idle | button-secondary: canvas bg, ink text, 1px `--color-edge-input`, `--radius-lg`, `--type-button`, padding `12px 24px`, min-height 48px. `:active` bg `--color-surface-soft`. Caption to the right (wraps below on mobile), `--type-caption` weight 400 muted. | Button "Load 5 more papers". Caption "Showing 10 papers for “<topic>”." |
| loading | Button disabled (`aria-disabled="true"`, edge `--color-border-strong`), label "Loading 5 more…" with the 16px glyph (D14 rays animation) before it. Under the button: compact working card (D14 variant `.working--compact`: cream, padding `--space-sm` `--space-md`, verb in `--type-body-md` weight 500, timer right, note hidden). | Verb loop as D15. |
| exhausted | Button removed. Caption only. | "No more papers for “<topic>”." (when the response had < 5 results) |
| error | Button back to idle look, label "Try again". Above it, `p.load-more__error`, `--type-body-md`, `--color-coral`, `role="alert"`. | "Could not load more papers. <detail>" (detail = API `detail` or "Could not reach the server. Check that the app is running.") |

### [FE] D20 — Appending, focus, announcement

- New rows append at the end; the list is **not** re-sorted (positions stay stable; each row shows its own rank).
  Before the first new row insert `li.batch-sep` (`aria-hidden="true"`): `--type-caption` muted, hairline above,
  text "Papers 11–15". Dedupe by `paper_id`: skip ids already in the list.
- New rows get `.paper--new`: background `--color-cream` fading to transparent over `--dur-flash`
  (`--ease-out`). Reduced motion: no fade; a static 3px `--color-cream` left inset (`box-shadow: inset 3px 0 0 var(--color-cream)`) for 5s, then removed.
- Focus: if focus was on the load-more button when the request finished, move focus to the first new
  `li.paper` (`tabindex=-1`, `scrollIntoView({block:"start"})`). Otherwise do not move focus.
- `#status` announces "Added 5 papers. 15 shown." / "Added 2 papers. No more for this topic."
- Update `#results-count` (D7) and the chat scope line (D23).

### [FE] D21 — Load-more request

Send exactly what B2 specifies. Planned shape (planner to confirm): `POST /api/triage`
`{"query": <original query>, "max_results": 5, "offset": <rows of this topic shown>}`; response = new results
only. Exhausted when `results.length < 5`. Errors use the same `{detail}` handling as triage.

---

## 6. Chat panel

### [FE] D22 — Panel layout

- `aside#chat`: bg `--color-surface-soft`, `--radius-lg`, padding `--space-lg`, 1px `--color-hairline` border.
- ≥1024px: `position: sticky; top: var(--space-lg); max-height: calc(100vh - 2 * var(--space-lg));`
  flex column: header (fixed), log (`flex:1; overflow-y:auto`), form (pinned bottom).
  <1024px: static, full width, after the results; log max-height 60vh.
- h2 `#chat-heading` "Ask your papers", `--type-title-md`, ink.
- Form: input (same spec as D6 input but height 44px, font 16px) + button-primary "Ask"
  (padding `10px 20px`, min-height 44px). Placeholder: "Ask about these papers".

### [FE] D23 — Scope line (`#chat-scope`, new)

Directly under the h2, `--type-caption` weight 400, muted. Makes the chat's data boundary explicit.

- With B3 (chat scoped to the shown papers): "Chatting about **10 papers** from this search." The count is
  `--type-caption` weight 500 ink. Count = shown rows with `status === "ok"`. Updates after load more and after a
  new triage. On stored load: "Chatting about 8 papers from your last run."
- Without B3 (current backend answers from the top-ranked stored papers, all topics):
  "Answers use only your stored papers, up to the top 10 by rank." Do not claim per-search scope until B3 ships.
- No papers stored: "Run a search first. Chat only answers from papers triaged here."; input and Ask button
  disabled (`disabled`, opacity .55).
- Second line, same style: "Questions outside these papers get a plain refusal, not a guess." (replaces old `#chat-help`; keep the id for `aria-describedby`).

### [FE] D24 — Turns (`ol#chat-log`, role=log)

No bubbles, no avatars. Each `li.turn`, separated by 1px hairline, padding-block `--space-md`.
- Question `p.turn__q`: `--type-label-md`, ink. Visually hidden prefix "You asked: ".
- Answer `div.turn__a`: `--type-body-md`, `line-height: var(--leading-prose)`, body color, margin-top `--space-xs`.
  Visually hidden prefix "Answer: ".
- Pending: `p.turn__pending` = compact glyph (16px, D14 rays) + "Reading your papers…" `--type-caption` muted.
  Reduced motion per D17.
- After each answer, focus returns to the input (existing behaviour). New turn scrolls into view with `block: "nearest"`.

### [FE] D25 — Citation chips

- Inline `[id]` markers in answers become chips `a.cite`: `--font-mono` 12px weight 500, ink text,
  bg `--color-surface-strong`, `--radius-sm`, padding `1px 6px`, no underline, no brackets (render the id only;
  `aria-label="Paper <id>: <title>"` when the title is known). `:active` bg `--color-hairline`.
- Below the answer, "Cited papers" (`--type-caption`, ink, margin-top `--space-sm`) then a list: chip + title
  (`--type-body-md`, body color, single line, ellipsis).
- Activation (click/Enter): scroll the row into view (`block: "start"`), focus it, and flash it:
  `.paper--cited` bg `--color-cream` → transparent over `--dur-flash`. Reduced motion: static
  `outline: 2px solid var(--color-info-border)` on the row for 2s (in addition to the focus ring).
  Keep `history.replaceState` to `#paper-<id>`.
- Id not in the current list (e.g. scrolled away by a new search): `span.cite--off`, same chip shape,
  bg transparent, 1px dashed `--color-edge-input`, muted text, `title="Not in the list shown"`. Not focusable.
- Dropped ids (`dropped_citations`): removed from text (unchanged behaviour).

### [FE] D26 — Refusal (`refused: true`)

Intentional, calm, not an error.
- `div.turn__a.turn__a--refused`: bg `--color-cream`, `--radius-md`, padding `--space-sm` `--space-md`, ink text.
- First line `--type-label-md` ink: "Not in these papers". Then the server's `answer` text (`--type-body-md`, prose leading).
- Last line `--type-caption` weight 400 muted: "Ask about something these papers cover, or run a new search above."
- No coral, no warning icon, no `role=alert` (the log's polite announcement is enough).

### [FE] D27 — Chat error (4xx/5xx/network)

- `p.turn__err`, `--type-body-md`, `--color-coral`, `role="alert"`: "Could not answer. <detail>".
- Inline button-secondary small (padding `6px 12px`, min-height 32px, `--type-caption`) "Ask again":
  resubmits the same question into the same turn. Disabled while pending.

### [FE] D28 — Chat empty state (papers exist, no turns yet)

Inside the log area, `--type-caption` weight 400 muted: "Try one of these:" then three button-secondary small
chips (stacked, full width, left-aligned text, `--type-body-md`):
"Which paper has the strongest evidence?" · "What baselines are missing across these papers?" ·
"What does the top-ranked paper claim?". Activating one fills `#question` and submits. Removed after the first turn.

---

## 7. Page states

### [FE] D29 — First run (nothing stored)

Replaces `#empty`. In the results column, no box, padding-block `--space-xl`:
- `--type-title-sm` ink: "Nothing triaged yet."
- `--type-reason` muted, max-width `--measure`: "Enter a topic, or paste arXiv IDs or PDF links. Each run fetches
  up to 10 papers, then summarizes, critiques and ranks them."
- "Examples" (`--type-caption` muted) + two button-secondary small chips: "retrieval augmented generation evaluation"
  and "2401.01234 2312.00752". Activating fills `#query` and focuses it (does not submit; a live run costs money).

### [FE] D30 — No papers found

Same layout as D29. Title: "No papers found for “<topic>”." Body: "Try broader keywords, or paste arXiv IDs or
PDF links." Focus stays on the input. `#status` announces "No papers found."

### [FE] D31 — Triage failure (`#alert`)

Full coral surface (DESIGN signature-coral-card, scaled to the tool):
- bg `--color-coral`, text `--color-on-primary`, `--radius-md`, padding `--space-lg`, `role="alert"`.
- Line 1 `--type-title-sm`: "Triage failed." Line 2 `--type-body-md` prose leading: detail text
  (API `detail`, or "Could not reach the server. Check that the app is running.").
- Button "Try again" (button-secondary-on-dark: canvas bg, ink text, `--radius-lg`, padding `10px 20px`),
  resubmits the last query. Focus ring on coral is white (D3).
- Previous list restored per D18.

### [FE] D32 — Mock-mode label (`#mock-label`)

- Badge in the nav: `--type-chip`, `--color-info` text, canvas bg, 1px `--color-info-border`, `--radius-sm`,
  padding `4px 8px`. Text "Mock mode". Desktop (≥1024px) adds a muted caption after the badge:
  "Canned responses, no model calls." (visible text, not a tooltip). Mobile: badge only; full sentence stays in
  `.sr-only`.
- Working-card note switches to the mock copy (D15).
- Status unknown (`/api/status` fails): show neither model nor badge (unchanged).

---

## 8. Responsive and accessibility

### [FE] D33 — Breakpoints (DESIGN.md table)

| Width | Changes |
|---|---|
| < 768px (mobile) | Container padding 16px. h1 `--type-title-lg`. Query form stacks: input full width, button full width below. Paper row columns `48px 1fr`, gap `--space-md`; rank number `--type-title-lg`; meter 32px wide. Meta row wraps, links on own line. Chat after results, not sticky. `#model` hidden. Load-more caption below button. |
| 768–1023px (tablet) | Container padding 24px. Single column; chat after results (full width). Form stays one row. |
| 1024–1439px (desktop) | Two-column workspace (D4), sticky chat. |
| ≥ 1440px (wide) | Same as desktop; container caps at 1280px; no type scaling. |

No horizontal scroll at 320px. Long ids/URLs: `overflow-wrap: anywhere` on `.paper__meta`, `.turn__a`, `#notes`.

### [FE] D34 — Contrast (computed, WCAG 2.2)

| Pair | Ratio | Use |
|---|---|---|
| ink #181d26 on canvas | 16.9:1 | titles |
| body #333840 on canvas | 11.8:1 | text |
| muted #41454d on canvas / surface-soft / cream | 9.6 / 9.2 / 8.0:1 | meta |
| link #1b61c9 on canvas | 5.8:1 | links |
| info #254fad on canvas | 7.5:1 | mock badge |
| coral #aa2d00 on canvas; white on coral | 6.8:1 | errors |
| ink on cream #f5e9d4 | 14.1:1 | working card, refusal |
| ink on surface-strong #e0e2e6 | 13.0:1 | chips |
| edge-input #8e939c on canvas | 3.09:1 | input/secondary edges (non-text 3:1) |
| info-border #458fff on canvas | 3.17:1 | focus ring |
| hairline #dddddd on canvas | 1.36:1 | decorative dividers only, never the sole boundary of a control |

### [FE] D35 — Keyboard

- Tab order: skip links → query → Triage → (results) per row: summary toggle, arXiv page, PDF → load more →
  chat suggestions → chat input → Ask. Citation chips are in tab order inside the log.
- `/` focuses `#query` (ignored when typing in an input). Enter submits both forms. Escape in `#query` clears
  it only when not running.
- Every interactive element ≥ 24×24px target (WCAG 2.5.8); buttons ≥ 44px tall except the small secondary
  chips (32px).
- Never trap focus; never move focus except: D20 (first new row, only if focus was on the button), D25 (cited row,
  user-initiated), chat input after answer (existing).

---

## 9. Backend needs (for the planner; FE must not fake these)

- **NEEDS-BE B1 — paper URLs in results.** Add `pdf_url` (already stored in `papers.pdf_url`) and optionally
  `abs_url` to every result item of `POST /api/triage` and `GET /api/papers`. Without it D10 works for arXiv rows
  only (URLs derived from the id) and pdf-source rows show no link.
- **NEEDS-BE B2 — load more.** Triage a further page for the same topic, excluding papers already returned.
  Proposed: `offset: int >= 0` on `POST /api/triage` (maps to arXiv API `start`), response holds only new papers,
  stored like a normal run. Needed by D19–D21.
- **NEEDS-BE B3 — chat scope.** `POST /api/chat` currently answers over `top_papers(chat_top_k)` across all stored
  papers, all topics. To make "Chatting about N papers from this search" true, accept `paper_ids: [str]`
  (optional) and restrict context to them. Until then FE uses the honest fallback copy in D23.

## 10. Out of scope

Cancel button (no server-side cancel), real progress stages (no endpoint), re-sorting across batches, dark
theme, any change to the textContent-only rendering rule in `app.js` (keep it: titles and model output are untrusted).
