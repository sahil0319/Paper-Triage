# Brief v3: Save, Library, Tags, Directories, PDF Preview

Status: ready for planner + frontend-builder. Author: designer, 2026-10-03.
Sources: DESIGN.md (active spec, Airtable), PRODUCT.md, current `src/paper_triage/static/` (read only),
`specs/001-paper-triage/contracts/api.md`, `docs/design/brief-v2-redesign.md` (v2 tokens and deviations still apply).
Aligned with `docs/research/v3-library-preview.md` (vendored pdf.js, thin custom `viewer.js`, canvas + TextLayer,
no pdf.js editor UI; highlights stored as page + fractional rects; chat cites `[p.N]`). The v3 spec was in progress.
The viewer spec stays renderer-agnostic beyond "canvas + selectable text layer per page".

Implementable items are tagged `[FE] Ln`. Backend needs are tagged `NEEDS-BE Bn` (section 9).
Open decisions the builder must not invent are in section 10.

> **Rev 2 (2026-10-03, user decisions).** Minimal changes; everything else unchanged.
> 1. Per-paper chat transcript is page-only, never stored. It resets on reload or when the preview closes (L20, B7, copy).
> 2. Highlight colours: 3 (Yellow, Mint, Peach). Unchanged.
> 3. Chat with no PDF: disabled with a reason. No abstract fallback (L20, sec 10.6 closed).
> 4. Unsave always confirms (result card and Library) and deletes the local PDF, highlights and notes (L4, L6, L13, B2, copy).
> 5. Modern evergreen browsers only: native `<dialog>`, `dvh`, `:focus-visible`, `inputmode` used without fallbacks (sec 10.11).
> 6. Direct PDF URLs can be saved like arXiv papers (sec 10.10 closed).

---

## 0. Job, mode, direction

- **Who:** the same single researcher. v2 cut a pile down to a few papers. v3 keeps those few and lets the user read
  them in place: highlight, note, and ask questions of one paper.
- **Mode:** Operate. The Library is a filing tool and the Preview is a reading tool. Scanability and keyboard reach
  outrank expression.
- **Direction:** unchanged Airtable-for-tools world from v2. White canvas, ink type at weight 400/500, hairline rules,
  near-black primary button used once per view, flat surfaces. Color voltage stays on full surfaces: cream (working,
  refusal), coral (failure). One new use of the signature palette: **highlight colors** (yellow, mint, peach) inside
  the PDF, which are content marks rather than UI accents.
- **Anti-goals:** card grid of saved papers, folder-tree file manager, drag-only interactions, floating chat bubble,
  AI sparkle iconography, chat that loads before the user asks, color as the only signal for highlight or state.

### Deviations (in addition to v2 section 0)

| DESIGN.md says | Brief does | Why |
|---|---|---|
| Signature pastels are demo-card surfaces only | Yellow, mint, peach are highlight fills in the PDF (multiply blend) | Highlights are content, not chrome. No new hue added. |
| Minimal shadows | Selection popover and mobile sheet use `--shadow-button` | Floating surfaces over a PDF need a separation edge. Same token, no new shadow. |
| `topic-filter-rail` 240px | Directory rail 240px at >= 1024px only | Token used as written; below 1024px it becomes a native select. |
| No hover | Still none. Default, active, focus-visible, disabled, `aria-pressed`, `aria-current` only. | Follows DESIGN.md. |

---

## 1. Shell and navigation

### [FE] L1 — View switcher in the global nav
- Add `<nav class="views" aria-label="Views">` inside `.global-nav__inner`, directly after `.brand`.
  Two links: `Triage` (`href="#/"`) and `Library` (`href="#/library"`) followed by a count `<span class="views__count">12</span>`.
- Active link: `aria-current="page"`, ink text, 2px ink bottom bar flush with the nav's bottom hairline.
  Inactive: `--color-muted` text. Type `--type-body-md` at weight 500. Min target 44px tall, padding 0 12px.
- The count uses `--type-chip`, `--color-muted`, no pill. Hidden when 0. Updates after every save/unsave.
- Links, not ARIA tabs: each view is a URL, so Back/Forward work.

### [FE] L2 — Hash routes, one page
| Hash | View | Visible regions |
|---|---|---|
| `#/` (default, also empty hash) | Triage | `.intro`, `.workspace` (results + chat) as today |
| `#/library` (+ query params `dir`, `tags`, `q`) | Library | `#library` section only |
| `#/library/paper/<paper_id>` | Preview | `#preview` section only |
- Switching view: hide others with `hidden`, never re-fetch triage results; triage state stays in memory.
- On route change: set `document.title` (`Paper Triage`, `Library · Paper Triage`, `<paper title> · Paper Triage`),
  move focus to the view's `h1`/`h2` (`tabindex="-1"`), and announce through the existing `#status` region.
- Library filter state lives in the hash (`#/library?dir=network&tags=diffusion%20models,video&q=attn`) so Back from
  Preview restores it. Returning from Preview focuses that paper's `Open` button.
- Skip links are per view: Triage keeps the two existing ones. Library: `Skip to saved papers`. Preview: `Skip to PDF`,
  `Skip to highlights and chat`.
- Mock badge and model label stay in the nav in every view.

