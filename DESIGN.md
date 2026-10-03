---
version: 2.0
name: Paper-Triage-Carbon
description: "A light, square, dense tool interface for reading and triaging research papers. Built on IBM Carbon: white canvas, #f4f4f4 layers, charcoal ink, one IBM Blue accent, 1px rules, no shadows except overlays. IBM Plex Sans and Plex Mono (vendored woff2) at weights 400 and 600. Colour is reserved for actions, focus, errors, refusals and the three PDF highlight fills."

colors:
  primary: "#0f62fe"
  primary-hover: "#0050e6"
  primary-active: "#002d9c"
  on-primary: "#ffffff"
  secondary: "#393939"
  secondary-hover: "#474747"
  secondary-active: "#6f6f6f"
  link: "#0f62fe"
  link-hover: "#0043ce"
  link-active: "#002d9c"
  ink: "#161616"
  ink-muted: "#525252"
  ink-subtle: "#6f6f6f"
  ink-disabled: "#8c8c8c"
  ink-inverse: "#ffffff"
  canvas: "#ffffff"
  surface-1: "#f4f4f4"
  surface-2: "#e0e0e0"
  surface-hover: "#e8e8e8"
  surface-selected: "#e0e0e0"
  surface-inverse: "#161616"
  well: "#e0e0e0"
  border-subtle: "#e0e0e0"
  border-strong: "#8d8d8d"
  border-page: "#c6c6c6"
  focus: "#0f62fe"
  focus-inset: "#ffffff"
  error: "#da1e28"
  error-hover: "#b81921"
  error-active: "#750e13"
  error-surface: "#fff1f1"
  info: "#0f62fe"
  info-surface: "#edf5ff"
  selection: "#d0e2ff"
  overlay: "rgba(22, 22, 22, 0.5)"
  hl-yellow: "#ffde66"
  hl-mint: "#9fe0c0"
  hl-peach: "#ffc29e"
  rank-track: "#e0e0e0"
  rank-fill: "#161616"
  cite-surface: "#e0e0e0"
  cite-surface-active: "#c6c6c6"

typography:
  heading-lg:
    fontFamily: IBM Plex Sans
    fontSize: 32px
    fontWeight: 400
    lineHeight: 40px
    letterSpacing: 0
  heading-md:
    fontFamily: IBM Plex Sans
    fontSize: 24px
    fontWeight: 400
    lineHeight: 32px
    letterSpacing: 0
  heading-sm:
    fontFamily: IBM Plex Sans
    fontSize: 20px
    fontWeight: 400
    lineHeight: 28px
    letterSpacing: 0
  heading-xs:
    fontFamily: IBM Plex Sans
    fontSize: 16px
    fontWeight: 600
    lineHeight: 24px
    letterSpacing: 0
  prose:
    fontFamily: IBM Plex Sans
    fontSize: 16px
    fontWeight: 400
    lineHeight: 24px
    letterSpacing: 0.16px
  body:
    fontFamily: IBM Plex Sans
    fontSize: 14px
    fontWeight: 400
    lineHeight: 20px
    letterSpacing: 0.16px
  body-compact:
    fontFamily: IBM Plex Sans
    fontSize: 14px
    fontWeight: 400
    lineHeight: 18px
    letterSpacing: 0.16px
  body-emphasis:
    fontFamily: IBM Plex Sans
    fontSize: 14px
    fontWeight: 600
    lineHeight: 18px
    letterSpacing: 0.16px
  label:
    fontFamily: IBM Plex Sans
    fontSize: 12px
    fontWeight: 400
    lineHeight: 16px
    letterSpacing: 0.32px
  mono:
    fontFamily: IBM Plex Mono
    fontSize: 12px
    fontWeight: 400
    lineHeight: 16px
    letterSpacing: 0.32px
  numeral-lg:
    fontFamily: IBM Plex Sans
    fontSize: 32px
    fontWeight: 400
    lineHeight: 40px
    letterSpacing: 0
  numeral-md:
    fontFamily: IBM Plex Sans
    fontSize: 24px
    fontWeight: 400
    lineHeight: 32px
    letterSpacing: 0

rounded:
  none: 0px
  xs: 2px
  pill: 9999px
  round: 50%

spacing:
  xxs: 4px
  xs: 8px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 48px

sizes:
  control-sm: 32px
  control-md: 40px
  control-lg: 48px
  nav-h: 48px
  rail-w: 240px
  panel-w: 384px
  page-max: 1312px
  measure: 72ch

