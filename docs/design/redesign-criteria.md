# Redesign criteria: choosing a replacement DESIGN.md

Author: designer, 2026-10-03. Phase 1 of 2. Phase 2 scores the candidates from
`docs/research/redesign-design-md-options.md` against the rubric in section 5.

Inputs read: PRODUCT.md (with the Library section), DESIGN.md (Airtable), `docs/design/v3-library-brief.md`,
`docs/design/v3-audit.md`, `src/paper_triage/static/app.css` and the static JS/HTML (read only).
Contrast figures below were computed from the shipped tokens (WCAG 2.x relative luminance).

## 1. What this product is, for a design system

- **Mode: Operate** (impeccable terms). The user completes tasks: triage a pile, file papers, read and
  mark a PDF, question a paper. Expression must never hide the task, the state or a familiar control.
  Brand lives in precise details, not in surfaces.
- **Scene.** One researcher at a desk or on a laptop, sessions of 30 to 120 minutes, often in the
  evening. Most of the time is spent reading: ranked reasons, critiques, PDF pages, chat answers.
- **Tone** (PRODUCT.md): calm, precise, skeptical. Anti-references: AI-chat gloss, gradient hero,
  card grid of everything, dashboard clutter.
- **Three views on one page:** Triage (input, ranked list, chat), Library (rail, filters, rows),
  Preview (toolbar, PDF well, highlights and chat panel or sheet).

## 2. What the product needs from a design system

Each need lists the token or component roles a candidate must supply, or let us derive cleanly.

### 2.1 Reading comfort over long sessions
- A text face built for screens at 14 to 17px, with open apertures and a large x-height. It must hold
  up in paragraphs (reason, critique, chat answers) and in metadata.
- A prose role at 15 to 17px with line-height 1.45 to 1.6, and a measure of 60 to 75ch. The current
  DESIGN.md body is 14px/1.25, which is too tight for prose; FE had to invent `--type-reason` 16/1.5.
- A real neutral ladder: ink, body, muted and faint must be visibly different steps. Long reading
  needs metadata that recedes. Pure #000 on #fff is not required and is tiring; near-black on white or
  off-white is fine.

### 2.2 Data-dense ranked lists
- Row grammar, not cards: hairline dividers, small radii (2 to 8px), compact vertical rhythm
  (16 to 24px per row), controls at 32 to 40px in dense areas, 44px for primary touch targets.
- A small type scale with clear steps at 12, 13, 14, 16, 18-20 and one larger step (24-32) for
  view titles and rank numerals. Weight steps 400/500/600 are enough.
- Tags and filter chips: unpressed, pressed (with a non-colour cue), counts.
- A side rail pattern (240px) with current-item state, and a filter bar.

### 2.3 Score and rank display
- Rank 0 to 10 is the primary scan target. It needs tabular lining figures (`font-variant-numeric:
  tabular-nums` must work in the chosen face), a numeral size of 24 to 32px, and a meter or bar.
- The meter needs a quiet track and a strong fill, with contrast >= 3:1 against the track
  (WCAG 1.4.11). Colour coding by score band is optional; if used it must not be the only signal.
- A "failed" state for ranking and summarizing (today: coral text and outlined flag).

### 2.4 Citation chips and refusals
- Inline chips for paper ids and page refs (`[2401.00001]`, `p.3`). These need a monospace (or
  tabular) face, a compact chip shape that sits in running text without breaking line-height, a
  pressed state, and a "not in stored papers" variant (dashed, muted).
- Refusals must look intentional: a distinct calm surface (today cream), not an error colour.
- Mock or offline mode label: a badge role that reads as information, not warning.

### 2.5 PDF viewer chrome
- A toolbar of 40px controls: icon buttons, a page input, a zoom select, a split button
  (Highlight plus colour), text buttons. One height, joined controls.
- A neutral "well" behind pages, darker than the page, that stays calm for an hour of reading.
- A side panel (384px) with tabs, and a bottom sheet below 1024px.
- A selection popover with swatches, and a find row with results.
- Elevation: one shadow level for popover and sheet. No other shadows needed.

### 2.6 Three highlight colours on PDF pages
- Highlights are drawn on white PDF pages with `mix-blend-mode: multiply` at partial alpha, so black
  text stays black. They live on the page, not on the theme, so they are the same in light and dark.
- Requirements: three hues that are distinct from each other for common colour-vision deficiencies
  (yellow, a cool green/blue, a warm orange/pink is the safe trio), visible on white (fill contrast
  >= 1.3:1 against the page, ideally 1.4 to 1.6), and with ink text over them >= 7:1.
- They must not collide with the UI accent or with the error colour. A design whose accent is yellow
  or orange forces a highlight change.
- Colour is never the only signal (Library principle 3): names are printed in the list.
- Current values fall short: Yellow/Mint/Peach at 45% give fills of only 1.19, 1.22 and 1.32:1
  against white. They read as faint, especially Yellow on bright screens.