---

## 2. Results card: Save

### [FE] L3 — Placement
Wrap `.paper__title` in `.paper__head` (flex, `align-items: flex-start`, gap `--space-md`). The Save button sits at the
right of the title, `flex: none`. Same position at every width. Failed rows (`status: failed`) get no Save button.

### [FE] L4 — Save toggle button
`<button type="button" class="btn btn--secondary btn--small save" aria-pressed="false">`
with a 16px bookmark glyph (inline SVG, `aria-hidden`) and visible text. Accessible name comes from visible text plus
`aria-describedby` pointing at the row title id, so screen readers hear "Save, toggle button, not pressed, <title>".

| State | Visible text | Glyph | Style | Attributes |
|---|---|---|---|---|
| Unsaved | `Save` | outline bookmark | `btn--secondary` (edge `--color-edge-input`) | `aria-pressed="false"` |
| Saving | `Saving…` | outline bookmark, static | same, opacity 0.7 | `aria-disabled="true"`, `aria-busy="true"` |
| Saved | `Saved` | filled bookmark | bg `--color-surface-strong`, border transparent, ink text | `aria-pressed="true"` |
| Removing | `Removing…` | filled, static | saved style, opacity 0.7 | `aria-disabled="true"` |
| Error | `Save` (or `Saved` if unsave failed) | as state | as state | error line below, see L5 |

- Activating `Saved` never unsaves directly: it always opens the L6 confirm (Rev 2).
- Already-saved papers render as Saved in new results and after reload (NEEDS-BE B1).
- No spinner; text change carries the state. Width must not jump: set `min-width` to fit `Removing…`.
- Announce on success via `#status`: `Saved to Library.` / `Removed from Library.`

### [FE] L5 — Save error
Below `.paper__meta`, `<p class="row-error" role="alert">` in `--color-coral`, `--type-body-md`, line-height 1.5:
`Could not save. <reason>` or `Could not remove from Library. <reason>`. Cleared on the next attempt. Focus stays on
the button.

### [FE] L6 — Unsave confirm (always)
Replace the button area with an inline group (`role="group"`, `aria-label="Confirm removal"`):
text `Remove from Library? This deletes the saved PDF and 3 highlights with their notes.` (no annotations:
`Remove from Library? This deletes the saved PDF.`) + `Remove` (secondary, coral text and coral
edge) + `Keep` (secondary). Focus moves to `Keep`. Esc = Keep. Same component is used in the Library row (L14).

---

## 3. Library view

### [FE] L7 — Layout
```
>= 1024px
+-------------------------------------------------------------------------------+
| nav: Paper Triage   Triage  [Library 12]                         Mock mode    |
+------------------+------------------------------------------------------------+
| DIRECTORIES      | Library                         h1 title-lg               |
| > All saved   12 | 4 of 12 saved papers · Unsorted               caption       |
|   Unsorted     3 | [ Filter tags and titles ______________ ]  Clear filters   |
|   network      4 | Tags  [diffusion models 5] [x video generation 2] [rag 3]  |
|   computer v.  2 |       Show all 14 tags                                      |
|   final year   3 | ---------------------------------------------------------- |
|                  |  8/10  Title of paper                       [Open preview] |
| + New directory  |        Authors                                              |
|                  |        Tags: diffusion models, video generation             |
|                  |        2401.01234 · Saved 3 Oct · PDF ready · 3 highlights |
|                  |        Directory [network v]   Remove from Library          |
|                  |        > Critique                                           |
+------------------+------------------------------------------------------------+
```
- Container is the existing `.container` (max 1280). Grid: `240px minmax(0,1fr)`, gap `--space-xxl`.
- Rail: `topic-filter-rail` token: canvas bg, `--type-body-md`, right edge 1px `--color-hairline`, sticky top
  `--space-lg`.
- Main column header: `h1` "Library" in `--type-title-lg` (display-md at >= 768 to match Triage h1 scale),
  count line in `--type-caption` muted.
- 768 to 1023px: rail removed; directory control becomes L10b above the filter row. Main column full width.
- < 768px: same as tablet; row actions wrap (L13).

### [FE] L8 — Directory rail (>= 1024px)
- `<nav aria-label="Directories">` with a `<ul>` of buttons. Order: `All saved`, `Unsorted`, then user directories
  A to Z (case-insensitive).
- Item: full-width button, min-height 40px, padding 8px 12px, radius `--radius-sm`, name left (ellipsis at one line,
  full name in `title`), count right in `--type-chip` muted, `tabular-nums`.
- Active item: `aria-current="true"`, bg `--color-surface-strong`, ink text weight 500. Inactive: `--color-body`.
- Section label above the list: `Directories` in `--type-caption` muted (not a heading level that breaks outline;
  use `<h2 class="rail__label">`).
- Bottom: `+ New directory` as `btn--secondary btn--small`, full width.

### [FE] L9 — Create, rename, delete directory
- **Create:** `New directory` swaps itself for an inline form: text input (height 40px, `maxlength=40`, label
  `New directory name`, placeholder `e.g. final year thesis`) + `Create` (secondary small) + `Cancel` (text button).
  Enter submits, Esc cancels and returns focus to `New directory`. On success the new directory is selected and
  announced: `Directory "network" created.`