components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.body-compact}"
    rounded: "{rounded.none}"
    height: "{sizes.control-md}"
    padding: 0 16px
  button-secondary:
    backgroundColor: "{colors.secondary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.body-compact}"
    rounded: "{rounded.none}"
    height: "{sizes.control-md}"
    padding: 0 16px
  button-outline:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-compact}"
    rounded: "{rounded.none}"
    height: "{sizes.control-md}"
    padding: 0 16px
  button-ghost:
    backgroundColor: transparent
    textColor: "{colors.link}"
    typography: "{typography.body-compact}"
    rounded: "{rounded.none}"
    height: "{sizes.control-md}"
    padding: 0 16px
  button-danger-outline:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.error}"
    typography: "{typography.body-compact}"
    rounded: "{rounded.none}"
    height: "{sizes.control-md}"
    padding: 0 16px
  icon-button:
    backgroundColor: transparent
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    size: "{sizes.control-md}"
  text-field:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink}"
    typography: "{typography.body-compact}"
    rounded: "{rounded.none}"
    height: "{sizes.control-md}"
    padding: 0 16px
  tag:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    height: "{sizes.control-sm}"
    padding: 0 12px
  tag-pressed:
    backgroundColor: "{colors.surface-inverse}"
    textColor: "{colors.ink-inverse}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    height: "{sizes.control-sm}"
  cite-chip:
    backgroundColor: "{colors.cite-surface}"
    textColor: "{colors.ink}"
    typography: "{typography.mono}"
    rounded: "{rounded.xs}"
    padding: 0 4px
  notification-error:
    backgroundColor: "{colors.error-surface}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: 16px
  notification-info:
    backgroundColor: "{colors.info-surface}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: 16px
  top-nav:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-compact}"
    height: "{sizes.nav-h}"
  side-panel:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: 16px 24px
  popover:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: 8px
---

# DESIGN.md: Paper Triage

This file is the single visual source of truth for Paper Triage. It covers tokens, type, components,
states and the v3 Library and Preview patterns. Builders need no other document for visual decisions.
Product truth (what the app does, copy, behaviour) lives in PRODUCT.md, the spec and the v3 brief.
Nothing here changes behaviour, copy, DOM order or ARIA.

## 1. Character

Paper Triage is a tool for one skeptical researcher. That person reads for an hour or more at a time:
ranked reasons, critiques, PDF pages and grounded answers. The interface is **Carbon-derived: light,
square, dense, quiet.**

- White canvas, `#f4f4f4` layers, charcoal ink. One accent: IBM Blue `#0f62fe`, used for primary
  actions, links, focus and selected-tab rules. No other hue appears in chrome, except error red, the
  info-blue refusal surface and the three highlight fills drawn on PDF pages.
- Square corners on everything you click or type into. Pills only for tags and badges. Circles only for
  highlight swatches.
- Depth comes from surface change and 1px rules. A shadow is allowed only on overlays (the selection
  popover and the bottom sheet).
- Hierarchy comes from size and the 400/600 weight pair, never from colour. Metadata recedes through a
  real grey ladder.
- Calm motion: short colour fades, one disclosure rotation, one sheet slide. Every motion has a
  reduced-motion equivalent that keeps the meaning.

**Never:** gradients, glass, glow, AI sparkle, drop shadows on cards, rounded buttons, a second brand
colour, weight 300/500/700, all-caps tracked labels, colour as the only signal.

## 2. Colour

Implement each token as a CSS custom property named `--color-<token>`. Highlight tokens are
`--hl-<colour>`. Set `color-scheme: light` on `:root`.

### 2.1 Neutrals and text

| Token | Hex | Use | Contrast |
| --- | --- | --- | --- |
| `ink` | #161616 | Titles, prose, answers, control labels | 18.1:1 on canvas, 16.5 on surface-1, 13.7 on surface-2 |
| `ink-muted` | #525252 | Secondary text: authors, scope lines, inactive tabs and nav, counts | 7.8 / 7.1 / 5.9 |
| `ink-subtle` | #6f6f6f | Tertiary text: captions, helper text, placeholders, "/10", timestamps | 5.0 on canvas, 4.6 on surface-1. **Never on surface-2** (3.8). |
| `ink-disabled` | #8c8c8c | Disabled labels only (WCAG-exempt). Never for real content. | 3.4 |
| `ink-inverse` | #ffffff | Text on primary, secondary, inverse and error fills |  |
| `canvas` | #ffffff | Page, nav, toolbar, rows, popover, sheet |  |
| `surface-1` | #f4f4f4 | Layer: chat panel, Preview side panel, critique, working card, text fields on canvas |  |
| `surface-2` | #e0e0e0 | Saved state, rank track, cite chip, selected rail item |  |
| `surface-hover` | #e8e8e8 | Hover fill for ghost, outline and icon buttons, rail items, find hits, tabs |  |
| `surface-selected` | #e0e0e0 | Current rail item, pressed or active icon buttons |  |
| `surface-inverse` | #161616 | Pressed tag |  |
| `well` | #e0e0e0 | Background behind PDF pages |  |
| `border-subtle` | #e0e0e0 | Dividers between rows, turns, highlight items; nav and toolbar bottom rule. Decorative only. | 1.3 |
| `border-strong` | #8d8d8d | Edges of controls: field bottom rule, outline buttons, unpressed tags, swatch edge, dashed off-chip | 3.3 on canvas, 3.0 on surface-1 (meets 1.4.11) |
| `border-page` | #c6c6c6 | 1px edge of PDF pages in the well; left edge of the Preview side panel |  |

The ladder **ink, ink-muted, ink-subtle** is the whole text hierarchy. Do not add greys. On
`surface-2` use only `ink` or `ink-muted`.

### 2.2 Accent and interaction

