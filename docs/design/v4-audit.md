# v4 UI audit: Carbon redesign (T066-T076)

Author: designer, 2026-10-04, at HEAD 14af76e. Checked against DESIGN.md v2.0 (Paper-Triage-Carbon),
PRODUCT.md and `docs/design/redesign-brief.md`. Same format and scoring as `v3-audit.md`.

**Method.** The app ran on :8767 with `MOCK_LLM=1`, a temp `PAPER_TRIAGE_DB` and a temp
`PAPER_TRIAGE_DATA_DIR`. Seed data: 4 saved papers (2401.00001 ready with 2 highlights and 1 page
note, 2401.00005 failed) and the directories `network` and `final year thesis with a long name`.
Playwright captured about 150 screenshots at 1440x900, 1280x800, 820x1100 and 390x844. They cover
Triage (empty, working, results, critique, chat answer, pending, refusal, unsave confirm, error, load
more), Library (all, tag pressed, no match, empty directory, duplicate name, manage panel, load error,
nothing saved) and Preview (ready, popover, highlights, note edit, paper chat idle, pending, answer
and refusal, find and jump, downloading, failed, not saved, side panel, sheet). Extra runs covered
reduced motion at 1440 and forced colours at 1440 and 390. I also ran a computed-contrast walk over
every visible text node in four views, a toolbar tab-order walk, `impeccable detect` on
`src/paper_triage/static`, and a check for literal colours outside `:root`. The only console errors
came from the 500 responses I injected.

**Accepted, not flagged:** the mobile Preview toolbar (5 visual rows, 249px, 30% of 844), and the
spec-mandated 3px left rules on notifications and highlight quotes (detector `side-tab` x6).

## Verdict

The redesign follows the Carbon system closely. It is light, square and dense, with one blue accent,
1px rules and no card shadows. Plex is vendored and loads, the 400/600 pair is the only weight pair,
and `font-synthesis` is off. No literal colours appear outside `:root`. The view titles read as tool
headings, not marketing. These behaviours hold:

- B-a: Preview opens on `Ask this paper` at every width.
- B-b: during a run, old rows stay at opacity 1, `pointer-events: auto` and not `inert`.
- v3 R1: `Highlights and chat` now comes after the viewer controls in tab order at 820 and 390.
- Nothing overflows horizontally: `scrollWidth` equals the viewport at every width and in every view.
- Every Preview toolbar control is 40px.

What is left is small: one contrast failure, one forced-colours signal that is lost, and a few places
where the build differs from DESIGN.md. **Audit health: a11y 3, perf 4, responsive 3, theming 4,
integrity 3. Total 17/20 (Good).** Fixing items 1 and 2 brings it to 18. Fixing items 1 to 6 brings
it to 19.

## Must-fix (ordered; items 1 and 2 block acceptance)