### 2.7 Chat
- Two chats (Triage over all papers, Ask this paper). Needs: question and answer turn styles (no
  bubbles required, no avatars), a pending state, an error line with retry, starters as buttons,
  sources list, sticky input row.
- No AI sparkle, no gradient, no glow. The answer is prose, styled like the critique.

### 2.8 Light and dark
- Light theme is required and is the default (PDF pages are white; triage is daytime work).
- Dark theme is wanted for evening sessions. A candidate that documents both themes scores higher.
  In dark, the PDF page stays white (or the user's PDF colours); only the chrome and well go dark,
  and the well must stay a mid-dark neutral so the white page does not glare.
- Shipping dark mode is new scope (planner task); this rubric only rewards a design that makes it
  cheap.

### 2.9 Accessibility
- Text pairs >= 4.5:1 (body, muted, links, chips, on-accent text). Large numerals >= 3:1.
- Control edges, meter fills, focus rings >= 3:1 against their background (1.4.11).
- A focus ring spec that works on light, dark and on the accent surface.
- State is never colour-only: pressed tags carry a check, saved carries a filled glyph and text.
- `forced-colors` must still work: the system should not rely on background colour alone to draw a
  control.

### 2.10 Motion
- Motion is light and functional: disclosure chevron, sheet in, row collapse, cited-row and new-row
  flash, the working glyph. Durations 150 to 250ms, one ease-out curve.
- All of it has a `prefers-reduced-motion` fallback that keeps the meaning (outline instead of flash).
- A candidate built on motion as identity (parallax, scroll scenes, spring physics) scores low.

## 3. The current DESIGN.md (Airtable) against v3

### Gets right
- Restraint fits the tone: white canvas, ink type, near-black primary, hairlines, flat surfaces,
  no gradients or glow. This is why the shipped UI already avoids every PRODUCT.md anti-reference.
- Modest weights (400 to 500, never bold for its own sake) read as calm and precise.
- 4px spacing base and a radius hierarchy (6 inputs, 10 cards, 12 buttons) map cleanly to tokens.
- Colour as full surfaces, not scattered accents: cream for working and refusal, coral for failure.
  The idea transfers well to "refusals look intentional".
- Text contrast is high everywhere (ink 16.9:1, body 11.8:1, link 5.8:1, coral 6.8:1).

### Gets wrong for v3
- **It is a marketing system.** About half its tokens have no tool use: the 96px section rhythm,
  signature coral/forest cards, pricing sub-system (Inter Display, pill buttons), logo strip, hero
  band, footer. `app.css` marks 21 tokens as `/* unused */`.
- **FE had to derive what a tool needs.** `--type-reason` (16/1.5), `--type-chip`, `--font-mono`,
  `--color-edge-input` (hairline #ddd is 1.36:1, too faint for a control edge), all motion tokens,
  layout widths. A good candidate supplies these.
- **The neutral ladder has no real steps.** Muted #41454d is 9.6:1 and body #333840 is 11.8:1;
  they look the same. Metadata does not recede, so rows feel heavier than they should.
- **Body 14px/1.25** is tuned for marketing captions, not for paragraphs read for an hour.
- **Sizes are too large for dense chrome.** 48px buttons with 12px radius, 16px button type. The
  Preview toolbar needed a 40px override and mobile still takes 4 rows (audit item 7).
- **No hover states by policy.** That is a documentation choice of the source, not a tool rule.
  Desktop rows, icon buttons and chips benefit from a quiet hover.
- **No dark theme, no motion, no state set.** No warning or error tokens beyond the coral card, no
  success use, no disabled spec.
- **Fonts are proprietary and not shipped.** Haas Grotesk is licensed; the stack falls back to
  Helvetica Neue on macOS and Segoe UI or Roboto elsewhere. The real typography differs by OS and
  is not designed.
- **Highlight colours were borrowed** from demo-card pastels. They are faint on PDF pages (see 2.6),
  and Yellow and the cream refusal surface sit close in hue.
- **Two near blues** (link #1b61c9, info #254fad, focus #458fff) plus ink primary. The focus ring
  is 3.17:1, just above the floor.

## 4. Constraints (binding on any candidate)

1. **Vanilla CSS custom properties.** The chosen DESIGN.md is translated to `:root` tokens in
   `app.css`. No Tailwind, no CSS-in-JS, no preprocessor, no framework, no build step.
2. **No CDN, no network fonts.** Any non-system font must be vendored as woff2 under
   `src/paper_triage/static/vendor/fonts/`, with its licence file next to it.
   - Licence must allow redistribution: SIL OFL 1.1 or Apache 2.0. Proprietary faces named by a
     candidate (Söhne, Haas, Circular, GT America, SF Pro as a web font, Graphik and similar) cannot
     be shipped. The candidate then needs a named open substitute, and its score reflects the loss.
   - Coverage: Latin plus Latin Extended (author names with diacritics), and basic Greek, because
     arXiv titles use α, β, λ. Tabular lining figures (`tnum`) are required.
   - Budget: at most 3 families (text, optional display or serif, mono), variable fonts preferred,
     about 250 KB woff2 total. `font-display: swap`, with metric-matched system fallbacks
     (`size-adjust`, `ascent-override`) so the layout does not jump.
   - A system-font stack is acceptable and costs nothing. It must still be specified per OS.
3. **No new runtime dependencies.** pdf.js stays the only vendored library.
4. **Product overlay is kept.** Whatever the source, these product roles survive and are re-mapped
   to the new tokens, not removed: rank numeral and meter, cite chip and its off variant, mock badge,
   refusal surface, working card, failure alert, PDF well, highlight trio, swatch popover, focus ring,
   motion tokens with reduced-motion fallbacks, forced-colors rules.
5. **Behaviour and copy do not change.** A redesign replaces the visual world. Layout topology,
   hash routes, copy strings, keyboard and ARIA contracts in the v3 brief stay as built.
6. **Modern evergreen browsers only.** `color-mix()`, `:focus-visible`, `dvh`, `light-dark()` are
   allowed.

## 5. Scoring rubric

### 5.1 Hard gates (fail any one and the candidate is out)

| Gate | Fails when |
|---|---|
| G1 Light theme | The system is dark-only and a light theme cannot be derived without inventing the palette. |
| G2 No gloss identity | The identity depends on gradients, glass, neon glow, or motion as decoration. |
| G3 Readable text | The identity depends on low-contrast text (for example light grey on white) that cannot reach 4.5:1 without losing its character. |
| G4 Not image-led | The brand is carried mainly by photography, illustration or 3D, and the system has little left without it. |

### 5.2 Weighted criteria (score each 0 to 4, multiply by weight / 4, total out of 100)

| # | Criterion | Weight | 4 looks like | 0 looks like |
|---|---|---|---|---|
| C1 | Register fit | 15 | Extracted from a product UI (app, docs, editor, dev tool) with app components documented | Pure marketing site: hero, sections, pricing |
| C2 | Density and list grammar | 15 | Compact scale (12 to 16px core), small radii, hairline rows, 32 to 40px controls, tables or lists documented | Big cards, 48px+ controls, generous section padding as the core rhythm |
| C3 | Reading comfort | 12 | Screen text face with a documented prose role (15 to 17px, 1.45 to 1.6), measure guidance | Only display and caption roles; tight line-height |
| C4 | Colour system | 12 | Restrained: neutral ladder of 5+ distinct steps, one accent, semantic set (error, warning, success, info) with on-colours | One brand colour and greys, or a many-hue palette with no roles |
| C5 | Dark theme | 8 | Light and dark both documented as token pairs | Light only, no guidance |
| C6 | Font portability | 10 | Fonts are OFL or Apache (or system), mono included, `tnum`, Greek and Latin Ext coverage | Proprietary faces with no close open substitute, identity depends on them |
| C7 | Accessibility headroom | 10 | Documented pairs meet 4.5:1 and 3:1, focus ring spec, states not colour-only | Pairs below AA, no focus spec |
| C8 | Highlight compatibility | 6 | Accent is cool or neutral; palette has, or leaves room for, 3 distinct page highlights | Accent is yellow or orange, or its tints would clash with highlights |
| C9 | Component coverage | 7 | Inputs, selects, tabs, chips, icon buttons, popover, dialog or sheet, badges, toasts or alerts | Buttons and cards only |
| C10 | Tone match | 5 | Calm, precise, skeptical; quiet hierarchy; nothing shouts | Playful, loud, hype, sparkle |

Total weight: 100. A full score is 100.

### 5.3 Scoring procedure for phase 2

1. Apply G1 to G4. Record a one-line reason for each excluded candidate.
2. Score survivors on C1 to C10 from the DESIGN.md text itself (tokens, components, prose), not from
   the brand's reputation. Note one line of evidence per criterion score.
3. Tie-breakers, in order: C1, then C2, then C6 (lower migration cost wins).
4. For the top pick and two alternates, give: font pairing (text, mono, optional display) with the
   vendored or system choice and licence; the token re-map for the product overlay (section 4.4); a
   highlight trio with computed fill contrast; and the list of sections of the source DESIGN.md to
   drop or rewrite (marketing parts, hover policy, imagery).
5. Phase 2 output: `docs/design/redesign-recommendation.md`. If the pick implies dark mode or font
   vendoring, flag it as planner work (`NEXT:planner`).

### 5.4 Adjustments every candidate will need (expect these; do not score them down)

- Replace marketing sections with the product overlay (section 4.4).
- Add a prose role if missing, and a chip role at 12 to 13px.
- Supply a control-edge colour >= 3:1 if the hairline is fainter.
- Redefine the highlight trio for multiply on white: target fills of 1.35 to 1.6:1 against white,
  with the swatch carrying a 1px edge >= 3:1.
- Add motion tokens and reduced-motion fallbacks if the source has none.
- Replace proprietary fonts with vendored OFL faces or a system stack.