| Token | Hex | Use |
| --- | --- | --- |
| `primary` | #0f62fe | Primary button fill, selected-tab underline, current rail-item bar, link text |
| `primary-hover` / `primary-active` | #0050e6 / #002d9c | Primary button hover / press |
| `secondary` / `-hover` / `-active` | #393939 / #474747 / #6f6f6f | Secondary (charcoal) button |
| `link` / `link-hover` / `link-active` | #0f62fe / #0043ce / #002d9c | Text links and ghost buttons. `link-hover` is also the ghost label colour on hover fill (6.4:1 on `surface-hover`). |
| `focus` | #0f62fe | Every focus indicator (5.0 on canvas, 3.8 on well) |
| `focus-inset` | #ffffff | Inner ring inside focused filled buttons |
| `selection` | #d0e2ff | `::selection` background in the app (ink text, 13.8:1). Inside the PDF text layer: `color-mix(in srgb, var(--color-primary) 25%, transparent)` with transparent text. |

Primary on `surface-1` is 4.55:1, so blue text may sit on layers. On `surface-hover`, switch ghost
labels to `link-hover`.

### 2.3 Status

| Token | Hex | Use |
| --- | --- | --- |
| `error` | #da1e28 | Error text and icons, 3px rule on error notifications, danger outline buttons, invalid field rule. 5.0 on canvas, 4.55 on error-surface and surface-1. |
| `error-hover` / `error-active` | #b81921 / #750e13 | Danger outline button hover fill / press fill (white text) |
| `error-surface` | #fff1f1 | Error notification background |
| `info` | #0f62fe | 3px rule on info notifications, mock badge outline and text |
| `info-surface` | #edf5ff | Info notification background (refusals, "no PDF, no chat"), cited and new row flash |

Success and warning tokens are not part of this product. If a future state needs one, use Carbon
success `#198038` (text) and warning `#f1c21b` (fill only, never text, and never near the PDF, because
it reads as Highlight Yellow).

### 2.4 PDF highlights

Highlights are content drawn on white PDF pages. They do not belong to the theme.

| Token | Hex | Name in UI and data | Fill on white | Ink on fill |
| --- | --- | --- | --- | --- |
| `hl-yellow` | #ffde66 | Yellow | 1.32:1 | 13.7:1 |
| `hl-mint` | #9fe0c0 | Mint | 1.51:1 | 12.0:1 |
| `hl-peach` | #ffc29e | Peach | 1.56:1 | 11.6:1 |

- Draw each rect as an **opaque fill** with `mix-blend-mode: multiply` on the highlight layer (no alpha).
  Black glyphs stay black and the fill reads at full strength. Yellow is at the lightest point a yellow
  can sit and still read as yellow.
- Radius `xs` (2px) on rects.
- A highlight that failed to save keeps its fill plus a 1px dashed `error` outline.
- A flashed highlight (jumped to from the list) gets a 2px `focus` outline that fades over `dur-flash`.
- Swatches (popover and list) are filled circles with a 1px `border-strong` edge. The name is always
  printed next to list swatches, so colour is never the only signal.
- `forced-colors: active`: no fill, 2px `Highlight` outline (`forced-color-adjust: none` on the layer).

### 2.5 Score and citation

| Token | Hex | Use |
| --- | --- | --- |
| `rank-track` | #e0e0e0 | Meter track |
| `rank-fill` | #161616 | Meter fill (13.7:1 against the track) |
| `cite-surface` | #e0e0e0 | Cite chip background (ink text 13.7:1) |
| `cite-surface-active` | #c6c6c6 | Cite chip pressed; hover on chips that are buttons or links |

There are no score colour bands. The numeral and the meter length carry the score.

## 3. Typography

### 3.1 Families and files

- **IBM Plex Sans** 400 and 600 for everything except ids. **IBM Plex Mono** 400 for paper ids, page refs
  and cite chips. Licence: SIL OFL 1.1.
- Weights 300, 500 and 700 are not shipped. Set `font-synthesis: none` on `html` so the browser never
  fakes them.
- Vendored woff2 lives in `src/paper_triage/static/vendor/fonts/`. Next to the files go the OFL text
  (`LICENSE-IBM-Plex.txt`) and a `README` that records sources and versions. Never use a CDN or a
  network URL.

| File (rename to this on vendoring) | Source | Bytes |
| --- | --- | --- |
| `plex-sans-latin-400.woff2`, `-600` | `@fontsource/ibm-plex-sans@5.3.0` `files/ibm-plex-sans-latin-{400,600}-normal.woff2` | 22,588 / 24,252 |
| `plex-sans-latin-ext-400.woff2`, `-600` | same package, `latin-ext` | 15,980 / 16,448 |
| `plex-sans-greek-400.woff2`, `-600` | `@ibm/plex-sans@1.1.0` `fonts/split/woff2/` Greek split, Regular / SemiBold | 8,832 / 9,072 |
| `plex-mono-latin-400.woff2` | `@fontsource/ibm-plex-mono@5.3.0` `files/ibm-plex-mono-latin-400-normal.woff2` | 14,708 |
| `plex-mono-latin-ext-400.woff2` | same package, `latin-ext` | 13,348 |

Total is about 125 KB. Only the Latin files (about 62 KB) load on a typical page. `latin-ext` loads
for names like Dvořák or Łukasz, and Greek loads for α or β in titles. Greek in Mono falls back to the
system mono.