- **Rename and delete** live in the main column header when a user directory is selected (never for All saved or
  Unsorted): after the h1 (which then shows the directory name, e.g. `network`), two small secondary buttons `Rename`
  and `Delete directory`.
  - Rename: h1 is replaced by the same inline form prefilled, button `Save`. Focus input with text selected.
  - Delete: inline confirm below header: `Delete "network"? Its 4 papers move to Unsorted.` `Delete` (coral text +
    edge) / `Keep`. Focus `Keep`. After delete, select Unsorted and announce `Directory deleted. 4 papers moved to Unsorted.`
- **Validation** (shown under the input, `--color-coral`, `aria-describedby` on input, `aria-invalid="true"`):
  `Enter a name.` / `"Network" already exists.` (case-insensitive) / `Names can be up to 40 characters.` /
  `Could not save the directory. <reason>`.
- Reserved names: `Unsorted`, `All saved` count as existing.

### [FE] L10 — Tag and title filter bar
Order inside `.lib-filters`: filter input row, then tag bar.

**a. Filter input.** `type="search"`, label (visible, caption muted) `Filter`, placeholder `Tags or titles`,
height 44px, max-width 480px. `/` focuses it in Library view (extend existing D35 handler). Esc clears it.
Behavior, deterministic:
1. Papers shown = papers in current directory AND having every selected tag AND whose title contains the text
   (case-insensitive). Empty text = no title filter.
2. Tag chips shown = tags whose name contains the text, plus every selected tag (selected chips never disappear).
3. Selecting a chip while text is present clears the text (the text was used to find the tag) and announces the new
   count.
Filtering runs on input (debounce 150ms), client-side over the loaded library.

**b. Tag bar.** `<div role="group" aria-labelledby="tags-label">` with label `Tags` (caption muted).
Each tag is a toggle `<button class="tag" aria-pressed>`:
- Unpressed: canvas bg, 1px `--color-edge-input`, ink text, `--type-chip`, radius `--radius-sm`, min-height 32px,
  padding 4px 10px, count after the name in muted (`diffusion models 5`).
- Pressed: bg `--color-primary`, text `--color-on-primary`, count also on-primary, a 12px check glyph before the
  name (so state is not color-only).
- Order: count desc, then A to Z. Counts reflect the current directory, not the filtered result.
- Overflow: show two rows max (`max-height` + `overflow: hidden`), then a text button `Show all 14 tags` /
  `Show fewer tags` with `aria-expanded`. Pressed tags always render in the first row (sort pressed first).
- Multi-select = AND. Count line reads `4 of 12 saved papers` and, when tags are pressed, the line below the bar reads
  `Showing papers tagged diffusion models and video generation.` (caption muted).

**c. Clear filters.** Text button `Clear filters` at the end of the input row. Visible only when text or any tag is
active. Clears text and tags, keeps the directory. Focus moves to the filter input. Announce `Filters cleared. 12 saved papers.`

**d. No tags at all:** tag bar replaced by caption `No tags yet. Tags are the search keywords that found each paper.`

### [FE] L10b — Directory control below 1024px
Native `<select>` labelled `Directory` (visible caption label) above the filter input, options
`All saved (12)`, `Unsorted (3)`, `network (4)`… Next to it a small secondary button `Manage directories` that opens
a disclosure panel (`aria-expanded`) holding the same list as L8 with per-item `Rename` and `Delete` buttons and the
`New directory` form. Same copy and validation as L9.

### [FE] L11 — Saved paper row
Reuse the `.paper` row grid (rank column 48/72px + body). Content, in order:
1. `.paper__head`: title (`--type-title-sm`) + `Open preview` (`btn--secondary btn--small`) on the right.
   The Library view has no primary button; nothing on this page is a single final action.
2. Authors (caption muted).
3. Tags line: `Tags: diffusion models, video generation` in caption muted. Plain text, not buttons (too many tab stops).
   If none: omit.
4. Meta row (`.paper__meta`): paper id (mono) · `Saved 3 Oct` · PDF status (L12) · `3 highlights` (omit when 0) ·
   existing external links (`abs`, `PDF`) right-aligned.
5. Rank block shows the snapshot rank with a caption under the meter: `for "diffusion models"` (the topic it was
   ranked against; omit for item runs). Rank reason paragraph stays under authors as in Triage.
6. Actions row: `Directory` native select (label visible at < 768, `sr-only` above) committing on change; text button
   `Remove from Library`.
7. Existing critique disclosure (`details`) unchanged.
- Sort: most recently saved first. (No sort control in v3.)

### [FE] L12 — PDF status in the row
| State | Text | Style |
|---|---|---|
| Downloading | `Downloading PDF…` | caption muted, no animation |
| Ready | `PDF ready` | caption muted |
| Unavailable | `PDF unavailable` + text button `Try again` | coral text; button link-colored, underlined |
| No PDF source | `No PDF` | caption muted (direct-PDF rows always have a source; arXiv always has one) |
While any visible row is Downloading, refresh statuses every 3s; stop when none are (NEEDS-BE B3).
Status changes are announced politely only when the row has focus within it, to avoid noise.

