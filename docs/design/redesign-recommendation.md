# Redesign recommendation: which DESIGN.md to adopt

Author: designer, 2026-10-03. Phase 2 of `docs/design/redesign-criteria.md`, scoring the shortlist in
`docs/research/redesign-design-md-options.md` (source: VoltAgent/awesome-design-md, MIT).
**Caveat.** The candidate tokens came through a summarizer and were not checked against the raw files.
Contrast figures below are computed from those reported hex values. Any Carbon value marked (C) comes
from the public Carbon system, not from the extract. Re-check both against the raw file before building.

## Decision (user delegated the choice)

**Final pick: `ibm` (Carbon).** It is light only for this redesign, uses sans only (IBM Plex Sans plus
IBM Plex Mono, vendored woff2), and loads `latin-ext` and `greek` through `unicode-range`. Cap: 250 KB.
Raw file for the researcher to fetch and verify:
`https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/ibm/DESIGN.md`
The alternates below are recorded for traceability only. They are not open options.

## 1. Ranked scores

Each criterion is scored 0 to 4. Weights: C1 15, C2 15, C3 12, C4 12, C5 8, C6 10, C7 10, C8 6, C9 7,
C10 5. Total = sum of (score x weight / 4), out of 100.

| Rank | Dir | Gates | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | C9 | C10 | Total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `ibm` | pass | 3 | 4 | 2 | 4 | 2 | 4 | 4 | 3 | 3 | 3 | **82** |
| 2 | `vercel` | pass | 2 | 3 | 2 | 3 | 2 | 4 | 2 | 4 | 3 | 3 | **68** |
| 3 | `notion` | pass | 2 | 2 | 3 | 3 | 1 | 3 | 3 | 4 | 3 | 4 | **66** |
| 4 | `mintlify` | pass | 3 | 3 | 3 | 2 | 1 | 4 | 2 | 1 | 3 | 3 | 65 |
| 5 | `claude` | pass | 2 | 2 | 4 | 3 | 1 | 3 | 2 | 2 | 2 | 3 | 61 |
| 6 | `wired` | pass | 1 | 3 | 4 | 2 | 1 | 1 | 3 | 4 | 1 | 2 | 55 |
| 7 | `cursor` | pass | 2 | 3 | 2 | 2 | 1 | 2 | 2 | 2 | 2 | 2 | 52 |
| 8 | `stripe` | pass (borderline G2) | 1 | 2 | 1 | 3 | 1 | 2 | 2 | 4 | 2 | 2 | 47 |
| out | `linear.app` | G1 fail | | | | | | | | | | | dark only |
| out | `raycast` | G1 fail | | | | | | | | | | | dark only |

Evidence behind the scores:
- **ibm**: Carbon is a product design system. It has the best density (0px radius, hairline rows, 32/40/48
  control sizes (C)), a full semantic set (error `#da1e28` 5.0:1, success, blue `#0f62fe` 5.0:1) and a real
  neutral ladder (ink 18.1:1, muted `#525252` 7.8:1, helper `#6f6f6f` 5.0:1 (C)). It has a strict focus
  spec. All fonts are OFL and come from one superfamily. Weak points: no serif for prose, and the extract
  is light only. Carbon g90/g100 dark themes exist (C).
- **notion**: Warm, calm, readable: 16/1.55 body, slate `#5d5b54` 6.8:1. Its pastel tints make good
  highlight material and the purple accent is cool. Against: it is a marketing extract (hero bands), it
  has two accents (purple and link blue, link only 4.57:1), no mono and no dark tokens.
- **vercel**: Geist and Geist Mono are the cheapest good pair (~52 KB). Neutral and engineered. Against:
  mute `#888` is 3.4:1 (fails AA), the polarity-flip bands are marketing, and shadows are stacked.
- **mintlify**: A good docs layout, but the mint accent `#00d4a4` is 1.9:1 on white and collides
  with the Mint highlight.
- **claude**: The best reading mood. But this product would end up looking like a Claude skin, which
  hits the PRODUCT.md anti-reference "generic AI-chat gloss". It is also the most common AI-generated
  look: cream ground, serif and terracotta. The coral `#cc785c` is 3.1:1 as text and sits close to
  Peach. The serif is proprietary and the system is light only.
