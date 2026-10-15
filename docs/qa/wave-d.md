# Wave D QA (v2 amendment, T027-T037)

Date 2026-10-01. Commit under test: 63fc73e. Result: GREEN, no blocking failures, 3 advisories.

## Suite
- `uv run pytest -q` (MOCK_LLM=1, offline): 219 passed (includes tests/frontend static-asset tests).
- `uv run pytest -m e2e -q`: 1 passed, 218 deselected (only the harness test exists; browser specs arrive in T041).
- `uv run ruff check .`: all checks passed.

## Live API smoke (port 8766, MOCK_LLM=1, temp DB, server killed afterwards)
| Check | Result |
|---|---|
| Topic triage items carry abs_url + pdf_url (FR-014) | PASS (`https://arxiv.org/abs/<id>`, `https://arxiv.org/pdf/<id>`) |
| offset 0, max_results 5 -> 5 results, next_offset 5, has_more true | PASS |
| Walk: offsets 0/5/10 -> 5/5/5; last page next_offset 15, has_more false | PASS |
| 15 unique ids over 3 pages, no duplicates (SC-008 API half) | PASS |
| ID query and URL query with offset 5 -> 422 `offset only applies to topic searches`; mixed topic+ID also 422 | PASS |
| offset 1001 -> 422; ID query offset 0 -> 200 | PASS |
| chat without paper_ids -> 422; 51 ids -> 422 `paper_ids: at most 50 ids`; 60 duplicate ids -> 200; empty question -> 422 | PASS |
| chat paper_ids [] -> refused, no-results sentence | PASS |
| In-set question (content word, or in-set paper id) -> answered, citations subset of set | PASS |
| Question naming a paper stored from an earlier search but outside the set (id and title word) -> refused, no citations | PASS |
| "what is the capital of France?" -> refused ("The stored papers do not cover this."), no sentinel text, old advisory gone | PASS |
| Extra: unknown stored ids only + off-topic -> no-results refusal | PASS |

## FE static and browser review (T035-T037)
Served assets on 8766: `/`, `/app.css`, `/app.js`, `/index.html` all 200 with correct content types.
No external URLs, fonts or `@import` in static/ (only the SVG namespace string in app.js). No `:hover` rules (matches brief section 0).
Own Playwright run (chromium, real mock server via `tests/e2e_harness.LiveServer`, `set_triage_delay(5.0)`, scratch script outside repo):
- Working card `#working` hidden before submit, visible ~0.6 s after submit, role=group, aria-label "Triage in progress".
- Card: cream rgb(245,233,212), radius 10px, padding 24px; verb "Fetching papers…"; timer ticks (0:03 after ~3 s); mock note "Mock mode: canned responses, usually a few seconds."
- `#status` (aria-live polite) "Triage started." then "10 papers ranked. Results below."; `.results` aria-busy true during run, false after.
- Verb rotates (2.4 s default; ~5 s under reduced motion). No progress bar or percentage elements.
- Card removed on results; no card on a no-delay run (no flash); card removed and `#alert` "Triage failed. ... Try again" on a stubbed 502; submit re-enabled.
- Prior list `inert` + opacity .4 during a re-run, restored after.
- `prefers-reduced-motion: reduce`: ray animation none (opacity 1), glyph animation none; with no preference: `ray` and `breathe` animations active.
- Zero external requests, zero console errors.
Contrast (computed from tokens): ink/cream 14.07, muted/cream 8.01, body/white 11.79, muted/white 9.62, white/primary 16.90, coral/white 6.81, edge-input/white 3.09 (>= 3), link/white 5.83. All pass.
`npx impeccable detect src/paper_triage/static`: 2 findings (see A1).

## Advisories (non-blocking; not logged in failures.md)
- A1 [FE] T035 low: impeccable detect reports `cramped-padding` on `.intro` and `flat-type-hierarchy` (h1 16px = body). Likely detector false positives: computed styles show `.intro` padding-bottom 32px, h1 32px vs body 14px (CSS uses `font: var(--type-title-lg)` shorthand and `padding-block`). Previous run (final pass) returned `[]`. Optional: expand to longhand properties to silence the detector.
- A2 [FE] T037 low: first run with an empty DB keeps the "Nothing triaged yet." empty-state block visible under the working card (src/paper_triage/static/index.html `#empty`, app.js startWorking). Brief D18 does not say to hide it; consider hiding `#empty` while running.
- A3 [BE] T030 info: mock chat cites the first set paper sharing a content word, so "Explain consistency models" cites 2401.00001 (title "...Diffusion Models") rather than 2401.00002 ("Consistency Models..."). Matches contracts/api.md ("first such paper"); noted as CHK005.
- Expected-pending, not failures: chat scope line still reads the pre-v2 "top 10 by rank" copy (T040); no source links and no Load 5 more in the UI yet (T038, T039); browser e2e specs (T041).

## Checklist
`specs/001-paper-triage/checklists/v2-requirements.md` (28 requirement-quality items, all left unchecked for the reviewer).

## Not run
no-mistakes gate (per-wave run; full gate on final pass). BE T042 (README) in progress in parallel, not tested.
