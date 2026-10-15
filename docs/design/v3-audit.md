# v3 UI audit: Save, Library, Preview, paper chat

Author: designer, 2026-10-03. Against `docs/design/v3-library-brief.md` (Rev 2), DESIGN.md, PRODUCT.md.
Method: app on :8767 with `MOCK_LLM=1` and a temp `PAPER_TRIAGE_DATA_DIR`. Seeded 4 saved papers
(2401.00001 ready with 2 highlights and 1 page note, 2401.00005 failed), directories `network` and
`final year thesis with a long name`. Playwright screenshots at 1440x900, 820x1100 and 390x844
(about 40 states). `impeccable detect` was run on `src/paper_triage/static`. No console errors.
Scope is visual and UX conformance only. The tester owns functional QA.

Accepted and not flagged: text selection uses info-border at 30% alpha (`.textLayer ::selection`),
and click-to-select a highlight on the page is not built.

## Verdict

The build matches the brief's structure and copy closely. These all match the brief: the view
switcher, hash routes, Save states with glyph and text, the always-on unsave confirm, pressed tags
with a check glyph, the directory rail, inline confirms, the coral unavailable card, chat that is
off until the first question, the refusal component, the find row, the swatch popover, and the
sheet below 1024px. Most failures are layout overflow and density at narrow widths. The worst is
the Preview toolbar on mobile, which takes 41% of the screen. Audit health: a11y 3, perf 3,
responsive 2, theming 3, integrity 3, total 14/20 (Good).

## Must-fix (ordered)

1. **[FE] L8: rail items overflow the 240px rail.** In `app.css`, `.rail__list` is an auto grid,
   so the longest nowrap name sets the track width. Every item then reaches about 12-18px past the
   rail's right hairline, and the counts sit on the line. The ellipsis never triggers.
   Fix: `.rail__list { grid-template-columns: minmax(0, 1fr); }` and `.rail__list > li { min-width: 0; }`.
   Items must end at the rail's content edge, with the count inside the 12px item padding.

2. **[FE] L9: the New directory form in the rail squeezes the input to about 88px.** The typed name
   scrolls out of view. Cause: `.dir-form__row` puts the input, `Create` and `Cancel` in one 224px row.
   Fix: inside `.rail`, set `.dir-form__row { flex-wrap: wrap; }` and
   `.dir-form input[type="text"] { flex-basis: 100%; }`. Buttons go on the line below. The error
   line stays under the input.

3. **[FE] L11.5: the rank snapshot caption wraps to 4 lines in the 72px rank column (>= 768px).**
   `.rank__for` shows `for "diffusion models video"` as a narrow ragged stack. Mobile already does
   better: `.lib-for` shows `Ranked for "…"` under the authors.
   Fix: use `.lib-for` at every width and hide `.lib-row .rank__for` at every width (move the rules
   out of the `max-width: 767px` block).

4. **[FE] L11.6 / L13: the row Directory select overflows the viewport below 768px.** At 390px,
   `documentElement.scrollWidth` is 402. The long option widens `.lib-dir__select`, and
   `.lib-dir` is `inline-flex` with no width limit.
   Fix: `.lib-dir { display: flex; max-width: 100%; min-width: 0; }` and
   `.lib-dir__select { flex: 1 1 auto; min-width: 0; max-width: 20rem; }`.

5. **[FE] L14 / L10d: an empty directory shows `No tags yet. Tags are the search keywords that
   found each paper.`** This is false, because the Library has tags. Only this directory has no
   papers.
   Fix: when the current directory has 0 papers, hide `.lib-filters` (filter row and tag bar). Show
   only the L14 empty-directory title and body. Keep `lib.tags.none` for a Library with no tags at all.

6. **[FE] L3 / L11.1: the Save and Open preview buttons squeeze titles at 390px.** `.save` has
   `min-width: 7.75rem`, which leaves the title about 150px. Titles wrap to 4-5 lines in the
   Triage list (`m-01`) and the Library list. `.paper__head { flex-wrap: wrap }` has no effect,
   because the title is `flex: 1; min-width: 0`.
   Fix: below 768px, set `.paper__head .paper__title { flex-basis: 100%; }`. The button then
   drops under the title, left-aligned, with 8px top gap. Keep the min-width, so the width still
   does not jump between states. Above 768px, nothing changes.