- **wired, cursor, stripe**: Loud or marketing-only. Their fonts are proprietary (Breve, CursorGothic,
  Söhne). Stripe's weight-300 body text is poor for long reading.
- **linear.app, raycast**: Dark only, so they fail G1. They are still useful as a reference if a dark theme is
  wanted. The Carbon dark themes cover that need with less invention.

## 2. Final pick: `ibm` (Carbon)

- **Download:** `design-md/ibm/DESIGN.md` from https://github.com/VoltAgent/awesome-design-md
  (raw: `https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/ibm/DESIGN.md`).
  The designer adapts it into the root `DESIGN.md` (user-approved). Git keeps the Airtable version in history.
- **Fonts (OFL-1.1, vendored woff2, Fontsource 5.3.0):** IBM Plex Sans 400/500/600 (22.6 + 24.2 + 24.3 KB)
  plus IBM Plex Mono 400/500 (14.7 + 14.9 KB), about **100 KB** for Latin. Add `latin-ext` and `greek`
  subsets through `unicode-range`, so they load only when a name or title needs them. Sizes are
  unmeasured; expect about 60 KB more in total. Check that the Fontsource package ships the `greek`
  subset. If it does not, Greek letters fall back to the system font, which is acceptable.
- **What it gives this product:** a tool register by origin, not adapted from marketing. Ranked rows and
  the Preview toolbar get the densest, most consistent control grammar on the list. Metadata finally
  recedes (7.8:1 against 18.1:1, where today it is 9.6 against 11.8). Real error, success and info
  states replace the coral and cream workarounds. Mono ids and page refs come from the same
  superfamily. The skeptical, engineering tone fits the critic and ranker.
- **Must change to fit:**
  1. Drop marketing parts: dark footer, display sizes above 32px, photography and expressive bands.
  2. Type roles: prose 16/24 (Carbon body-long-02 (C)) for reason, critique and chat answers. Lists and
     chrome use 14/20 with +0.16px tracking, captions 12/16 with +0.32px. Headings at 400 and 600.
  3. Neutral ladder: ink `#161616`, body `#393939` (C), muted `#525252`, faint `#6f6f6f`. The
     placeholder uses faint, not Carbon `#a8a8a8`, which fails 4.5:1. The control edge is `#8d8d8d`
     (3.3:1, meets 1.4.11). Hairline `#e0e0e0` is for dividers only.
  4. Primary action becomes blue `#0f62fe`. Links use the same blue. Use one primary per view, as today.
  5. States: the failure card becomes a Carbon inline notification (light red field, 3px `#da1e28` left
     rule, red title). The refusal becomes an info notification (light blue field, 3px blue rule), so it
     reads as intentional, not as an error. The mock badge becomes an outlined blue tag. The working card
     becomes layer `#f4f4f4`.
  6. Score and citation: rank numeral in Plex Sans 32px with `tabular-nums`. The meter keeps a `#e0e0e0`
     track and a `#161616` fill (13.7:1). No colour bands. The cite chip uses Plex Mono 12px on `#e0e0e0`
     with a 2px radius, and its off variant is dashed `#8d8d8d`.
  7. Highlights: keep the names Yellow, Mint and Peach. The names are copy and stored data, so no
     migration is needed. Draw opaque fills with `multiply`, not 45% alpha: Yellow `#ffde66` (1.32:1 on
     white), Mint `#9fe0c0` (1.51:1), Peach `#ffc29e` (1.56:1). Ink on each fill stays at 11.6:1 or
     higher. Yellow cannot get darker and stay yellow, so its 1.32:1 is the ceiling. Swatches keep a
     1px `#8d8d8d` edge.
  8. Radius: 0 on buttons, inputs, cards, the sheet and the popover. Tags and chips may stay square or
     use the Carbon pill. Swatches stay round.
  9. Focus: Carbon 2px `#0f62fe` ring. On a blue button, use an inset 1px white ring inside it (C).
  10. Hover: allowed on desktop (Carbon hover tokens), which replaces the Airtable no-hover rule.
  11. Motion: Carbon productive easing `cubic-bezier(0.2, 0, 0.38, 0.9)` (C) at 110 to 240ms. Keep every
      existing reduced-motion fallback.
  12. Dark mode: not in the first wave (see Q1).

## 3. Alternate 1: `vercel` (Geist, minimal)

