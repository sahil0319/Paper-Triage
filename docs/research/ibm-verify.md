# ibm DESIGN.md: verification against docs/design/redesign-recommendation.md

Date 2026-10-03. Basis: `docs/research/ibm-DESIGN.md` (token extract, not a byte-exact copy; see header there). Verbatim copy needs `curl` by someone with a shell.

## 1. Token check
| Item in recommendation | In extract | Result |
|---|---|---|
| ink `#161616`, muted `#525252`, hairline `#e0e0e0`, layer `#f4f4f4`, blue `#0f62fe`, error `#da1e28`, success `#24a148`, info = blue | same | match |
| faint `#6f6f6f` (C) | `ink-subtle: #8c8c8c` (about 3.4:1 on white, fails 4.5:1 text) | MISMATCH, matters. Keep the recommendation's `#6f6f6f` override; do not use `ink-subtle` for text |
| body `#393939` (C) | no body token; `button-secondary` is only "charcoal" | not in file; keep as (C) |
| control edge `#8d8d8d` | not in file; `hairline-strong #161616` is used as input bottom underline, `hairline #e0e0e0` as card edge | not in file; keep as (C) |
| placeholder `#a8a8a8` fails | not in file | n/a |
| prose 16/24, +0.16px | body 16px, lh 1.50 (=24px), +0.16px | match |
| list/chrome 14/20, +0.16px | body-sm 14px, lh 1.29 (=18px), +0.16px | MISMATCH: 18px line, not 20px. Use 14/18 per file, or 14/20 as an explicit product choice (row height) |
| caption 12/16, +0.32px | 12px, lh 1.33 (=16px), +0.32px | match |
| headings at 400 and 600 | headline 32/400, card-title 24/400, body-emphasis 14/**600** | match. Display styles are weight **300** (76/60/42px): dropped, so Plex Sans 300 is not needed |
| radius 0 on controls and cards | none 0; scale xs 2, sm 4, md 6, lg 8, pill 9999; buttons, inputs, cards 0px | match. Tags/chips may use xs 2px or pill |
| focus: 2px `#0f62fe` ring; inset 1px white on blue button (C) | input focus = "2px primary outline + 1px hairline-strong underline"; no button focus spec | partial; button ring stays (C) |
| notifications (error/info), tags | no notification or tag component in file | not in file; (C) |
| hover allowed (Carbon hover tokens) | `blue-hover #0050e6`, `button-primary-pressed #002d9c`; no other hover tokens | partial; other hovers from Carbon (C) |
| easing `cubic-bezier(0.2,0,0.38,0.9)`, 110-240ms | no motion tokens | not in file; (C) |
| control heights 32/40/48 (C) | not in file; button padding 12px/16px, input 11px/16px | not in file |
| spacing 4px grid | 4, 8, 12, 16, 24, 32, 48, 96 | match |
| Plex Mono, `tabular-nums` | no mono or tabular rule in file | not in file; our addition |
| Extra in file, unmentioned | `semantic-warning #f1c21b`, `blue-60 #0043ce`, `blue-80 #002d9c`, `button-danger`, `inverse-*` | usable; warning yellow is near Highlight Yellow, do not use it as text or as a highlight |
| Marketing parts to drop | display 42-76px, footer (charcoal), customer-logo-tile, product-card 32px pad | as the recommendation says |

Mismatches that matter: (1) `ink-subtle #8c8c8c` is below AA for text; (2) body-sm line height is 18px, not 20px; (3) no notification, tag, hover, motion or control-height tokens exist, so those stay Carbon (C) values, not file values.

## 2. Plex fonts for vendoring
Licence: SIL OFL 1.1, https://openfontlicense.org. Upstream: https://github.com/IBM/plex (licence file in the repo root, path unverified). Vendor `LICENSE`/`license.txt` next to the fonts.

Two sources, both measured via jsdelivr package listings:

| Source | Version | Greek? | Notes |
|---|---|---|---|
| `@fontsource/ibm-plex-sans` | 5.3.0 | **No** (verified absent) | latin, latin-ext, cyrillic, plus others; ships `unicode-range` CSS |
| `@fontsource/ibm-plex-mono` | 5.3.0 | **No** (verified absent) | same; `/LICENSE` 5,299 bytes |
| `@ibm/plex-sans` (official) | 1.1.0 | Yes | `fonts/split/woff2/` = Latin1, Latin2, Latin3, Greek, Pi per weight; `fonts/split/woff2/license.txt` 4,360 bytes |

The recommendation's assumption "check Fontsource ships greek" resolved: it does not. Official `@ibm/plex-sans` has Greek.

Sizes (woff2, bytes):
| File | 400 | 500 | 600 |
|---|---|---|---|
| Sans latin (Fontsource) | 22,588 | 24,184 | 24,252 |
| Sans latin-ext (Fontsource) | 15,980 | 16,456 | 16,448 |
| Sans Greek (official split) | 8,832 | 9,008 | 9,072 |
| Mono latin (Fontsource) | 14,708 | 14,888 | n/a |
| Mono latin-ext (Fontsource) | 13,348 | 13,432 | n/a |

Totals: Sans latin 71.0 KB, Sans latin-ext 48.9 KB, Sans Greek 26.9 KB, Mono latin 29.6 KB, Mono latin-ext 26.8 KB. Sum = 203.2 KB, under the 250 KB cap. Latin core only = 100.6 KB. Official Plex Mono Greek: not checked (`@ibm/plex-mono`); drop it if absent, system fallback covers rare Greek in ids.

Download (build time only; no runtime URLs):
```
npm pack @fontsource/ibm-plex-sans@5.3.0 @fontsource/ibm-plex-mono@5.3.0 @ibm/plex-sans@1.1.0
# take from each tarball's package/files/ (Fontsource) or package/fonts/split/woff2/ (official):
#   ibm-plex-sans-{latin,latin-ext}-{400,500,600}-normal.woff2
#   ibm-plex-mono-{latin,latin-ext}-{400,500}-normal.woff2
#   IBMPlexSans-{Regular,Medium,SemiBold}-Greek.woff2  (exact official file names: list the tarball first)
```
Set `unicode-range` per `@font-face` (Fontsource's `latin.css`/`latin-ext.css` carry the ranges; Greek U+0370-03FF). Use `font-display: swap` and a metric-adjusted system fallback.

## Sources
- https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/ibm/DESIGN.md
- https://data.jsdelivr.com/v1/packages/npm/@ibm/plex-sans@1.1.0?structure=flat
- https://data.jsdelivr.com/v1/packages/npm/@fontsource/ibm-plex-sans@5.3.0?structure=flat
- https://data.jsdelivr.com/v1/packages/npm/@fontsource/ibm-plex-mono@5.3.0?structure=flat
- https://github.com/IBM/plex
