# Redesign brief: apply the Carbon-based DESIGN.md

Author: designer, 2026-10-03. The visual spec is the new root `DESIGN.md` (v2.0, Paper-Triage-Carbon).
This brief is the work list for applying it. Section numbers like D8.4 point into DESIGN.md.

**Scope.** This is a visual revamp. It does not change copy, DOM order, ids, ARIA, hash routes,
keyboard paths or API calls. Two behaviour changes the user asked for are in flight in FE and must
survive the restyle:

- **B-a.** Preview opens on the `Ask this paper` tab (panel and sheet). The chat stays lazy.
- **B-b.** During a new search, old results stay interactive until the new results replace them.
  The working card does not block them. The redesign removes the 0.4 dimming (D8.4).

Class names stay as they are. Restyle existing selectors; do not rename them. If an e2e test asserts
an old visual value (opacity, colour, radius), update it to the DESIGN.md value in the same task and
say so in the commit.

## 0. Foundations (do first; every other item depends on these)

1. **[FE] Fonts.** Vendor IBM Plex per D3.1 into `src/paper_triage/static/vendor/fonts/`: 7 woff2
   files (about 125 KB), `LICENSE-IBM-Plex.txt` (OFL 1.1) and a `README` with package names and
   versions. Write `vendor/fonts/plex.css` with the `@font-face` rules and fallback face from D3.2.
   Copy the `unicode-range` values verbatim from Fontsource `latin.css` and `latin-ext.css`; Greek is
   `U+0370-03FF`. Link it in `index.html` before `app.css` with a relative href. Fetch the packages at
   build time only (`npm pack`, see `docs/research/ibm-verify.md`). Nothing loads from the network at
   runtime.
2. **[FE] Tests for fonts** (`tests/frontend/test_static_assets.py`). The existing rule
   "`@font-face` not in own CSS" stays valid, because `@font-face` lives under `vendor/`. Add:
   - all 7 files exist and are non-empty;
   - the licence file exists and contains "SIL Open Font License";
   - `plex.css` uses only relative `url()` values;
   - `index.html` links `vendor/fonts/plex.css`.
3. **[FE] Tokens.** Replace the whole `:root` block in `app.css` with the DESIGN.md tokens (D9):
   `--color-*`, `--hl-*`, `--type-*`, `--space-*`, `--radius-*`, `--control-*`, `--dur-*`, `--ease-*`,
   `--shadow-overlay` and the layout sizes. Delete every Airtable token and every `/* unused */` line.
   Rewrite the header comment so it says "Carbon-based, see DESIGN.md". Set `color-scheme: light`.
   Add `font-synthesis: none` and the stacks from D3.2 to `html`/`body`. Old to new map:
   | Old | New |
   | --- | --- |
   | `--color-body` | `--color-ink` |
   | `--color-muted` | `--color-ink-muted` (secondary) or `--color-ink-subtle` (captions, helper, placeholder); see D2.1 |
   | `--color-hairline` | `--color-border-subtle` |
   | `--color-edge-input` | `--color-border-strong` |
   | `--color-surface-soft` | `--color-surface-1` |
   | `--color-surface-strong` | `--color-surface-2` (or `--color-well` in Preview) |
   | `--color-coral` | `--color-error` |
   | `--color-cream` | `--color-info-surface` (refusal, no-PDF, flash) or `--color-surface-1` (working card) |
   | `--color-info-border` | `--color-focus` |
   | `--color-yellow/mint/peach` | `--hl-yellow/mint/peach` |
   | `--type-title-sm` (paper title) | `--type-heading-xs` |
   | `--type-reason` | `--type-prose` |
   | `--type-caption`, `--type-chip` | `--type-label` |
   | `--type-body-md` | `--type-body` (wrapped) or `--type-body-compact` (single line) |
   | `--type-display-md` | `--type-heading-lg` / `--type-numeral-lg` |
   | `--radius-sm/md/lg` | `0` (`--radius-none`) unless D5 says otherwise |
4. **[FE] Global focus, hover and motion.** Implement focus once per D7 (inset for controls, inset
   white ring for filled buttons). Put all hover rules inside `@media (hover: hover)`. Replace the
   motion tokens per D6. Keep every `prefers-reduced-motion` and `forced-colors` block and update them
   to the new tokens. `test_css_has_reduced_motion_rules` must still pass (`@keyframes ray` and
   `breathe` stay).

## 1. Shell and nav (D8.3)