- **Download:** `design-md/vercel/DESIGN.md` (raw: `https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/vercel/DESIGN.md`).
- **Fonts:** Geist plus Geist Mono (OFL), about **52 KB**, the lightest option. Geist's Greek coverage is
  unverified; system fallback through `unicode-range` is acceptable.
- **Gives:** a stark, precise look in which ids and numbers look native. The cool neutral leaves the
  highlight trio clear.
- **Must change:** darken mute `#888` (3.4:1) to about `#666` (5.5:1). Drop the polarity-flip bands
  and keep one shadow level. Add a prose role (16/1.55). Check link `#0070f3` (4.55:1, marginal). Add
  semantic states beyond error. Dark mode can be derived from the inverse tokens.

## 4. Alternate 2: `notion` (warmer reading; pick if reading mood beats density)

- **Download:** `design-md/notion/DESIGN.md` (raw: `https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/notion/DESIGN.md`).
- **Fonts:** Inter variable (OFL, 48.3 KB) plus Geist Mono (OFL, 23.1 KB), about **71 KB**. Optional
  Literata (OFL, 52.5 KB) for prose. Notion Sans is Inter-based, so Inter stands in for it without loss.
- **Gives:** the calmest reading surface, warm neutrals, and generous prose. Its list and side-peek idea
  matches Library plus Preview.
- **Must change:** keep one accent (the blue link, darkened to about 5.5:1) and drop purple, or the
  reverse. Add a mono role and a chip role. Tighten the list rhythm to 14px rows, with 40px toolbar
  controls instead of 44px. Use the pastel tints only as highlight fills, not as tag colours (colour must
  not be the only signal). Drop hero bands. Add a control edge of at least 3:1, because the
  `#e5e3df` hairline is 1.28:1. Derive semantic states. Dark mode must be invented.

## 5. Researcher's questions: decided (user delegated)

1. **Light only, or light plus dark?** Decision: light only for this redesign. Add dark later as its own small
   wave, driven by `prefers-color-scheme` through `light-dark()` with no toggle, using Carbon g100
   tokens (C). The PDF page stays white and only the chrome and the well darken. Doing dark now
   roughly doubles the token and audit work and delays the swap.
2. **Serif for summary and critique prose?** Decision: no, sans only. Reasons,
   critiques and chat answers are short blocks. The long reading happens in the PDF, which is set in
   the paper's own font. Plex Sans at 16/24 is comfortable. A serif can be added later as Plex Serif 400 and 400 italic for
   prose roles only (about 50 KB, unmeasured). That is not part of this redesign.
3. **About 125 KB font budget, and latin-ext?** Decision: yes to both. The app is local, so the bytes cost almost
   nothing. The pick needs about 100 KB for Latin. Include `latin-ext` (Müller, Łukasz, Dvořák) and
   `greek` (α, β in titles) as `unicode-range` subsets, so they load only when needed. Cap the total at
   250 KB.

## 6. Next steps

1. **Researcher:** fetch the raw `ibm` DESIGN.md (URL above) into `docs/research/` and flag every token
   that differs from this note.
2. **Designer:** adapt it into the root `DESIGN.md` (user-approved). Drop the marketing parts and add
   the product overlay and the section 2 must-change items. Then write `docs/design/redesign-brief.md`,
   with the token map to every `app.css` role and the per-view deltas for Triage, Library and Preview.
3. **Planner** adds tasks (re-check with speckit-analyze):
   - [FE] Swap the tokens in the `app.css` `:root` and delete unused tokens.
   - [FE] Vendor the fonts in `static/vendor/fonts/`, with their OFL licence files and `@font-face`
     rules using `unicode-range` and metric fallbacks. Update the static no-external-URL guard test.
   - [BE] Check that `.woff2` is served as `font/woff2`, since Python `mimetypes` may lack it
     (NEEDS-BE if missing).
   - [FE] Restyle the components per view: radius, heights, notifications, buttons, focus, hover, motion.
   - [FE] Change the highlight fills to opaque plus `multiply`. Names and data stay the same.
   - Later, separate wave: [FE] dark theme from Carbon g100.
4. **Frontend-builder** rebuilds. The **tester** runs the full pytest and e2e suites plus a contrast
   check. The **designer** does one re-audit at 1440, 820 and 390 widths, then at most one confirm pass.