### 3.2 @font-face

Declare the faces in `static/vendor/fonts/plex.css`, linked from `index.html` before `app.css` with a
relative href. That file keeps `app.css` free of `@font-face`. Copy the `unicode-range` values verbatim
from Fontsource's `latin.css` and `latin-ext.css` for the same package version. Greek is
`U+0370-03FF`. Pattern:

```css
@font-face {
  font-family: "IBM Plex Sans";
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url("plex-sans-latin-400.woff2") format("woff2");
  unicode-range: /* Fontsource latin range */;
}
/* repeat for 600, for latin-ext and greek, and for "IBM Plex Mono" 400 latin + latin-ext */

@font-face {            /* metric-matched fallback, limits layout shift during swap */
  font-family: "IBM Plex Sans Fallback";
  src: local("Arial"), local("Helvetica Neue"), local("Helvetica");
  ascent-override: 102.5%;
  descent-override: 27.5%;
  line-gap-override: 0%;
  size-adjust: 100%;       /* tune once by eye against Plex; keep ascent/descent */
}
```

Stacks (`--font-sans`, `--font-mono`):

```css
--font-sans: "IBM Plex Sans", "IBM Plex Sans Fallback", system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
--font-mono: "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
```

Set `font-variant-numeric: tabular-nums` on `body`. Plex has `tnum`, so ranks, counts, page numbers
and timers never jitter.

### 3.3 Roles

Implement each role as a `font` shorthand custom property (`--type-<role>`). Apply the role's tracking
as `letter-spacing` wherever the role is used.

| Role | Spec | Used for |
| --- | --- | --- |
| `heading-lg` | 400 32/40, 0 | View titles at >= 768px (`Triage papers`, Library directory name) |
| `heading-md` | 400 24/32, 0 | View titles below 768px; results heading (`Ranked papers`) |
| `heading-sm` | 400 20/28, 0 | Panel titles (Chat), Preview not-saved and failed card titles |
| `heading-xs` | 600 16/24, 0 | Paper titles in rows, empty-state titles, Preview toolbar title |
| `prose` | 400 16/24, +0.16px | Rank reason, intro lead, empty-state body. Measure <= 72ch |
| `body` | 400 14/20, +0.16px | Wrapped UI text: critique, chat answers, notes, quotes, error lines, notification body, find hits, confirm text |
| `body-compact` | 400 14/18, +0.16px | Single-line UI: buttons, nav and view links, tabs, fields, selects, rail items, toolbar |
| `body-emphasis` | 600 14/18, +0.16px | Selected tab and view, current rail item, chat question, notification title, find match, section heads in critique |
| `label` | 400 12/16, +0.32px | Meta: authors, counts, helper, scope lines, tags, PDF status, captions, "/10", badge |
| `mono` | Plex Mono 400 12/16, +0.32px | Paper ids, cite chips, page refs |
| `numeral-lg` / `numeral-md` | 400 32/40 and 24/32, tabular | Rank numeral at >= 768px and below |

Text fields use 16px text below 768px (this stops iOS zoom) and `body-compact` above. Use sentence
case everywhere. No uppercase labels.

## 4. Space, size, layout

- **Grid:** 4px. Spacing tokens `--space-xxs` 4 · `xs` 8 · `sm` 12 · `md` 16 · `lg` 24 · `xl` 32 ·
  `xxl` 48. Put more space above a heading than below it.
- **Control heights:** `--control-sm` 32 (tags, row Directory select, text buttons, chips row),
  `--control-md` 40 (default buttons, fields, toolbar, icon buttons), `--control-lg` 48 (Triage topic
  field and its submit button). On `pointer: coarse`, raise `control-sm` hit areas to 40 with padding
  (the visual stays 32).
- **Breakpoints (product, not Carbon):** mobile < 768, tablet 768 to 1023, desktop >= 1024. Page
  padding (`--pad-x`) is 16 / 24 / 48.
- **Shell:** nav 48px (`--nav-h`). Content container max `--page-max` 1312px, centred. Preview runs
  full width under the nav.
- **Triage (>= 1024):** two columns, list `minmax(0,1fr)` and chat `--panel-w` 384px, gap 48. The chat is
  sticky (top 24px, max-height `100vh - 48px`). Below 1024, the chat stacks under the list.
- **Library (>= 1024):** rail `--rail-w` 240px plus list, gap 48. The rail is sticky with a right 1px
  `border-subtle` rule. Below 1024, a Directory select replaces the rail.
- **Preview:** a column at `100dvh - nav`: toolbar, optional find row, then the work area. At >= 1024
  with the panel open, the work area is well `minmax(0,1fr)` plus side panel 384px. Below 1024, the
  panel becomes the bottom sheet.
- **Rows:** a paper row is a grid with the rank column (56px mobile, 72px >= 768) and the body. Column
  gap 16 / 24. Padding-block `md` 16 (mobile) and `lg` 24 (>= 768). A 1px `border-subtle` top rule
  goes on every row except the first.

## 5. Shape and depth

- Radius `none` on buttons, fields, selects, icon buttons, cards, notifications, panels, sheet, popover
  and the meter.