7. **[FE] L15 / L16: the Preview toolbar takes 350 of 844px on mobile, and the title shows 9
   characters (`Progressi…`).** It uses 6 rows: back, title and sheet button, then `Export notes`,
   `Open PDF in new tab`, page nav, zoom, and highlight. With find open, about 200px of PDF is
   left. Target: at most 3 rows, about 150px.
   Fix below 768px:
   - Row 1: `Library` back button + title, with the title wrapping to 2 lines (`-webkit-line-clamp: 2`).
   - Row 2: page nav, zoom select (hide `#pv-zoom-out` and `#pv-zoom-in`; the select and the keys
     remain), Find, `Highlights and chat`.
   - Row 3: `Highlight` + colour, then `Export notes` and `Open PDF in new tab` as inline text
     links, wrapping as needed.
   Also remove `.pv-external { flex-basis: 100% }` in the 767px block.

8. **[FE] L15: on tablet (820px), the title is cut at 230px.** `#pv-sheet-open` sits in `.pv-bar`
   between the title and `Export notes`.
   Fix: from 768 to 1023px, move `Highlights and chat` to the end of `#pv-controls` (row 2,
   `margin-left: auto`). Row 1 then keeps back, title, export and external. The DOM order may stay
   if you use CSS `order`, but keep the tab order logical. The brief's tab order puts the panel
   control after the viewer controls.

9. **[FE] L16: toolbar controls have mixed heights, and the Highlight split is not one control.**
   The icon buttons and page input are 40px, the selects are 44px (`.select`), and `#pv-hl-btn` is
   32px (`btn--small`). The Highlight button and the colour select also sit 8px apart, so they read
   as two unrelated controls.
   Fix: in `.pv-controls`, set every control to height 40px (`.pv-controls .select`,
   `.pv-controls .btn`). In `.pv-hlctl`, set gap 0, round only the outer corners
   (`border-radius: var(--radius-sm)` on the outer sides), and let the shared edge collapse
   (`margin-left: -1px` on the select).

10. **[FE] L23: Export notes looks enabled when it is disabled.** `#pv-export` has
    `aria-disabled="true"` with 0 highlights, but `.text-btn` has no disabled style, so it renders
    link-blue (`d-36`).
    Fix: `.text-btn[aria-disabled="true"] { color: var(--color-muted); cursor: default; }`. This
    rule covers every text button.

11. **[FE] L18: the selection popover covers the toolbar on mobile.** In `annotations.js`,
    `showPopover` flips below the selection only when `top < 8` in viewport coordinates. A
    selection near the top of the well therefore puts the popover over `.pv-toolbar` (`m-11`).
    Fix: flip when `top < el.well.getBoundingClientRect().top + 8`. Clamp so the popover never
    rises above the well's top edge.

12. **[FE] L19: the panel keeps the previous paper's tab.** If you open paper B after using Ask on
    paper A, B opens on `Ask this paper` (`d-20`). `selectTab` runs only from `showPanel(name)`.
    Fix: on every preview open (route change to a new `paper_id`), call `selectTab("highlights")`
    without moving focus. Rev 2 already resets the chat transcript at the same point.

13. **[FE] L22: the sheet header wastes a row, and the sheet surface is wrong.** `Close` sits alone
    in `.pv-sheet__head`, with the tabs on a second line. The sheet also uses
    `--color-surface-soft`, but the brief says canvas.
    Fix: render the tablist and the 40px `Close` button in one header row (tabs left, close right,
    hairline bottom). Set `.pv-sheet` and the sticky `.pv-chat__form` background to
    `--color-canvas` when inside the sheet.

## Nice-to-have (max 5)

1. On wide screens, the nav brand starts at the 1280px container (x=128) while the Preview toolbar
   starts at `--pad-x` (x=48). Consider aligning `.global-nav__inner` to full width in the Preview
   view only.
2. In the Triage unsave confirm, the `Remove`/`Keep` group touches the authors line. Add
   `margin-bottom: var(--space-sm)` to the confirm group.
3. `.text-btn` has 4px inline padding, so panel links (`Add note for this page`, `Edit note`, `Go to`)
   sit 4px in from the content edge. Use `margin-inline: -4px` on leading text buttons.
4. The row collapse animates `height` (detector `layout-transition`, `app.css:656`). Opacity plus a
   `grid-template-rows` collapse would avoid layout work. Visual result unchanged.
5. The not-saved Preview shows the placeholder h1 `Preview`. Set the h1 to the copy title
   `This paper is not in your Library.` and drop the duplicate paragraph.

## Notes for the planner (not FE)

- Mock `/api/paper-chat` refuses all three starter questions (`What is the main claim?` etc.), so
  the mock demo shows only refusals. Its refusal text, `The stored papers do not cover this.`,
  uses Triage wording inside a single-paper view. Suggest NEEDS-BE: mock answers the starters with
  `[p.1]`, and the per-paper refusal says `This paper does not cover that.`