1. **[FE] BLOCKS. The current rail item's count fails contrast (3.81:1).** In `app.css`,
   `.rail__count` uses `--color-ink-subtle` (#6f6f6f). On the current item (`surface-selected`
   #e0e0e0) that gives 3.81:1, and on hover (`surface-hover` #e8e8e8) about 4.2:1. Both are below
   4.5:1 (WCAG 1.4.3). DESIGN.md 2.1 also says ink-subtle must never sit on surface-2. You can see it
   on `All saved 4` in `d-10-library`.
   Fix: `.rail__item[aria-current="true"] .rail__count { color: var(--color-ink-muted); }`, and inside
   `@media (hover: hover)` add `.rail__item:hover .rail__count { color: var(--color-ink-muted); }`.
   ink-muted is 5.9:1 on #e0e0e0.

2. **[FE] BLOCKS. In forced colours, every nav link and every Preview tab shows the underline.** The
   2px `transparent` bottom border on `.views a` (app.css ~546) and `.pv-tab` (~808) is painted as a
   system colour. Triage and Library are both underlined, and so are `Highlights` and
   `Ask this paper`. Weight is then the only signal left for the current view or tab. DESIGN.md 7 asks
   for weight plus underline. You can see it in `fd-23-hl-list` and `fd-11-lib-tag`.
   Fix: in the forced-colours block (app.css ~1036), add
   `.views a, .pv-tab { border-bottom-color: Canvas; }` and
   `.views a[aria-current="page"], .pv-tab[aria-selected="true"] { border-bottom-color: Highlight; }`.

3. **[FE] Polish. The Preview back button is an outline button, but the spec says ghost.**
   `#pv-back` in `index.html:157` has the classes `btn btn--secondary btn--small`, so it renders a 1px
   `border-strong` box. DESIGN.md 8.8 says "back (ghost with a chevron, `Library`)". The box is the
   heaviest object in the toolbar and competes with the title.
   Fix (CSS only): `.btn.pv-back { background: transparent; border-color: transparent; color: var(--color-link); }`.
   In `@media (hover: hover)`, add `.btn.pv-back:hover { background: var(--color-surface-hover); color: var(--color-link-hover); }`.
   Make the chevron `::before` use `currentColor`. Keep the 40px height and the inset focus ring.
   Update any e2e test that asserts the border.

4. **[FE] Polish. The form submits are outline buttons, but the spec says primary.**
   DESIGN.md 8.1 lists Create (directory), Save note and Rename as primary. Today they are
   `btn btn--secondary btn--small`:
   - `library.js:459`: the shared directory form submit. This covers `Create` and the rename `Save`.
   - `annotations.js:652`: `Save note`.

   The note editor and the new-directory form then have no clear commit action (`d-24-note-edit`,
   `d-14-dir-dup`).
   Fix: change both to `btn btn--primary btn--small`. Keep the 32px height. Each of these regions then
   has exactly one primary button.

5. **[FE] Polish. The unsave confirm and the mobile Save button crowd the authors line (4px).**
   `.confirm` (app.css ~570) has `margin-top` but no bottom margin. DESIGN.md 8.4 asks for a 12px
   margin below. Below 768px, the Save and Open preview button sits 4px above `.paper__authors`
   (`m-06-unsave-confirm`, `m-02-results`). This is the v3 nice-to-have 2, still open.
   Fix: add `.confirm { margin-bottom: var(--space-sm); }`. In the `max-width: 767px` block, add
   `.paper__head .btn { margin-bottom: var(--space-xs); }`.

6. **[FE] Polish. The not-saved Preview state is left-aligned, its title is too small, and the h1
   still says `Preview`.** `previewState()` in `app.js:1212` renders `.empty` inside `#pv-stage` at the
   left edge (x=48), and the title uses heading-xs. DESIGN.md 8.8 asks for a centred column, max
   640px, and DESIGN.md 3.3 sets heading-sm for the not-saved title. The toolbar h1 reads `Preview`,
   which is the v3 nice-to-have 5 (`d-31-notsaved`).
   Fix:
   - Add `.pv-stage > .empty { max-width: 640px; margin: var(--space-xl) auto 0; padding-inline: var(--pad-x); }`.
   - Add `.pv-stage > .empty .empty__title { font: var(--type-heading-sm); }`.
   - In the `!it` branch of `renderPreview`, set `previewHeading.textContent = "Not in your Library"`.
     This is a copy change. Planner, confirm it, or keep `Preview`.

## Nice-to-have (max 5)

1. **`Triage papers` changes width when it becomes `Triaging…`** (119 to 95px), so the field widens
   by 24px during a run (`d-s01-working`). Fix: `.triage-form .btn--primary { min-width: 7.5rem; }`.
2. **The `Highlights and chat` label sits about 4px above centre** (820 and 390). This is still open
   from the v3 re-check. Fix: `.pv-sheet-open:not([hidden]) { align-items: center; }`.
3. **The highlight meta line has no dot.** DESIGN.md 8.8 says "colour name, a dot, and `Page n`". The
   build renders `Yellow  Page 1`. Fix: `.hl-item__page::before { content: "·"; margin-inline: var(--space-xxs); }`.
   Or add the dot in `annotations.js:563`.
4. **Leading text buttons sit 4px in from the content edge.** This is the v3 nice-to-have 3 and
   affects `Add note for this page`, `Edit note` and the first action in panel rows. Fix: `.hl-item__actions > .text-btn:first-child, .pv-hl-tools > .text-btn:first-child { margin-left: calc(-1 * var(--space-xxs)); }`.
5. **On wide screens the nav brand and the Preview toolbar start at different x.** The brand starts at
   x=112 (1312 container) and the toolbar at x=48 (`--pad-x`). This is the v3 nice-to-have 1, now
   more visible because `Library` is boxed. Consider a full-width `.global-nav__inner` in the Preview
   view only.

## Checked and passing (no action)

- **Tokens and type.** Body is Plex Sans. Ids and cite chips are Plex Mono. Numerals are tabular.
  Sentence case everywhere. The contrast walk found no other pair below 4.5:1 in Triage, Library,
  Preview ready or Preview failed. ink-subtle appears only on canvas and surface-1.
- **Focus.** Filled buttons (`#submit`, `Ask`) show the inset blue ring with the inner white ring.
  Fields, the page input, Save and tags show the inset 2px ring. The well shows an inset ring when
  it has keyboard focus.
- **States.**
  - The working card is surface-1 in normal flow, with the timer at the right.
  - Errors use the error-surface notification with a 3px rule and a charcoal `Try again`.
  - Refusals use info-surface (`Not in these papers` / `Not in this paper`) and read as deliberate.
  - The empty directory hides the filters. The duplicate name shows an inset error outline and text.
  - Downloading and failed use the centred 640px column.
  - The disabled `Ask` uses surface-2 with ink-disabled text.
  - The busy `Triaging…` and `Loading 5 more…` are disabled controls, so the 0.6 opacity is exempt
    from contrast rules.
- **Preview.** Highlights are opaque multiply fills, so text stays black. The popover has 32px
  swatches and a ring on the last-used one, and on mobile it flips below the selection. Find hits
  bold the match, and a jump flashes the page outline. The side panel is surface-1 with a
  border-page left edge. The sheet is 85dvh on canvas, with the tabs and Close in one row and the
  fields on surface-1.
- **Reduced motion.** The cited row and the page or highlight flash become static outlines. New rows
  get a static info-surface background. The sheet appears without sliding. The rays are static.
- **Forced colours.** Highlights become a 2px `Highlight` outline. Panels, notifications, chips and
  meters keep a `CanvasText` border. The pressed tag keeps its check glyph. The current rail item
  keeps its bar and weight. The one exception is item 2.
- **Detector.** `side-tab` x6 is spec-mandated (accepted). `cramped-padding` on `.intro` and
  `.pv-tabbar` is a false positive, because those containers have only a bottom rule.
  `flat-type-hierarchy` is a false positive, because it reads static HTML before the CSS roles apply.
  `design-system-font` on "IBM Plex Sans Fallback" is the metric fallback that DESIGN.md 3.2
  requires. The advisory about the input border-top is the browser's default style before the CSS
  loads.

## Score

| # | Dimension | Score | Key finding |
|---|---|---|---|
| 1 | Accessibility | 3 | Rail count at 3.81:1 (item 1). Forced-colours underline on every link and tab (item 2). |
| 2 | Performance | 4 | Fonts are vendored with unicode-range. No layout-property animation. Chat loads lazily. |
| 3 | Responsive | 3 | No overflow at any width. The 4px crowding on mobile (item 5) and the accepted toolbar height remain. |
| 4 | Theming | 4 | Every colour is a token. The scheme is light only, as the spec requires. |
| 5 | Integrity | 3 | Coherent Carbon system, with three spec drifts (items 3, 4 and 6). |
| **Total** | | **17/20** | **Good.** 18 after items 1 and 2. 19 after items 1 to 6. |