- Radius `xs` (2px) on cite chips and highlight rects. Radius `pill` on tags and the mock badge.
  Radius `round` on swatches.
- Depth: canvas, then `surface-1` layer, then `surface-2` for selected or saved. Fields alternate
  against their layer: `surface-1` fields on canvas, `canvas` fields on `surface-1` panels.
- `--shadow-overlay: 0 2px 6px rgba(0, 0, 0, 0.3)` on the selection popover and the bottom sheet only.
  The sheet backdrop is `overlay`.

## 6. Motion

| Token | Value | Use |
| --- | --- | --- |
| `--dur-fast` | 110ms | Colour and background changes (hover, press, toggle) |
| `--dur-moderate` | 240ms | Disclosure chevron, sheet in, row collapse, verb swap |
| `--dur-flash` | 1600ms | Cited-row, new-row and page/highlight flash fade |
| `--ease-standard` | cubic-bezier(0.2, 0, 0.38, 0.9) | Default |
| `--ease-entrance` | cubic-bezier(0, 0, 0.38, 0.9) | Sheet in, verb in |
| `--ease-exit` | cubic-bezier(0.2, 0, 1, 0.9) | Row collapse, verb out |

- Animate only `opacity`, `transform`, `background-color`, `outline-color` and `color`. The row
  collapse uses opacity plus a `grid-template-rows` collapse, not `height`.
- Working loops (rays at 1.2s, glyph breathe at 2.4s) stay as they are.
- `prefers-reduced-motion: reduce`: no smooth scroll, no transitions or keyframes. The flash becomes a
  static 2px `focus` outline (cited row) or a static `info-surface` background (new rows), the working
  glyph is static with rays at full opacity, and the sheet appears without sliding. Meaning never
  depends on motion.

## 7. Focus, hover, accessibility

- **Focus (one system):** `:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }`.
  Fields, selects, icon buttons, tabs, rail items and outline or ghost buttons use `outline-offset: -2px`
  (inset, Carbon). Filled buttons (primary, secondary, pressed tag) use
  `outline: 2px solid var(--color-focus); outline-offset: -2px; box-shadow: inset 0 0 0 3px var(--color-focus-inset);`.
  Focus on rows that take focus programmatically (`tabindex="-1"` targets) shows no ring.
- **Hover:** only inside `@media (hover: hover)`. Use the hover tokens above, with `dur-fast` colour
  transitions. Hover is never the only way to discover an action.
- **Contrast:** text >= 4.5:1, large numerals >= 3:1, control edges and meter >= 3:1. Every token pair in
  section 2 is pre-checked. A new pairing must be checked before use.
- **Non-colour signals:** pressed tag shows a check glyph; saved shows a filled bookmark plus the text
  `Saved`; the current rail item has a 3px bar plus weight 600; selected tabs use weight 600 plus a
  2px underline; highlight names are printed; errors carry text, not colour alone.
- **Targets:** >= 40px for toolbar and panel controls, >= 32px visual for tags and inline actions, 48px
  for the Triage submit.
- **Forced colours:** controls keep a 1px `ButtonText` or `CanvasText` border. Fills are dropped.
  Focus uses `Highlight`. The meter fill uses `CanvasText`. Notifications, chips, panels and the sheet
  get a 1px `CanvasText` border.

## 8. Components

States listed: default, hover, active (press), focus, disabled, plus product states. Implement focus
per section 7.

### 8.1 Buttons

- **Primary** (`button-primary`): `primary` fill, white `body-compact`, 40px (48px in the Triage form),
  16px inline padding, radius 0. Hover `primary-hover`, press `primary-active`. Busy: label kept,
  `cursor: progress`, opacity 0.6. Disabled: `surface-2` fill, `ink-disabled` text. Use: Triage submit,
  Ask (both chats), Create (directory), Save note, Rename. At most one primary per region.
- **Secondary** (`button-secondary`): charcoal fill. Use: `Load 5 more`, `Try again` inside error
  notifications.
- **Outline** (`button-outline`): canvas fill, 1px `border-strong`, `ink` text. Hover `surface-hover`,
  press `surface-selected`. Use: Save toggle, Open preview, Cancel, Keep, New directory, directory
  actions, chat starters (full width, label start-aligned, 40px min, wraps to 2 lines).
- **Ghost / text button** (`button-ghost`, `.text-btn`): no fill, `link` text. Hover: `surface-hover`
  fill and `link-hover` text. Disabled (`aria-disabled="true"`): `ink-disabled`, no hover. Use: Export
  notes, Open PDF in new tab, Go to, Edit note, Delete (highlight), Add note, Show more, Find. Inline
  text buttons in prose (`Try again` in the row PDF status) are underlined with a 3px offset.
- **Danger outline**: canvas fill, 1px `error` border, `error` text. Hover `error-hover` fill with
  white text, press `error-active`. Use: Remove (unsave confirm), Delete directory confirm.
- **Icon button**: 40×40, transparent, `ink` 16px glyph, radius 0. Hover `surface-hover`, press
  `surface-selected`. Disabled: glyph `ink-disabled`. Each one has an `aria-label`.