- Tags are single keywords (`diffusion`, `models`, `video`) per the contract `tags.keywords(topic)`.
  Brief section 10.1 assumed the whole topic string. Accepted as a spec decision. The tag bar
  reads fine either way.
- Detector false positives: `cramped-padding` on `.intro` (border-bottom only) and
  `flat-type-hierarchy` (static HTML before CSS roles apply).

## Re-check (2026-10-03, after 6e1b9a1 and 22781d9)

One confirm pass on :8767 (`MOCK_LLM=1`, temp data dir), at 1440x900, 820x1100 and 390x844, with
the same states as the first pass. No console errors. At 390px, `documentElement.scrollWidth` is
390 in Library and Preview.

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | L8 rail overflow | Pass | Items end inside the rail. Counts clear the hairline. The long name ellipsizes (`final year thesis with a lon…`). |
| 2 | L9 rail New directory form | Pass | Input is full rail width. `Create`/`Cancel` on the next line. Error under the form. |
| 3 | L11.5 rank caption | Pass | `Ranked for "…"` sits under the authors at every width. The rank column is clean. |
| 4 | L11.6/L13 row select overflow | Pass | scrollWidth is 390 at 390px. The select fits beside its visible label. |
| 5 | L14/L10d empty directory | Pass | Filter row and tag bar are hidden. Only the empty-directory title and body show. |
| 6 | L3/L11.1 title squeeze | Pass | Below 768px, Save and Open preview drop under a full-width title. Titles wrap to 2 lines. |
| 7 | L15/L16 mobile toolbar | Pass (deviation accepted, see below) | 4 rows, 231px (was 350px). Title shows 2 full lines. |
| 8 | L15 tablet title | Pass | `Highlights and chat` moved to the end of row 2. The title gets about 390px. |
| 9 | L16 heights and Highlight split | Pass | All toolbar controls are 40px. Highlight and colour form one joined control. |
| 10 | L23 Export notes disabled look | Pass | Muted when `aria-disabled`. Link colour when highlights exist. |
| 11 | L18 popover flip | Pass | On mobile it flips below the selection and stays inside the well. Desktop is unchanged. |
| 12 | L19 tab reset | Pass | A new paper opens on `Highlights` after Ask was used on the previous paper. |
| 13 | L22 sheet header and surface | Pass | Tabs and `Close` share one row. Canvas surface. |

**Mobile toolbar deviation: accepted.** At 390px, the pager, zoom select and Find fill row 2. The
joined Highlight control plus `Highlights and chat` cannot share that row without shrinking
targets below 40px. 231px is 27% of an 844px viewport, down from 41%, and the title is readable.
The two external text links on row 4 are a fair trade.

**Refusal copy: accepted.** The title `Not in this paper` and the hint come from the brief. The body
is the server text `This paper does not cover that.` This closes the planner note about Triage
wording.

### Must-fix (regression from fix 8)

R1. **[FE] L16 / section 5: `Highlights and chat` focus order does not match its visual position
below 1024px.** `.pv-bar` and `.pv-controls` are `display: contents`, and `#pv-sheet-open` is
moved only with CSS `order`. In the DOM it stays in `.pv-bar`, right after `#pv-back`. Keyboard
focus therefore goes Back, Highlights and chat, Export, Open PDF, then the pager. Visually, the
button sits at the end of row 2 (tablet) or row 3 (mobile). This fails WCAG 2.4.3 and the brief's
order, which puts the panel control after the viewer controls.
Fix:
- Move the `<button id="pv-sheet-open">` element in `index.html` out of `.pv-bar`. Make it a
  direct child of `.pv-toolbar`, placed after `#pv-controls`.
- Do not put it inside `#pv-controls`. That container is `hidden` in the failed, downloading and
  not-saved states, and the sheet must stay reachable there.
- Keep its current `order` values (10 tablet, 9 mobile).
- At >= 1024px it stays `display: none` (no change).
- Check that it still appears in the failed state below 1024px.
Accepted, not flagged: on mobile, `Export notes` and `Open PDF in new tab` come after the
pager in visual order but before it in DOM order. They are links at the end of a short toolbar,
and on tablet and desktop the DOM order matches.

### Nice-to-have (re-check)

- The `Highlights and chat` label sits about 5px above the vertical centre of its 40px box
  (tablet and mobile). Use `display: inline-flex; align-items: center` with the base line-height.

### Score

Accessibility 3 (R1 open), performance 3, responsive 4, theming 4 (literals moved to tokens),
integrity 3. **17/20 (Good).** It becomes 18/20 once R1 lands.