### [FE] L13 — Move and remove
- Move: select change saves at once. Disabled while saving. Success announces `Moved to network.` If the current
  directory filter no longer includes the paper, the row collapses out (200ms height+opacity; instant under reduced
  motion) and focus moves to the next row's `Open preview`, or to the h1 if none. Error: revert select, row error
  `Could not move. <reason>`.
- Remove: `Remove from Library` always confirms in Library (row disappears): L6 group, text
  same copy as L6. After removal focus goes to next row, announce
  `Removed from Library.`

### [FE] L14 — Library states
| State | Content |
|---|---|
| Loading (> 300ms) | Caption `Loading your library…` in the list area. No skeletons. |
| Load error | Coral `.alert` card: title `Could not load your library.`, detail `<reason>`, button `Try again` (`btn--on-dark`). |
| Empty library | `.empty`: title `Nothing saved yet.` body `Save papers from your ranked results. Each saved paper keeps its rank, critique, tags and a local PDF.` + secondary button `Go to Triage` (`#/`). Rail still shows All saved 0 / Unsorted 0 and New directory. |
| Empty directory | title `No papers in network.` body `Move a saved paper here with its Directory menu.` |
| No filter matches | title `No saved papers match.` body `Try fewer tags or a shorter filter.` + `Clear filters`. |

---

## 4. Preview view

### [FE] L15 — Layout
```
>= 1024px  (height: 100dvh - nav; viewer and panel scroll independently)
+-------------------------------------------------------------------------------------+
| [< Library]  Title of the paper (one line, ellipsis)            Open PDF in new tab  |
| [<] Page [ 3 ] of 14 [>]   [-] [Fit width v] [+]   [Highlight v]                     |
+-----------------------------------------------------------+-------------------------+
|  surface-strong well                                       | [Highlights 5] [Ask]    |
|      +---------------------------+                         |  panel (384px)          |
|      |  white page, 1px hairline |                         |                         |
|      |  canvas + text layer      |                         |                         |
|      +---------------------------+                         |                         |
+-----------------------------------------------------------+-------------------------+
```
- Preview is wider than the reading column: it uses the full viewport width with `--pad-x` gutters, not the 1280 cap.
- Grid `minmax(0,1fr) var(--chat-w)` (384px), gap 0, panel has 1px hairline left edge, bg `--color-surface-soft`.
- Toolbar: canvas bg, 1px hairline bottom, sticky. Row 1 = back + title + external link; row 2 = viewer controls.
  At >= 1280 both rows merge into one 56px row when it fits (FE may keep two rows; do not truncate controls).
- Viewer well: bg `--color-surface-strong`; pages centered, gap `--space-md` between pages, white with 1px
  `--color-hairline`, no shadow.
- < 1024px: panel leaves the grid. Toolbar gains button `Highlights and chat` (secondary small) that opens the panel
  as a modal sheet (L22). Viewer is full width.

### [FE] L16 — Toolbar controls
- **Back:** `button-icon-circular` style is 40px; use a secondary small button with left chevron + text `Library`
  (text keeps it clear). Goes to the stored Library hash.
- **Title:** `--type-label-md`, ink, one line, ellipsis, full title in `title`. This is the view's `h1`
  (`tabindex="-1"`, focus target on entry).
- **Page nav:** `Previous page` and `Next page` icon buttons (40px, `aria-label`), number input (width 4ch, `inputmode=numeric`,
  label `Page`, `aria-describedby` = "of 14"), text `of 14`. Enter or blur jumps; out-of-range clamps and the input
  shows the clamped value. Disabled ends at page 1 and last page. Current page updates as the user scrolls (page with
  the largest visible area wins).
- **Zoom:** `Zoom out` / `Zoom in` icon buttons + native select: `Fit width` (default), `Fit page`, `50%`, `75%`,
  `100%`, `125%`, `150%`, `200%`. Buttons step through the percentage list. Zoom keeps the current page's top in view.
- **Find:** icon button `Find in paper` (40px) opens L24. `aria-keyshortcuts="f"` inside the viewer region.
- **Export notes:** text button `Export notes` in toolbar row 1, before `Open PDF in new tab` (L23).
- **Highlight button:** `Highlight` split control: main button applies the last-used color to the current selection
  (disabled with `aria-disabled` when there is no selection inside the text layer); a small adjoining select or menu
  button `Highlight color` chooses Yellow / Mint / Peach. This is the keyboard path to highlighting (L18).
- **Open PDF in new tab:** existing `.ext-link` style, points at the local file URL.
- Keyboard inside the viewer region only (never globally, never Ctrl/Cmd combos): `+` zoom in, `-` zoom out,
  `0` fit width, `n`/`p` next/previous page, `f` find. Declare with `aria-keyshortcuts` on the matching buttons.

### [FE] L17 — Viewer region and page structure
- Viewer scroll container: `role="region"`, `aria-label="PDF pages"`, `tabindex="0"` so arrows/PageUp/PageDown scroll it.
- Each page: `<section class="pdf-page" aria-label="Page 3">` holding canvas (`aria-hidden="true"`), text layer
  (real selectable text, read by screen readers), highlight layer (`aria-hidden`; the panel list is the accessible copy).