- **Joined control (Highlight split):** an outline button plus an outline select. They share one
  1px edge (`margin-left: -1px`), both 40px, radius 0. The focused part rises (`z-index: 1`).

### 8.2 Fields

- **Text field / search / textarea:** fill `surface-1` on canvas (`canvas` inside `surface-1`
  panels). No side or top border. A 1px `border-strong` bottom rule. 40px (48px for the Triage
  topic). Inline padding 16px (12px in the toolbar page input). Placeholder `ink-subtle`.
  Focus: 2px inset `focus` outline. Invalid (`aria-invalid="true"`): 2px inset `error` outline,
  error text below in `body` `error`, linked by `aria-describedby`. Read-only during a run:
  `cursor: progress`. Disabled: `ink-disabled` text, bottom rule `border-subtle`.
- **Select:** same box as the field. `appearance: none` with a 16px chevron (inline SVG data URI,
  `ink`) at right 12px, and 40px right padding. Long options ellipsize. The select never widens past
  its container.
- **Note editor:** textarea in `body`, min 4 lines, vertical resize. The counter (`label`,
  `ink-subtle`, tabular) sits right; at the limit it turns `error`.

### 8.3 Navigation

- **Top nav:** canvas, 48px, 1px `border-subtle` bottom. Brand `body-emphasis` `ink`. View links
  (Triage, Library with count): `body-compact` `ink-muted`, 48px tall, 12px padding. Current view
  (`aria-current="page"`): `ink`, `body-emphasis`, 2px `primary` bottom rule. Hover: `ink` text with
  `surface-hover` fill. Count: `label`, tabular, `ink-subtle`; hidden at 0.
- **Model label:** `label` `ink-subtle`, ellipsized at 32ch, shown at >= 768px.
- **Mock badge:** pill, 1px `info` border, `info` text in `label`, canvas fill, 2px 8px padding. The
  explanatory line beside it is `label` `ink-muted` at >= 1024px and screen-reader-only below.
- **Skip links:** hidden until focused, then canvas with a 1px `border-strong` edge and `body-compact`
  text, top left.

### 8.4 Triage view

- **Intro band:** canvas, 1px `border-subtle` bottom rule, padding 32/24 (48/32 at >= 1024). Title is
  `heading-md` (or `heading-lg` at >= 768). Lead is `prose` `ink-muted`. Form: 48px field plus 48px
  primary button in a row at >= 768; the button goes full width below. Help line in `label`
  `ink-subtle`.
- **Results header:** `heading-md` plus a `label` `ink-muted` count.
- **Paper row:**
  - Rank column: numeral (`numeral-md`, or `numeral-lg` at >= 768) in `ink`, then `/10` in `label`
    `ink-subtle` on the same baseline. Below it, the meter: 48×4px (32px mobile), `rank-track`, fill
    width = rank × 10% in `rank-fill`, radius 0.
  - Head: title (`heading-xs` `ink`) and, at the end, the Save toggle and Open preview (outline,
    32px). Below 768px the buttons wrap under the title.
  - Authors: `label` `ink-muted`. Reason: `prose` `ink`, max 72ch, 12px top gap. A failed reason
    uses `error` text.
  - Meta line: id in `mono` `ink-muted`; flags (square: `label` on `surface-2`, 2px 8px;
    the failed flag is `error` text with a 1px `error` border on canvas); external links as ghost text
    (`label` size, `link`) pushed to the end.
- **Critique disclosure:** a summary row (32px, `body-emphasis` `ink`, chevron rotating 90° over
  `dur-moderate`). The panel is `surface-1`, radius 0, padding 16/24, max 72ch. Section heads are
  `body-emphasis`; items are `body` with disc bullets; the basis line and "why" lines are `label`
  `ink-muted`; "none" is `ink-subtle`.
- **Save toggle:** outline button, min-width 7.75rem so the width does not jump. Glyph before the label.
  Unsaved: outline bookmark plus `Save`. Saved (`aria-pressed="true"`): `surface-2` fill, no border,
  filled bookmark plus `Saved`. Busy: opacity 0.6 with `cursor: progress`. The row error below is
  `body` `error`.
- **Inline confirm** (unsave, delete directory): the text (`body` `ink`, full width), then the danger
  outline button and an outline `Keep` / `Cancel`. 12px gap, 12px margin below.
- **Batch separator:** `label` `ink-muted` with a 1px `border-subtle` top rule and 24px top padding.
  New rows flash `info-surface` to transparent over `dur-flash`.
- **Load more:** secondary button with an optional working glyph, a `label` caption, and an error line
  above it.
- **Previous results during a new search:** they stay at full opacity and fully interactive (save,
  open preview, critique, links, chat) until the new results replace them. No overlay, no dimming, no
  `pointer-events` block, no `inert`. Dimming would also drop text below 4.5:1. The working card sits
  in normal flow above the list and is the only sign that a run is in progress. Its live-region text
  carries the state for screen readers.

### 8.5 Working, notes, empty, failure

- **Working card:** in normal flow, never an overlay. `surface-1`, radius 0, padding 24 (compact: 12/16). The glyph is in `ink`. The verb
  is `heading-xs` (compact: `body-emphasis`). The timer is `label` `ink-subtle`, right-aligned and
  tabular. The note is `body` `ink-muted`, indented 32px.