5. **[FE] `.global-nav`**: 48px (`--nav-h`). View links `.views a`: 48px tall, `ink-muted`; the
   current link gets `ink`, 600 and a 2px `primary` underline. Brand in `body-emphasis`.
6. **[FE] `.badge` (mock):** pill, 1px `info` border, `info` text, `label`. `.mock-label__more` and
   `.model` in `label` with `ink-muted` / `ink-subtle`.
7. **[FE] Buttons** (D8.1), mapped onto existing classes:
   | Class | New look |
   | --- | --- |
   | `.btn--primary`, `.btn--ask` | Primary, 40px (48px in `.triage-form`), radius 0 |
   | `.btn--secondary` | Outline (`border-strong`, ink text) |
   | `#load-more`, `.alert .btn` / notification `Try again` | Secondary (charcoal) |
   | `.btn--small` | Outline at `--control-sm` (32px) |
   | `.btn--remove` | Danger outline |
   | `.btn--on-dark` | Retire the look: notifications are light now, so use secondary |
   | `.text-btn`, `.ext-link` | Ghost: `link`, hover fill `surface-hover` with `link-hover` text |
   | `.icon-btn` | Square 40px ghost icon button (no circle, no border) |

## 2. Triage view (D8.4, D8.5, D8.6)

8. **[FE] `.intro`, `.triage-form`:** 48px field and button, Carbon field (`surface-1` fill, bottom
   `border-strong` rule, inset focus). Title `heading-md` / `heading-lg` (>= 768). Lead in `prose`
   `ink-muted`.
9. **[FE] `.paper` rows:** rank column 56 / 72px; padding-block 16 / 24. `.rank__n` uses
   `numeral-md` / `numeral-lg`; `.rank__of` uses `label` `ink-subtle`; `.rank__meter` is a 4px
   square bar with `rank-track` / `rank-fill`. `.paper__title` uses `heading-xs`. `.paper__reason`
   uses `prose` `ink`. `.paper__id` uses `mono`. `.flag` is a square `surface-2` tag; `.flag--failed`
   has `error` text and border.
10. **[FE] `.disclosure` and `.critique`:** square `surface-1` panel. Section heads in
    `body-emphasis`, text in `body`. Chevron at `dur-moderate`.
11. **[FE] `.save`:** outline, 32px, min-width kept. `.is-saved` uses `surface-2` with no border.
    `.confirm` uses the danger outline plus an outline `Keep`.
12. **[FE] B-b, results during a run:** in `.is-stale`, remove `opacity: 0.4`, so old results keep
    full opacity and stay interactive (no overlay, no `pointer-events`, no `inert`). `.working` stays
    in normal flow above the list, styled `surface-1` with a square frame. `.working--compact` is
    the same at 12/16 padding. Leave the class hook in place in case FE logic still toggles it.
13. **[FE] `.notes`:** `surface-1`. **`.alert`:** error notification (`error-surface`, 3px `error`
    left rule, ink text, secondary `Try again`). The coral fill and white text are removed;
    `.ext-link--on-dark` becomes a normal ghost link.
14. **[FE] `.empty`:** title `heading-xs`, body `prose` `ink-muted`, example chips as 32px outline
    buttons.
15. **[FE] `.chat`:** square `surface-1`, no border. `.chat h2` uses `heading-sm`. `.turn__q` uses
    `body-emphasis`. `.turn__a` uses `body`. `.turn__a--refused` becomes an info notification
    (`info-surface`, 3px `info` rule). Fields inside the panel are canvas.
16. **[FE] `.cite`:** `mono`, `cite-surface`, radius 2px; active and hover `cite-surface-active`.
    `.cite--off` is dashed `border-strong` with `ink-muted` text.
17. **[FE] Flashes:** `.paper--cited` and `.paper--new` fade `info-surface` over `dur-flash`. The
    reduced-motion fallbacks follow D6.

## 3. Library view (D8.7)

18. **[FE] `.rail`:** items 32px (40 on coarse pointers). `.rail__item[aria-current="true"]` gets the
    `surface-selected` fill, 600 weight and a 3px inset `primary` left bar (`box-shadow: inset 3px 0 0`
    so nothing shifts). Hover `surface-hover`. Counts in `label` `ink-subtle`.
19. **[FE] `.tag`:** pill, 32px, 1px `border-strong`, `label`. `[aria-pressed="true"]` uses
    `surface-inverse` with white text and keeps the check glyph. Focus is the filled-button ring.
