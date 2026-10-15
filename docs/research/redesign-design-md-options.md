# Redesign research: DESIGN.md options, fonts, prior art

Date 2026-10-03. Context: Paper Triage (local, single user, long reading sessions, dense lists, PDF viewer). Static guard forbids CDN/external URLs, so every font must be a vendored woff2.
Caveat: entry details below come from fetching each raw DESIGN.md through a summarizer. Hex and font names are probably right but re-check the raw file before the designer commits to tokens.

## 0. Current baseline
The repo `DESIGN.md` is `Airtable-design-analysis` (light, white canvas, ink `#181d26`, near-black pill CTA, Haas Grotesk + Inter Display). Haas is proprietary and cannot be vendored. It is a marketing-site extraction (coral/forest signature cards), which clashes with PRODUCT.md anti-references (card grid, gloss).

## 1. Collections that exist
| Repo | What | Notes |
|---|---|---|
| https://github.com/VoltAgent/awesome-design-md (MIT) | Main collection. API listing shows 74 dirs `design-md/<site>/{DESIGN.md,preview.html,preview-dark.html}`; README says 73 | Raw: `https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/<site>/DESIGN.md`. Site view: `https://getdesign.md/<site>/design-md`. `slack` exists on disk but is not in the README list |
| https://github.com/VoltAgent/awesome-claude-design | 68 DESIGN.md files, same getdesign.md source, framed for Claude Design | Subset-style; Notion, Linear, Mintlify present |
| Forks (djdev, lem85930, Mu-L, HSKIMRobert, Digiflex-solution /awesome-design-md) | Copies of the main repo | Nothing new; ignore |
| Format spec: Google Stitch DESIGN.md | 9 sections (theme, colour, type, components, layout, depth, do/don't, responsive, agent prompt) | Referenced in README |

Not in the repo (verified against dir list): Perplexity, Readwise, Obsidian, Arc, Zotero, any academic/arXiv site, Semantic Scholar. Closest reading-oriented entries: Claude, Notion, Mintlify, Wired, IBM, Cursor.

## 2. Shortlist (path = `design-md/<dir>/DESIGN.md`)
| Dir | Character | Mode | Palette | Type stack | Free/vendorable? | Density, components | Fit: reading / dense list / PDF viewer |
|---|---|---|---|---|---|---|---|
| `claude` | Warm editorial, magazine column | Light only (cream, dark navy for code) | canvas `#faf9f5`, card `#efe9de`, ink `#141413`, body `#3d3d3a`, muted `#6c6a64`, hairline `#e6dfd8`, accent coral `#cc785c` | Serif display Copernicus/Tiempos (proprietary); body StyreneB or Inter; mono JetBrains Mono | Display no; Inter + JetBrains Mono yes (OFL) | Airy; 8px buttons, 12px cards, 1px hairline, no shadows; body 14-16/1.55 | Reading: best. List: ok (needs tighter rows). PDF: cream chrome sits well next to white pages. Matches "calm, precise" tone |
| `notion` | Warm minimal, serif-free in extract despite README blurb | Light | canvas `#fff`, surface `#f6f5f4`, ink `#1a1a1a`, charcoal `#37352f`, slate `#5d5b54`, hairline `#e5e3df`, purple `#5645d4`, link `#0075de`; pastel tints | Notion Sans (Inter-based), fallback Inter; no mono defined | Inter yes | 16/1.55 body, 14 small; flat cards 12px with hairline; 8px buttons, 44px inputs | Reading good; pastel tints useful for highlight/tag colours; marketing hero bands irrelevant |
| `mintlify` | Docs-first: sidebar / prose / TOC 3-column | Light (dark code blocks) | canvas `#fff`, surface `#f7f7f7`, ink `#0a0a0a`, steel `#5a5a5c`, hairline `#e5e5e5`, mint `#00d4a4`, code `#1c1c1e` | Inter; Geist Mono | Both OFL | Dense 14/16px, 12px cards, 8px inputs, pill buttons | Reading good (docs prose). 3-column layout maps to list / reader / chat. Mint accent gives green-as-"good", watch score semantics |
| `ibm` | Carbon: enterprise, dense, square | Light (dark footer) | canvas `#fff`, surface `#f4f4f4`, ink `#161616`, muted `#525252`, blue `#0f62fe`, hairline `#e0e0e0`, error `#da1e28`, ok `#24a148` | IBM Plex Sans (OFL), no mono listed (Plex Mono is the pair) | Fully vendorable, one family | 0px radius, 1px hairlines, +0.16px body tracking, 2px underline focus | Dense lists: best. Reading: ok in Plex Sans, weaker without serif. Strong academic/engineer feel, strict a11y focus style |
| `cursor` | Calm warm editor brand | Light | canvas `#f7f7f4`, card `#fff`, ink `#26251e`, body `#5a5852`, hairline `#e6e5e0`, orange `#f54e00`; pastel timeline set `#dfa88f #9fc9a2 #9fbbe0 #c0a8dd #c08532` | CursorGothic (proprietary); JetBrains Mono | Mono yes, sans no | 40/44px controls, 8/12px radii, no shadows, weight 400 headings | Reading ok; the five scoped pastels are a ready muted highlight palette. Orange CTA too loud for skeptical tone |
| `linear.app` | Dense, technical, quiet | Dark only | canvas `#010102`, surfaces `#0f1011 #141516 #18191a #191a1b`, ink `#f7f8f8`, muted `#d0d6e0`, subtle `#8a8f98`, border `#23252a`, accent `#5e6ad2` | Linear Display/Text/Mono (proprietary) | No | 4-step surface ladder instead of shadows, 8px/12px radii, 14-16px/1.5 | Best source for an optional dark theme and for list density. Dark-only is a poor default for PDFs (white pages glare) |
| `raycast` | Near-black, hairline, keycap details | Dark only | canvas `#07080a`, ladder `#0d0d0d #101111 #121212`, text `#fff #cdcdcd #9c9c9d`, border `#242728`; accents `#ffc533 #ff6161 #59d499 #57c1ff` | Inter with `ss03`, 16/1.6 | Inter yes | 36px controls, 6/8/10px radii, keycap chips | Keyboard-chip styling fits "keyboard-reachable filing". Dark-only, same caveat |
| `vercel` | Stark black/white, engineered | Light (polarity-flip bands) | canvas-soft `#fafafa`, ink `#171717`, body `#4d4d4d`, mute `#888`, hairline `#ebebeb`, link `#0070f3`, error `#ee0000` | Geist + Geist Mono | Both OFL, smallest files | Tight, 6/8/12px radii, stacked shadows | Lists/ids/mono good; neutral. Reading is sans-only |
| `wired` | Magazine broadsheet | Light | `#fff`, `#f5f5f5`, `#000`, `#757575`, `#e0e0e0`, links `#057dbc` | WiredDisplay, BreveText (serif body), Apercu | None free; pattern only | 0px radius, hairline row separators, serif body 16-19px | Pattern worth copying: serif for narrative, sans for structure, row dividers for lists. Too loud as is |
| `stripe` | Light, weight-300, tabular figures | Light | `#fff`, `#f6f9fc`, ink `#0d253d`, indigo `#533afd`, hairline `#e3e8ee` | Sohne (proprietary), `ss01`; substitute Inter 300; `tnum` on all numbers | Substitute only | 12px cards, 6px inputs, soft blue shadows | Not for reading; only the `tnum` rule for score columns is useful |

Skipped as poor fit: marketing-only or loud brands (Slack aubergine, Sanity coral on black, Shopify, Spotify, automotive, retail).

Ranking hint (designer decides): 1 `claude` (reading mood) with `ibm`-style hairline density for lists and `linear.app`/`raycast` surface ladder as the dark theme; 2 `mintlify` (3-column docs layout); 3 `notion`; 4 `ibm` as the whole system. Light default recommended: PDFs are white pages.

## 3. Typography (self-hosted woff2, Latin subset, wght-only; sizes from jsdelivr package listings of Fontsource 5.3.0)
| Family | Role | License | Latin woff2 (normal / italic) | Notes |
|---|---|---|---|---|
| Inter (variable) | UI sans | OFL | 48.3 KB / 51.8 KB (opsz axis version 72.9 KB) | Has `tnum`, `ss01`, `cv` features (known, not fetched here). Default pick for UI |
| Literata (variable) | Reading serif, designed for screen text | OFL-1.1 | 52.5 KB / 53.7 KB | wght 200-900, opsz axis, `tnum`/`lnum`/`onum` (Fontsource). Best for long summaries and critique |
| Newsreader (variable) | Editorial serif, closest to the Claude look | OFL-1.1 (Production Type) | 58.1 KB / 64.5 KB | wght 200-800, `tnum`/`lnum` |
| Source Serif 4 (variable) | Neutral transitional serif | OFL-1.1 | 50.8 KB / 51.5 KB | wght 200-900; pairs with Source Sans 3 (size not measured) |
| IBM Plex Sans (static) | UI sans, academic tone | OFL | 400: 22.6 KB, 500: 24.2 KB, 600: 24.3 KB, 400 italic: 24.4 KB | Fits `ibm` entry exactly |
| IBM Plex Mono (static) | ids, page refs | OFL | 400: 14.7 KB, 500: 14.9 KB | Plex Serif exists; not measured |
| JetBrains Mono (variable) | ids, code | OFL | 40.4 KB / 43.0 KB | Slightly wide for arXiv ids; Plex/Geist Mono narrower |
| Geist (variable) | UI sans | OFL-1.1 | 29.4 KB / 31.0 KB | Matches `vercel` |
| Geist Mono (variable) | ids | OFL | 23.1 KB / 25.5 KB | Smallest mono |

Pairings (Latin normal only, plus italic where noted):
- A. Literata (reading) + Inter (UI) + Geist Mono or Plex Mono (ids): 52.5 + 48.3 + 23.1 = ~124 KB (~190 KB with Literata italic and Inter italic). Recommended for the `claude` direction.
- B. Newsreader + Inter + Plex Mono: ~121 KB.
- C. All Plex (Sans 400/500/600 + Mono 400/500): ~100 KB, one coherent family, matches `ibm`. No serif for summaries.
- D. Geist + Geist Mono: ~52 KB, matches `vercel`; no reading serif.
Gotchas: (1) the `opsz` builds are 1.5-2.5x larger; use the `wght` files. (2) Author names with diacritics need the `latin-ext` subset (extra file per family, not measured). (3) Use `font-variant-numeric: tabular-nums` on score, rank and page columns. (4) Reading measure 60-75ch; Readwise Reader defaults to 20px body, 1.4 line spacing, with line-width control (source below). (5) Serif only for summaries, critique and chat prose; sans for chrome and lists; mono only for ids.
Delivery: `npm pack @fontsource-variable/<name>` or `@fontsource/<name>`, copy `files/*-latin-wght-normal.woff2` into the vendor dir, write `@font-face` locally.

## 4. Prior art
| Tool | Paper list / reader | Annotation colours | Takeaway |
|---|---|---|---|
| Zotero 7 | 3-pane app (collections, items, item pane; known layout, not fetched); PDF reader with annotation sidebar; annotations can be extracted to notes with page links | 8 colours: yellow `#ffd400`, red `#ff6666`, green `#5fb236`, blue `#2ea8e5`, purple `#a28ae5`, magenta `#e56eee`, orange `#f19837`, gray `#aaaaaa`; reader themes Snow `#ECEFF4`, Sepia `#F4ECD8`, Dark `#2E3440`. Users ask for labelled colours (forum) | Three colours is enough; pair colour with a label or shape. Find-all uses magenta tint, current match green |
| Readwise Reader | Library list with status dots; long-form view hides action bar; font, size 14-80px (default 20), line spacing (default 1.4), line width, light/dark/auto | Docs say no multi-colour highlights; use highlight tags. Shortcuts H, T, N, Shift+N | Reading controls to copy: size, spacing, width. Tags over colours supports "colour never the only signal" |
| Semantic Scholar / Semantic Reader | In-page citation cards with TLDR, AI skimming highlights labelled Goal / Method / Result with opacity and count controls, side panel, dotted-underline definitions, Hypothesis annotations | Skim highlights by category, user-controlled intensity | Label-based, not colour-only highlights; AI marks must be visibly distinct from user marks |
| Elicit | Table-first: one row per paper, user-editable columns, quotes and reasoning per cell, sort | n/a | Dense table view of rank/score with sortable columns is accepted prior art for triage |
| Consensus | Consensus Meter: yes / no / possibly aggregate over first 20 results | n/a | Verdict as a labelled word, not only colour |
| Scholarcy | Summary flashcards, section split (intro/methods/results), "Robo-Highlighter" | Auto highlights | Section-chunked summary is familiar; avoid flashcard gimmick |
| Notion databases | Views: table, board, list ("very clean, minimal"), gallery; filters AND/OR, sort, group, side/centre peek | Select/multi-select tags with colour | List + side peek maps to list + reader; multi-select tags with AND filter matches Library tag filter |

## Recommendation (one line)
Light-default Claude-like system (warm canvas, hairlines, no shadows, serif reading text) with Literata + Inter + Plex/Geist Mono vendored at ~125 KB, a surface-ladder dark theme borrowed from Linear/Raycast, tabular numerals for scores, and highlights that always carry a label or shape.

## Sources
- https://github.com/VoltAgent/awesome-design-md and `https://api.github.com/repos/VoltAgent/awesome-design-md/contents/design-md`
- https://github.com/VoltAgent/awesome-claude-design
- Raw files: `https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/{claude,notion,linear.app,mintlify,vercel,raycast,cursor,wired,ibm,stripe,slack,sanity}/DESIGN.md`
- Font sizes: `https://data.jsdelivr.com/v1/packages/npm/@fontsource-variable/{inter,literata,newsreader,source-serif-4,jetbrains-mono,geist,geist-mono}@5.3.0?structure=flat` and `.../@fontsource/{ibm-plex-sans,ibm-plex-mono}@5.3.0?structure=flat`
- Licences/features: https://fontsource.org/fonts/literata , /newsreader , /source-serif-4 , /geist
- Zotero colours: https://raw.githubusercontent.com/zotero/reader/master/src/common/defines.js ; reader docs https://www.zotero.org/support/pdf_reader
- Readwise: https://docs.readwise.io/reader/docs/faqs/highlights-tags-notes , https://docs.readwise.io/reader/docs/faqs/appearance
- Semantic Reader: https://www.semanticscholar.org/product/semantic-reader
- Elicit/Consensus: https://support.elicit.com/en/articles/1418881 , https://consensus.app/home/blog/introducing-the-consensus-meter/
- Scholarcy: https://www.scholarcy.com/
- Notion views: https://www.notion.com/help/views-filters-and-sorts

## Clarification questions
1. Light default only, or light plus dark theme?
2. Is a serif for summary/critique prose acceptable, or sans only?
3. Is a ~125 KB vendored font budget acceptable, and is latin-ext needed for author names?