- **Fetch notes:** `surface-1`, padding 16. The title is `body-emphasis`, items are `body`, and code is
  `mono`.
- **Error notification** (triage failure, library load error, PDF unavailable): `error-surface`, 3px
  `error` left rule, padding 16 (16 left after the rule). The title is `body-emphasis` `ink`, the detail
  `body` `ink`, and actions are a secondary `Try again` plus ghost links. Links inside use `link`.
- **Info notification** (chat refusal, "no PDF, no chat", not-saved preview note, no-text-layer page
  note): `info-surface`, 3px `info` left rule, padding 12/16. The title is `body-emphasis` `ink`, the
  body `body` `ink`, and the hint is `label` `ink-muted`. A refusal must look deliberate and calm, never
  like an error.
- **Empty state:** title `heading-xs` `ink`, body `prose` `ink-muted` (max 72ch), example label
  `label` `ink-muted`, example chips as outline buttons at 32px.

### 8.6 Chat (Triage and Ask this paper)

- **Panel:** `side-panel` (`surface-1`, radius 0, no border, padding 24 on Triage, 16/24 in Preview).
  The title is `heading-sm`. Scope lines are `label` `ink-muted`, with `<strong>` in `ink` 600.
- **Turns:** separated by 1px `border-subtle` rules with 16px padding. The question is
  `body-emphasis` `ink`. The answer is `body` `ink`. Pending: `label` `ink-muted` with the rays glyph.
  Error: `body` `error` plus an outline `Try again`.
- **Cite chip:** `mono` on `cite-surface`, radius 2px, 0 4px padding, inline-block, wraps anywhere.
  As a link or button: hover and press use `cite-surface-active`. The off variant (id not in stored
  papers): transparent with a 1px dashed `border-strong` edge and `ink-muted` text. Page refs (`p.3`)
  in Ask this paper use the same chip. Lines with chips use line-height 1.9 so chips do not collide.
- **Sources list:** the head is `body-emphasis`. Each item is a chip plus the title in `body` `ink`,
  ellipsized.
- **Starters:** a label in `label` `ink-muted`, then outline buttons stacked with 8px gaps.
- **Form:** a field (canvas on the panel) plus a primary `Ask`, 40px, 8px gap. In Preview the form is
  sticky at the bottom on the panel colour.
- **Cited row flash:** the cited paper row flashes `info-surface` to transparent over `dur-flash`.

### 8.7 Library view

- **Head:** directory name in `heading-md` / `heading-lg`, with directory actions (outline, 32px) beside
  it. The rename form is a field plus primary `Rename` plus outline `Cancel`.
- **Rail (>= 1024):** the label is `label` `ink-muted`. Items are 32px min (40 on coarse pointers),
  `body-compact` `ink-muted`, 12px padding, the name ellipsized and the count in `label` tabular
  `ink-subtle`. Hover: `surface-hover`. Current (`aria-current="true"`): `surface-selected` fill,
  `ink` text, weight 600, 3px `primary` bar on the left edge (inset, no layout shift). `New directory`
  is a full-width outline button. The new-directory form stacks: field full width, then the buttons.
- **Directory select (< 1024):** labelled select, full width.
- **Filter bar:** a title search field (40px, max 480px) with a visible `label` label. Tags follow.
- **Tag:** pill, 32px, 1px `border-strong`, canvas, `label` `ink`, with the count in `ink-muted`.
  Hover: `surface-hover`. Pressed: `surface-inverse` fill, white text and count, a 12px check glyph
  before the name. When clamped to 2 rows, a ghost `Show all` follows.
- **Saved row:** same grammar as the Triage row. Meta adds:
  - `Ranked for "…"` in `label` `ink-muted` under the authors;
  - PDF status in `label`: `ink-muted` for ready and downloading, `error` for unavailable, followed by
    an underlined text button;
  - saved date and highlight count in `label` `ink-subtle`;
  - a Directory select (32px, max 20rem, its label visually hidden at >= 768).
  Row actions are Open preview (outline) and Remove (ghost, which opens the danger confirm).
- **Manage panel (< 1024):** `surface-1`, padding 16. Items are a name (`body` `ink`, ellipsized) plus
  ghost actions.
- **Row removal:** opacity to 0 plus a row collapse over `dur-moderate` (`ease-exit`).

### 8.8 Preview view

- **Toolbar:** canvas, 1px `border-subtle` bottom, padding 12px by `--pad-x`. Row 1: back (ghost with a
  chevron, `Library`), the title (`heading-xs` `ink`, ellipsized; 2-line clamp below 768), then Export
  notes and Open PDF in new tab (ghost). Row 2 (`#pv-controls`): pager (icon button, page field 56px
  wide with `of N` in `label` `ink-subtle`, icon button), zoom (icon buttons plus select), Find
  (ghost), Highlight joined control, and `Highlights and chat` (outline, below 1024 only). Every control
  is 40px. Groups are 8px apart internally and 24px between groups. Below 1024 the existing wrap and
  order rules stay; only the visuals change.