- Pages outside the viewport ± 2 pages are placeholders sized to the page aspect ratio, bg canvas, caption
  `Page 7` centered in muted. Render on approach; no per-page spinner.
- Text selection color inside the PDF stays the global `::selection` (cream).

### [FE] L18 — Highlight creation
- Mouse/touch: when a selection ends inside one page's text layer, show the **selection popover** above the selection
  (below if near the top edge): canvas bg, 1px `--color-edge-input`, radius `--radius-md`, `--shadow-button`,
  padding 8px. Contents: three 32px round swatches (`rounded.full`, 1px edge, fill = color) with
  `aria-label="Highlight yellow"` etc., then text button `Add note`. Last-used color swatch carries a 2px ink ring.
- Clicking a swatch creates the highlight; `Add note` creates it in the last-used color and opens its note editor
  in the panel (switches panel to Highlights; on < 1024 opens the sheet).
- Popover closes on Esc, on selection collapse, on scroll beyond 200px. Esc returns focus to the viewer region.
- Keyboard: select text with caret browsing or Shift+arrows, then the toolbar `Highlight` button (L16) or the popover.
  When the popover opens from a keyboard selection, it does not steal focus; `Tab` from the viewer reaches it first.
- Selections across pages: highlight only the part on the page where the selection started, and say so in status:
  `Highlighted the part on page 3. Select across pages one page at a time.`