20. **[FE] Fields and selects** (`.lib-filter input`, `.select`, `.lib-dir__select`, `.dir-form input`):
    Carbon field look (D8.2). The select chevron is an inline SVG data URI. The row select is 32px.
21. **[FE] Library rows:** same as items 9 and 11. `.lib-pdf` uses `label`; `.lib-pdf--failed` uses
    `error`. `.lib-saved` and `.lib-hl` use `ink-subtle`. `.dir-manage` uses square `surface-1`.
22. **[FE] `.lib-row.is-collapsing`:** opacity plus a `grid-template-rows` collapse instead of a
    `height` transition (closes audit nice-to-have 4). Use `ease-exit` at `dur-moderate`.

## 4. Preview view (D8.8)

23. **[FE] `.pv-toolbar`:** every control is 40px and square. The title uses `heading-xs`. Pager,
    zoom and find are icon or ghost buttons. `.pv-hlctl` is a joined outline button plus select
    (shared 1px edge). `.pv-sheet-open` is outline. The wrap and order rules below 1024 stay as built.
24. **[FE] `.pv-find`:** Carbon field, `label` count. `.find-hit` hover uses `surface-hover`.
    `.find-match` uses `body-emphasis`.
25. **[FE] `.pv-well` and `.pdf-page`:** `well` fill; pages are canvas with a 1px `border-page` edge.
    The page flash is a 2px `focus` outline. In `.textLayer ::selection`, use `primary` at 25%.
26. **[FE] Highlights:** `.hl--yellow/mint/peach` become opaque fills from `--hl-*` (no
    `color-mix` alpha), with `mix-blend-mode: multiply` kept on `.hl-layer`, radius 2px. Swatches
    and `.dot` become circles with a 1px `border-strong` edge. `.hl-item__quote` gets a 3px left rule
    in the highlight colour. Stored colour names do not change, so no data migration is needed.
27. **[FE] `.pv-popover`:** square, canvas, `shadow-overlay`, 1px `border-subtle`. `.swatch.is-last`
    gets a 2px `ink` ring offset 2px.
28. **[FE] `.pv-panel`:** `surface-1` with a 1px `border-page` left edge. `.pv-tab` is 40px; the
    selected tab has a 2px `primary` underline and 600 weight. **B-a:** the default selected tab on
    every preview open is `Ask this paper`. The visual default must match FE's behaviour change, and
    nothing loads until the first question.
29. **[FE] Notes and paper chat:** `.note-editor textarea` uses a canvas field on the panel.
    `.note-counter.is-max` uses `error`. `.pv-chat__nopdf` becomes an info notification. The
    `.pv-chat__form` sticky background is `surface-1` (canvas inside the sheet). `button.cite` gets
    the same chip as item 16.
30. **[FE] `.pv-sheet`:** square top, canvas, `shadow-overlay`, `overlay` backdrop. Tabs and Close
    share one header row. Slide in with `ease-entrance` at `dur-moderate`; no slide under reduced
    motion.
31. **[FE] `.pdf-page__notext`:** info notification look (`info-surface`, `body`), square.

## 5. Backend

32. **[BE] woff2 MIME type.** In `src/paper_triage/app.py`, next to the existing
    `mimetypes.add_type("text/javascript", ".mjs")`, add `mimetypes.add_type("font/woff2", ".woff2")`.
    macOS Python already maps it, but minimal Linux images may not. Add a test asserting that
    `GET /vendor/fonts/plex-sans-latin-400.woff2` returns `content-type: font/woff2`. This test lands
    after item 1. It is a small item and can ride with any BE task.

## 6. Verify

33. **Tester:** full pytest plus ruff, the e2e suites at 390, 820 and 1440, and a spot check of the
    contrast pairs from DESIGN.md section 2 in the rendered page. Confirm B-a and B-b still hold.
34. **Designer:** one re-audit pass (desktop, tablet and mobile together), one ordered fix list, at
    most one confirm pass.

## Suggested task split (planner decides)

- T-R1 [FE] items 1, 2 (fonts and tests). T-R2 [FE] items 3, 4 (tokens, focus, hover, motion).
  T-R3 [BE] item 32.
- T-R4 [FE] items 5 to 17 (shell and Triage). T-R5 [FE] items 18 to 22 (Library).
  T-R6 [FE] items 23 to 31 (Preview).
- T-R7 tester, then T-R8 designer re-audit. R1 and R2 come first. R3 runs in parallel. R4 to R6
  touch only `app.css`, so run them in sequence in one FE lane to avoid conflicts.