- **Find row:** canvas, 1px `border-subtle` bottom. A search field (40px, max 480px), a count
  (`label` `ink-muted`), a ghost close. Results: list max 15rem (10rem below 1024). Each hit is 40px
  min, `body` `ink`, with the match in `body-emphasis`. Hover `surface-hover`.
- **Well:** `well` fill, padding 16. Pages are canvas with a 1px `border-page` edge and no shadow,
  centred, 16px apart. The page label (before render) is `label` `ink-subtle`, centred. The jump
  flash is a 2px `focus` outline fading over `dur-flash`. Text selection uses the text-layer selection
  colour (section 2.2).
- **Not-saved, opening, downloading and failed states:** a centred card column, max 640px, on canvas.
  Failed uses the error notification. Opening and downloading are `label` `ink-muted`, centred.
- **Selection popover:** canvas, radius 0, `shadow-overlay`, 1px `border-subtle`, padding 8. It holds
  three 32px swatches (8px apart) and a ghost `Add note`. The last-used swatch has a 2px `ink` ring
  offset 2px. It never covers the toolbar: it flips below the selection near the well top.
- **Side panel (>= 1024):** `surface-1`, a 1px `border-page` left edge, width 384, scrolls on its own.
  Tab bar: tabs `body-compact` `ink-muted`, 40px, 16px apart, 1px `border-subtle` bar. The selected
  tab is `body-emphasis` `ink` with a 2px `primary` underline. The count is `label` tabular.
  **Default tab is `Ask this paper`** on every preview open (panel and sheet). The chat stays lazy:
  showing the tab loads nothing until the first question.
- **Highlight item:** 12px padding-block, with a 1px `border-subtle` rule between items. Line 1: a 12px
  swatch (circle, 1px `border-strong` edge), the colour name, a dot, and `Page n` (all `label`
  `ink-muted`), then a ghost `Go to` at the end. Quote: `body` `ink`, a 3px left rule in the highlight
  colour, 12px left padding, 3-line clamp with `Show more`. Note: `body` `ink`, line breaks preserved.
  Actions are ghost text buttons plus a colour select (32px). A deleted item is a `body` `ink-muted`
  line with `Undo`.
- **Ask this paper (default tab):** the same chat components as Triage (8.6) inside the panel. Idle shows starters;
  nothing loads until the first question. "No PDF" is an info notification and the form is disabled.
- **Bottom sheet (< 1024):** a native `<dialog>`, canvas, 85dvh, full width, radius 0,
  `shadow-overlay`, `overlay` backdrop. The header row holds tabs on the left and a 40px `Close` icon
  button on the right, over a 1px `border-subtle` rule. Slides up over `dur-moderate` with
  `ease-entrance`. Fields inside use `surface-1`.

## 9. CSS implementation rules

- Tokens live in `:root` in `app.css`, one custom property per token above (`--color-*`, `--hl-*`,
  `--type-*`, `--space-*`, `--radius-*`, `--control-*`, `--dur-*`, `--ease-*`, `--shadow-overlay`, layout
  sizes). Do not declare unused tokens. Do not use literal hex values outside `:root`, except `CanvasText` and
  similar system colours in forced-colors blocks.
- Vanilla CSS only: no framework, no preprocessor, no build step, no network. `color-mix()`,
  `:focus-visible`, `dvh`, `:has()` are allowed (evergreen browsers only).
- Class names, DOM structure, ids and ARIA stay as built. This system is applied through CSS. The only
  markup addition is the `plex.css` link in `index.html`.

## 10. Do and don't

### Do

- Keep blue scarce: primary action, links, focus, selected tab and current-item bars, info rules.
- Use surface change and 1px rules for structure. Put rows on canvas and panels on `surface-1`.
- Pair every state colour with text or a glyph.
- Keep long text at <= 72ch and use `prose` for reasons.

### Don't

- Round buttons, fields or panels, or use pills anywhere except tags and the badge.
- Use `ink-subtle` on `surface-2`, or `ink-disabled` for content.
- Use yellow, mint or peach anywhere except the highlight trio.
- Add shadows to anything that is not an overlay.
- Use weights other than 400 and 600, or display sizes above 32px.

## 11. Known gaps and provenance

- **Light only.** Dark mode is out of scope. If added later, derive it from Carbon Gray 100 (canvas
  `#161616`, layer `#262626`, ink `#f4f4f4`, muted `#c6c6c6`, focus `#ffffff`, link `#78a9ff`). PDF pages
  stay white and highlights stay unchanged. Ship it via `light-dark()` and `prefers-color-scheme`, with
  no toggle.
- The fallback font metrics (section 3.2) are a starting point. Tune `size-adjust` once by eye.
- Provenance: derived from IBM Carbon via the VoltAgent awesome-design-md IBM extract (MIT). The verbatim
  source is in `docs/design/ibm-DESIGN.source.md`. Product adaptations (text ladder fix: `ink-subtle`
  #6f6f6f replaces the source's #8c8c8c, which is 3.4:1; body-compact 14/18; notifications; tags;
  hover; motion; control heights; highlights; rank; cite chips; fonts) follow
  `docs/design/redesign-recommendation.md`. The previous Airtable-based spec is kept in
  `docs/design/DESIGN.airtable.md`.