- After creation announce `Yellow highlight added on page 3.`
- Colors: Yellow `--color-yellow` (#f4d35e), Mint `--color-mint` (#a8d8c4), Peach `--color-peach` (#fcab79).
  Highlight rects use the color at 0.45 alpha with `mix-blend-mode: multiply` so text stays ink-dark.
- Highlight layer has `pointer-events: none` and multiply blend (research). Clicks reach highlights through a thin
  transparent hit layer (or skip click-to-select and rely on the list; the list is the required path).
- Clicking an existing highlight in the PDF selects its panel item (scroll into view, 2px `--color-info-border`
  outline for 1.6s, static outline under reduced motion) and switches the panel to Highlights.

### [FE] L19 — Highlights panel (tab 1)
- Panel tabs: real ARIA tabs (`role="tablist"`, two `role="tab"`, arrow keys move, Home/End). Labels
  `Highlights 5` and `Ask this paper`. Selected tab: ink text + 2px ink underline; other: muted.
- List `<ol aria-label="Highlights">` ordered by page, then top position. Item (`.hl`), padding 12px 0, hairline between:
  - Line 1: 10px square swatch with 1px edge + color name text `Yellow` (caption muted) · `Page 3` · right side
    text button `Go to` (`aria-label="Go to highlight on page 3"`).
  - Quote: the selected text, `--type-body-md`, line-height 1.5, ink, left 2px rule in the highlight color, clamp to
    3 lines with `Show more` text button when clamped.
  - Note: if present, `--type-body-md` body color, preserved line breaks. Else text button `Add note`.
  - Actions row (text buttons, caption size): `Edit note` · `Color` (native select Yellow/Mint/Peach) · `Delete`.
- `Go to` scrolls the viewer so the highlight sits 25% from the top, then outlines it (1.6s pulse; reduced motion:
  instant jump, static outline 2s). On < 1024 it closes the sheet first. Focus moves to the viewer region.
- **Note editor:** inline in the item. `<textarea>` label `Note`, 3 rows, `maxlength=500`, counter `420/500` appears
  from 400 chars (caption muted; coral at 500). Buttons `Save note` (secondary small) and `Cancel` (text). Cmd/Ctrl+Enter
  saves, Esc cancels. Empty note on save = delete note (not the highlight).
- **Delete highlight:** immediate, then the item becomes a one-line row `Highlight deleted.` + `Undo` text button for
  8s (Undo re-creates it with the same note). Focus moves to `Undo`; after 8s to the next item.
- Empty: title `No highlights yet.` body `Select text in the PDF, then pick a color. Add a short note to any highlight.`
- Save failure for any annotation write: item-level coral line `Could not save. <reason>` + `Try again`; the highlight
  stays drawn with a dashed 1px `--color-coral` outline until saved.

### [FE] L20 — Ask this paper (tab 2), lazy
Scope line at the top (caption muted): copy `pv.chat.scope` (section 8).

**Idle (not started)** — the default; no network request of any kind for chat until the first submit:
- Cream-free, quiet block: title `Chat is off until you ask.` (`--type-label-md`) and body
  `Your first question reads this paper, so it takes longer than the rest.` (caption muted).
- Three starter buttons (`btn--suggest` style): `What is the main claim?`, `What baselines are compared?`,
  `What are the stated limitations?`. Clicking one sends it (counts as the first message).
- Input + `Ask` primary button (the Preview's single primary button), same form as Triage chat, label
  `Question about this paper`, placeholder `Ask about this paper`.

**Starting (first question in flight):** turn shows the question, then the pending line with the existing ray glyph:
`Reading this paper. The first answer takes longer.` After 20s add `Still reading. Long papers take up to a minute.`
Ask button disabled, input stays editable.

**Ready:** later questions show the pending line `Reading this paper…`. Answers use `.turn__a`.
- `[p.N]` tokens in the answer render as `.cite` chips with text `p. 4` (button, not link; `aria-label="Go to page 4"`).
  Activating jumps the viewer to that page and outlines the page for 1.6s (reduced motion: static outline 2s).
  On < 1024 the sheet closes first.
- Sources line under each answer: `Pages: p. 4, p. 7`.
- **Refusal:** identical component to Triage (cream `.turn__a--refused`): title `Not in this paper`, body = model text,
  hint `Ask about something this paper covers.`
- **Error:** existing `.turn__err` pattern: `Could not answer. <reason>` + `Ask again`.
  If the first question fails during start, the panel returns to Idle copy with the error above the input; the
  question text is restored into the input.
- **PDF not ready / unavailable:** input disabled; message `Chat needs the PDF text. It is not ready yet.` or
  `Chat needs the PDF text, and this PDF is unavailable.` No abstract fallback (Rev 2).
- Transcript is page-only, never stored (Rev 2). Kept in memory while this preview is open; closing the preview
  (Back, nav, another paper) or reloading clears it and the panel returns to Idle. Say so in the scope line (copy
  `pv.chat.scope`). Once a transcript exists, add caption under the log: `This chat clears when you close the preview
  or reload.` `[arXiv:ID]` tokens, if any, render as plain `.cite` chips without a jump.
- Mock mode: idle and flow identical; canned answers cite `p. 1`. Nav badge already labels the mode.

### [FE] L21 — Preview PDF states (viewer area)
| State | Viewer area | Panel |
|---|---|---|
| Opening (local file, > 300ms) | Caption `Opening PDF…` centered in the well | Highlights list loads; Ask idle |
| Downloading | Cream `.working` card centered, glyph + `Downloading the PDF…`, note `You can read the critique below while you wait.` and the saved critique rendered below the card in `.critique` style. Poll status (B3); render when ready, announce `PDF ready.` | Highlights tab disabled-ish empty copy `Highlights are available once the PDF is ready.`; Ask shows not-ready message |
| Unavailable (download failed) | Coral `.alert`: `This PDF could not be downloaded.` detail `<reason>`; buttons `Try again` (`btn--on-dark`) and link `Open the source page` (abs_url) | as Downloading, copy `…unavailable.` |
| Render failed (corrupt/unsupported) | Coral `.alert`: `This PDF could not be displayed.` detail `The file may be damaged or use features the viewer does not support.` + `Open PDF in new tab` | Highlights list still shows saved items; `Go to` disabled |
| Not saved / unknown id | `.empty`: `This paper is not in your Library.` + `Go to Library` | hidden |
| Ready | Pages | Normal |

### [FE] L22 — Panel as sheet (< 1024px)
- Native `<dialog>` opened with `showModal()`; bottom sheet, height 85dvh, top radius `--radius-lg`, canvas bg,
  `--shadow-button`. Header row: tabs + close icon button `Close` (40px). Esc and Close return focus to the
  `Highlights and chat` toolbar button. Background scroll locked by the dialog.
- Slide-up 200ms `--ease-out`; reduced motion: no transform, appears instantly.

### [FE] L23 — Export notes (Markdown)
- Toolbar text button `Export notes`, disabled (`aria-disabled`) when there are no highlights.
- Built client-side from the loaded annotation list, downloaded as `<paper_id>-notes.md` via a Blob link.
- Format: `# <title>` / `<paper_id> · <abs or pdf url>` / blank / per highlight in page order:
  `> <quote> (p.N)` then the note on the next line (omit if empty), blank line between items.
- Announce `Notes exported.` No dialog.

### [FE] L24 — Find in paper (simple)
- Opens a find row under the toolbar: search input (label `Find in paper`, placeholder `Find text`), result count
  caption `7 matches on 4 pages`, `Close` text button. Enter runs it; Esc closes and returns focus to the Find button.
- Results list below the input (max 6 visible, scrolls): each a button `Page 3: …context snippet with **match**…`
  (match in weight 500, not color). Activating jumps to the page (same jump/outline as L19). No in-page match painting
  in v3 (research).
- Searches the loaded text layer per page or the server page text (B8); FE does not paint matches.
- No matches: `No matches.` Not ready: input disabled with `Find is available once the PDF is ready.`
- < 1024px: the find row is full width under the toolbar; results list max 4 visible.

---

## 5. Keyboard and focus summary

| Where | Order / keys |
|---|---|
| Nav | skip links, brand (not focusable), Triage, Library |
| Triage row | rank (none), title (none), `Save`, links, critique summary |
| Library | skip link, rail items (>= 1024) top to bottom, New directory, h1, Rename/Delete (if user dir), Filter input, Clear filters, tag chips, Show all tags, rows (Open preview, ext links, Directory select, Remove, critique) |
| Preview | Back, h1 title (programmatic only), Export notes, Open in new tab, page prev/input/next, zoom out/select/in, Find, Highlight/color, find row (when open), viewer region, selection popover (when open), panel tabs, panel content |
| Global | `/` focuses the view's main input (Triage query, Library filter, Preview chat input). Esc closes popover, sheet, inline forms, confirms (topmost first). |
All focus rings: existing `:focus-visible` 2px `--color-info-border`. On the dark pressed chip use the same ring with
2px canvas offset (`--ring-focus`).

---

## 6. ARIA and announcements

- One polite live region (existing `#status`) for all view-level announcements. Row errors use `role="alert"`.
- Save buttons and tag chips: `aria-pressed`. Directory items: `aria-current="true"`. Nav: `aria-current="page"`.
- Panel tabs: `role="tablist"/"tab"/"tabpanel"`, `aria-controls`, `aria-selected`.
- Chat log: `role="log"`, `aria-label="Conversation about this paper"`.
- Highlight list items expose quote + note as text; the visual overlay is `aria-hidden`.
- Color never stands alone: highlight color name is printed in the list; pressed chips get a check; saved gets
  a filled glyph and the word `Saved`.

---

## 7. Motion, reduced motion, forced colors

- Motion used: row collapse (200ms), highlight/page outline pulse (1.6s, `--dur-flash`), sheet slide (200ms),
  existing working glyph. Nothing else animates; no popover fade.
- `prefers-reduced-motion: reduce`: instant scroll for jumps (`behavior: "auto"`), static 2s outlines, no row collapse
  animation, no sheet transform, working glyph static (existing rule).
- `forced-colors: active`: highlights render as a 2px `Highlight` outline with no fill (`forced-color-adjust: none`
  is not used); pressed chips and saved buttons get a 1px `CanvasText` border plus their glyph; swatches show a
  border and keep their text labels; the sheet and popover get 1px `CanvasText` borders.

---

## 8. Copy strings (single source)

| Key | String |
|---|---|
| nav.triage / nav.library | `Triage` / `Library` |
| save.idle / busy / done / removing | `Save` / `Saving…` / `Saved` / `Removing…` |
| save.ok / save.removed | `Saved to Library.` / `Removed from Library.` |
| save.err / unsave.err | `Could not save. <reason>` / `Could not remove from Library. <reason>` |
| unsave.confirm | `Remove from Library? This deletes the saved PDF and <n> highlights with their notes.` (`highlight` when n = 1) |
| unsave.confirm.plain | `Remove from Library? This deletes the saved PDF.` |
| confirm.remove / keep | `Remove` / `Keep` |
| lib.h1 | `Library` (or the directory name) |
| lib.count | `<shown> of <total> saved papers` (`saved paper` when total = 1) |
| lib.filter.label / placeholder | `Filter` / `Tags or titles` |
| lib.tags.label / more / less | `Tags` / `Show all <n> tags` / `Show fewer tags` |
| lib.tags.summary | `Showing papers tagged <a> and <b>.` |
| lib.tags.none | `No tags yet. Tags are the search keywords that found each paper.` |
| lib.clear / cleared | `Clear filters` / `Filters cleared. <n> saved papers.` |
| dir.all / unsorted | `All saved` / `Unsorted` |
| dir.new / create / rename / save / cancel / delete | `New directory` / `Create` / `Rename` / `Save` / `Cancel` / `Delete directory` |
| dir.name.label / placeholder | `Directory name` / `e.g. final year thesis` |
| dir.err.empty / dup / long / save | `Enter a name.` / `"<name>" already exists.` / `Names can be up to 40 characters.` / `Could not save the directory. <reason>` |
| dir.delete.confirm | `Delete "<name>"? Its <n> papers move to Unsorted.` |
| dir.created / deleted / moved | `Directory "<name>" created.` / `Directory deleted. <n> papers moved to Unsorted.` / `Moved to <name>.` |
| row.open / remove / dir | `Open preview` / `Remove from Library` / `Directory` |
| row.saved / rankfor / hl | `Saved <d Mon>` / `for "<topic>"` / `<n> highlights` |
| pdf.downloading / ready / unavailable / retry / none | `Downloading PDF…` / `PDF ready` / `PDF unavailable` / `Try again` / `No PDF` |
| lib.loading / error | `Loading your library…` / `Could not load your library.` |
| lib.empty | `Nothing saved yet.` / `Save papers from your ranked results. Each saved paper keeps its rank, critique, tags and a local PDF.` / `Go to Triage` |
| lib.emptydir | `No papers in <name>.` / `Move a saved paper here with its Directory menu.` |
| lib.nomatch | `No saved papers match.` / `Try fewer tags or a shorter filter.` |
| pv.back / external / panel | `Library` / `Open PDF in new tab` / `Highlights and chat` |
| pv.page | `Page` `<input>` `of <n>`; buttons `Previous page` / `Next page` |
| pv.zoom | `Zoom out` / `Zoom in` / `Fit width` / `Fit page` |
| pv.hl | `Highlight` / `Highlight color` / `Yellow` / `Mint` / `Peach` / `Add note` |
| pv.hl.added / partial | `<Color> highlight added on page <n>.` / `Highlighted the part on page <n>. Select across pages one page at a time.` |
| pv.hl.empty | `No highlights yet.` / `Select text in the PDF, then pick a color. Add a short note to any highlight.` |
| pv.hl.actions | `Go to` / `Edit note` / `Color` / `Delete` / `Save note` / `Cancel` / `Show more` |
| pv.hl.deleted | `Highlight deleted.` / `Undo` |
| pv.tabs | `Highlights <n>` / `Ask this paper` |
| pv.chat.scope | `Answers use only this paper. Citations point to pages. Not saved: closing or reloading clears this chat.` |
| pv.chat.reset | `This chat clears when you close the preview or reload.` |
| pv.chat.idle | `Chat is off until you ask.` / `Your first question reads this paper, so it takes longer than the rest.` |
| pv.chat.starters | `What is the main claim?` / `What baselines are compared?` / `What are the stated limitations?` |
| pv.chat.label / placeholder / button | `Question about this paper` / `Ask about this paper` / `Ask` |
| pv.chat.start / slow / pending | `Reading this paper. The first answer takes longer.` / `Still reading. Long papers take up to a minute.` / `Reading this paper…` |
| pv.chat.refused | `Not in this paper` / hint `Ask about something this paper covers.` |
| pv.chat.err / retry | `Could not answer. <reason>` / `Ask again` |
| pv.chat.nopdf | `Chat needs the PDF text. It is not ready yet.` / `Chat needs the PDF text, and this PDF is unavailable.` |
| pv.cite / sources | `p. <n>` (aria `Go to page <n>`) / `Pages: ` |
| pv.opening / downloading | `Opening PDF…` / `Downloading the PDF…` + `You can read the critique below while you wait.` |
| pv.fail.download | `This PDF could not be downloaded.` / `Open the source page` |
| pv.fail.render | `This PDF could not be displayed.` / `The file may be damaged or use features the viewer does not support.` |
| pv.export / exported | `Export notes` / `Notes exported.` |
| pv.find | `Find in paper` / `Find text` / `<n> matches on <p> pages` (`match`, `page` singular) / `No matches.` / `Close` / `Find is available once the PDF is ready.` |
| pv.notsaved | `This paper is not in your Library.` / `Go to Library` |

No emoji, no exclamation marks, sentence case everywhere.

---

## 9. Backend needs (planner turns into tasks; FE must not invent the contract)

- **B1** Saved flag on results: `saved: bool` on every item of `POST /api/triage` and `GET /api/papers`, or a cheap
  `GET /api/library/ids`. Needed for L4 on load.
- **B2** Library CRUD: save (snapshot of the visible card: title, authors, rank, rank_reason, critique, basis, ids,
  links, topic ranked against), unsave (deletes local PDF file, annotations; Rev 2), list with tags, directory, saved_at, pdf_status,
  highlight_count.
- **B3** PDF lifecycle: download starts on save; `pdf_status` in `downloading | ready | unavailable | none` with error
  reason; retry endpoint; local file served same-origin (viewer needs it without CORS).
- **B4** Directories: create / rename / delete (moves papers to Unsorted) / move paper; unique case-insensitive names,
  max 40 chars; Unsorted is implicit and fixed.
- **B5** Tags: list with counts per directory (or FE computes from the list; either is fine if list returns tags).
- **B6** Annotations: create / update (color, note <= 500 chars) / delete / list per paper. Anchor per research:
  1-based page + rects as fractions of the page box + quote (<= 500 chars) + optional prefix/suffix.
  Routes per research: `GET|POST /api/papers/{id}/annotations`, `PATCH|DELETE /api/annotations/{id}`.
- **B7** Per-paper chat: lazy start on first question, answers grounded only on that paper's text, `[p.N]` page
  citations validated server-side (unknown pages dropped), same `refused` semantics as `/api/chat`. No stored
  turns (Rev 2): FE sends the in-page history with each request if multi-turn context is wanted. MOCK_LLM canned `[p.1]` answer.
- **B8** Find in paper (optional): server search over per-page text returning `{page, snippet, match offsets}`; or FE
  uses the text layer content and B8 is dropped. Planner picks one.

## 10. Assumptions and open decisions (planner/spec owner decides)

1. **Tag unit.** Assumed one tag = the whole normalized topic string of a run (`diffusion models`), not single words
   (words like "of" would be noise). Item-only runs (arXiv ids / PDF URLs, topic `""`) add no tag.
2. **Tag accrual.** Assumed tags accumulate whenever a run surfaces the paper, before or after saving.
3. **Snapshot vs live.** Assumed the saved card is a frozen snapshot; a later re-triage does not overwrite it.
4. **Renderer.** Vendored pdf.js under `static/` (no CDN), per research. The "vanilla, no framework" rule needs an
   explicit spec note allowing a vendored PDF library and `.mjs` MIME registration.
5. **Mock mode PDF.** Uses `src/paper_triage/fixtures/sample.pdf` (multi-page, known words) per research.
6. **Chat without PDF.** Decided: disabled with a reason, no abstract fallback.
7. **Chat persistence.** Decided: page-only, not stored; resets on reload or close. No pre-warm on open.
8. **Unsave cascade.** Decided: always confirm; unsave deletes the local PDF, highlights and notes.
9. **No sort control, no bulk move, no drag and drop** in v3.
10. **Download trigger.** Research says fetch only on user action (Save or first open). Brief assumes download starts
   on Save, so `Downloading` shows in the Library row right after saving. Direct PDF URLs: decided, saveable like
   arXiv papers (no abs link; `Open the source page` points at the PDF URL).
11. **Browsers.** Decided: modern evergreen only. No polyfills or fallbacks.
