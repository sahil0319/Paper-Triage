# QA final pass (T001-T024, both lanes) 2026-10-01

Verdict: GREEN. No blocking failures. 1 advisory note, 2 minor FE/doc nits (no action required).

## Gates
| check | result |
|---|---|
| `uv run pytest -q` (MOCK_LLM=1) | 156 passed, 2.3 s |
| `uv run ruff check .` | All checks passed |
| tests/test_e2e_mock.py | passes inside the 156; blocks `socket.connect`, no key; 5-paper triage < 5 s (SC-001) |
| no-mistakes gate | skipped per instruction (not initialised) |

## Live smoke (MOCK_LLM=1, uvicorn :8766, temp DB, server killed after)
- GET /api/status -> `{"mock":true,"model":"claude-opus-5-5","paper_count":0}`.
- GET /api/papers empty -> `{"topic":"","results":[]}`.
- POST /api/chat on empty store -> refused, no citations (FR-010).
- POST /api/triage `{"query":"diffusion model distillation"}` -> 5 results, ranks 7,6,3,2,1 (desc), basis mix fulltext/abstract. Body field is `query` (not `input`).
- GET /api/papers after -> same 5, same order. Repeat triage -> still 5, paper_count stable (dedupe).
- Mixed `2301.00001 2301.00002 https://example.com/a.pdf` -> 1 pdf result (`pdf:e5beb0efa319`, 12 hex, FR-001a) + 2 `not found` errors; others continue.
- Chat in-scope -> `citations:["2401.00005"]`, refused false, dropped [].
- GET / 200 html; /app.css 200 text/css; /app.js 200 text/javascript. (`/static/*` is 404: assets are served at root, index.html uses relative `app.css`/`app.js`. Works; not a bug.)

## FE checks
- `npx impeccable detect src/paper_triage/static` -> exit 0, `[]` (no findings).
- app.css vs DESIGN.md tokens: primary #0066cc, focus #0071e3, ink #1d1d1f, ink-2 #333, hairline #e0e0e0, parchment #f5f5f7, chip #d2d2d7, black nav 44px, spacing 4/8/12/17/24/32/48, pill radius, 56/40/34 h1 steps at DESIGN breakpoints (1068/833/640), no shadows, no gradients, focus ring 2px solid focus-blue. Match.
- Deliberate / minor deviations (all acceptable):
  - Input border #7a7a7a (ink-muted-48) 1px, for WCAG 1.4.11 (4.29:1). DESIGN search-input has no border. Deliberate.
  - Disabled button text #4a4a4d, `rgba(0,0,0,.08)` hairline-soft (DESIGN lists this value), inline #cccccc (= body-muted). Fine.
  - Lead 21px/400 vs tagline 21px/600. Fine (lighter reads calmer).
- a11y (read html/js): lang=en; skip link; header/section/main/aside landmarks, each labelled; one h1 then h2/h3 in order; visible-hidden labels on both inputs, linked help via aria-describedby; form role=search; results `aria-busy` toggled; `#status` role=status polite; `#alert` role=alert; chat log `role=log`, `tabindex=0`; native button/input/details so keyboard works; 2px focus-visible ring; 44px targets; reduced-motion and forced-colors handled; all model/paper text via textContent (no innerHTML, XSS-safe); citations are links only for server-validated ids, dropped ids stripped; refusal styled as calm "Not covered by your papers" not an error. Static review only; no real browser run.
- Nit (FE, no action): skip link targets non-focusable `h2`; browsers still move the sequential focus start point.

## Repo hygiene / fresh clone
- `git ls-files`: src (modules, 4 prompts, fixtures, static), tests, pyproject, uv.lock, .env.example, README, specs, docs. No untracked files; only diff is `.claude/state/progress.json` (sentinel/orchestrator).
- `.env`, `*.db`, `.local/` ignored. `paper_triage.db` in project root: `git check-ignore` -> .gitignore:9 `*.db`; never in git history.
- No `sk-ant`/key literals outside tool-provided impeccable assets (earlier false positive on binary).
- pyproject: hatchling wheel packages `src/paper_triage`; prompts/fixtures live inside the package.
- README commands: `MOCK_LLM=1 uv run uvicorn paper_triage.app:app` verified equivalent (ran with `--port 8766`); `uv run pytest -q`, `uv run ruff check .` verified. `.env.example` cp step is trivial. Not done: literal `git clone` + `uv sync` (sandbox denied; clone/uv sync operations blocked). Risk low: uv.lock and all runtime files tracked.
- Ticks: tasks.md 24 ticked, 0 unticked. Every T001..T024 has a git commit (T013 x3 incl. checkpoint, T021 has api + ui commits, T023 impl + tick, T001/T005 incl. checkpoint).

## Spec coverage (specs/001-paper-triage/spec.md)
| item | covered by |
|---|---|
| US1 AC1 ranked list w/ title,id,rank,reason | test_pipeline/test_api/e2e, smoke, app.js row() |
| US1 AC2 critique one click, "Not stated" | details/summary in app.js; notStated(); mock canned "Not stated" |
| US1 AC3 exactly 3 items | test_triage_mixed_ids_and_pdf_url, e2e mixed |
| US2 AC1 cite stored ids | test_chat, e2e, smoke |
| US2 AC2 intentional refusal | test_chat sentinel, no-citation and unknown-id refusals; UI refusal state |
| US2 AC3 empty store refuses w/o model | test_empty_store_refuses_without_llm_call, smoke |
| US3 reload w/o refetch | test_new_app_instance_same_db..., loadStored() |
| Edges: abstract fallback, zero found, invalid id/URL, dedupe, retry once, mock label | test_fetcher, test_pipeline (retry, failed, zero found), app.js, mock-label |
| FR-001/001a cap 20 default 10 | app.py max_results 1..20; test_triage_n_limits_and_caps_at_20 |
| FR-002 rate limit | net.Throttle + test_search_throttled_and_cached |
| FR-003..006 | agents + 3 separate prompt files |
| FR-007 persistence/cache | db tests, test_fetch_reuses_stored_papers |
| FR-008 top 20 by rank | test_context_limited_to_top_k_by_rank |
| FR-009 citation validation | test_unknown_ids_dropped_known_kept; `dropped_citations` |
| FR-010, FR-011 | covered |
| FR-012 | static review (rank/reason visible, details, cite links, mock label, keyboard) |
| SC-001 < 5 s | e2e asserts < 5 s |
| SC-002 | test_chat_in_scope_cites_stored_ids_only, e2e |
| SC-003 | test_chat_out_of_scope_refused (api + e2e), test_chat sentinel. See note below. |
| SC-004 | whole suite offline; e2e blocks sockets |
| SC-005 one input one action | index.html single form + button |

Gaps: none blocking. No automated JS/browser test exists (FE verified by static read + served-asset checks only).

## Advisory note (not logged as failure): mock chat and out-of-scope questions
In mock mode the chat refuses only when the question contains the sentinel "out of scope" (MockClient). A natural question like "What is the capital of France?" or "recipe for banana bread" returns a canned answer citing a stored id (refused=false). Real mode is not affected: the model decides, and the chat layer additionally refuses any answer with no valid citation. SC-003 says "out-of-scope test questions", and all tests use the sentinel convention, so no criterion is violated. Impact is a demo wart in mock mode only. Optional improvement [BE]: document the sentinel in README, or have MockClient refuse when the question shares no token with any stored title/summary. Not required for DONE.

## T025 (c549b1a, OpenAI provider) - PASS
- `uv run pytest -q`: 167 passed (offline, fake SDK objects); `ruff check .`: clean.
- MOCK_LLM=1 + LLM_PROVIDER=openai, no key -> MockClient; /api/status `{mock:true, model:gpt-5-mini, provider:openai}`.
- openai, no MOCK, no OPENAI_API_KEY -> `LLMError: LLM_PROVIDER=openai but OPENAI_API_KEY is not set` (raised in create_app, so startup fails as README says). No key read/printed; no .env created.
- Default provider anthropic unchanged (AnthropicClient; status provider=anthropic, model claude-opus-5-5).
- OpenAIClient: APIError->LLMError, refusal/content_filter->LLMRefusal, no-parsed->LLMError, ValidationError propagates, text() returns content or "". Covered by tests.
- tasks.md T025 ticked, matches commit. README, contracts/api.md, .env.example consistent. No secrets/.env tracked.
- Failures: none.

## T026 (bc81813) concurrent triage + ranker calibration
- pytest full: 174 pass; ruff clean; e2e 6 pass; test_pipeline.py x3: 22 pass each (no flake).
- sqlite: _compute has no DB access; _save runs on calling thread in paper order. OK.
- TRIAGE_CONCURRENCY: ''->4, 0->1, -3->1, abc->4, 2.5->4, 8->8. OK.
- Order: results rebuilt from `papers` order after save. Failure isolation: LLMError/ValidationError caught per paper -> failed row with partials. OK. Non-LLM exceptions in a worker would propagate via fut.result() and abort the batch (pre-existing behavior, low risk).
- Behavior change: with concurrency>1 a summarizer failure still saves critique (partial); sequential mode does not. Spec has no FR on partials; acceptable.
- [BE] minor: tasks.md T026 claims `.env.example` updated; commit did not touch it (TRIAGE_CONCURRENCY only in README/tasks.md).
- No secrets in diff.

---

# QA final pass v2 (T027-T042, wave E + whole v2) 2026-10-01, HEAD 0abd7b4

Verdict: GREEN. All v2 acceptance criteria verified. 0 blocking failures; 4 low optional items (F-002..F-005 in docs/qa/failures.md).

## Gates (HEAD 0abd7b4; no dev servers running during runs)
| check | result |
|---|---|
| `uv run pytest -q` | 226 passed, 8.3 s |
| `uv run pytest -q -m e2e` x5 (twice full, then 3 more, plus each of the 7 browser cases alone) | 8 passed every time, ~4.3 s, no flake |
| `uv run ruff check .` | All checks passed |
| `npx impeccable detect src/paper_triage/static` | 3 findings: cramped-padding on `.intro` and flat-type-hierarchy (known false positives, wave D A1: computed padding-bottom 32px, h1 32px vs body 14px) + side-tab on `.paper--new` (F-003, real, low) |
| no-mistakes gate | not initialised (SETUP_LOG.md); pytest+ruff+e2e substituted |

Note: one e2e run failed while my own scratch server held port 8766 (harness probe passed against my server, which has no triage delay). Not a product bug; logged as F-005.

## e2e spec review (tests/frontend/test_e2e_browser.py, 7 cases)
Mapping to the five asks:
- Indicator visible during search then gone: `test_indicator_visible_during_search_then_gone` is real. It sets a 1.5 s server delay, asserts `#working` visible and `#empty` hidden, then `#working` hidden and 10 rows. Sanity: it fails when the delay is missing (observed via the port collision), so it is not tautological.
- Links: `test_every_arxiv_row_links_to_abs_and_pdf` asserts exact href for abs and pdf, `target=_blank`, `noopener` in rel, on all 10 rows. Gap: no direct-PDF (1 link) case (F-004).
- Load more: `test_load_more_appends_five_then_ends` asserts 10 -> 15, 15 unique, new set equals the 5 fixture ids, control hidden at the end. Good.
- No load-more for id search: `test_id_search_offers_no_load_more` passes `not_to_be_visible`; a valid negative paired with the positive in the previous test.
- Chat: out-of-topic refused (`.turn__a--refused`, 0 cites); out-of-set paper refused (word from 2401.00002, set = {2401.00001}); in-set answer cites only shown ids. Weaknesses: the last depends on earlier tests' stored data to be meaningful and does not assert the expected id; the out-of-set case has no positive control for the same word (F-004).
All 7 pass independently (`-k` per case), so no hidden order dependence for pass/fail.

## Own Playwright run (chromium, real mock server on 8766 via `python -m uvicorn`; delay cases via the tests/e2e_harness LiveServer on 8768; scripts in the session scratchpad, outside the repo)
Load more:
- Error: injected HTTP 500 -> `#load-more-error` "Could not load more papers. boom", button reads "Try again", list stays 10 rows and not inert, working-more hidden, `#status` cleared, request body `{query, max_results:5, offset:10}`. Click again -> 15 unique rows, error cleared, control hidden, caption "No more papers for “diffusion distillation”.". Network abort -> "Could not load more papers. Could not reach the server. Check that the app is running." with focus kept on the button.
- 50-row cap (routed synthetic pages): offsets 0,10,15,...,45; exactly 50 rows; control hidden; caption "Showing 50 papers, the most one search holds."; scope "Chatting about 50 papers from this search."; chat body `paper_ids` = the 50 shown ids in display order. A last page returning 3 extra rows is clamped to 50.
- Reload then load more: reload restores 15 rows ("from your last run."), control offered; click sends `offset:15`; status "No new papers in this batch. No more for this topic."; caption "No new papers in this batch. No more papers for “diffusion distillation”."; rows stay 15.
- Batch separator "Papers 11–15" present; count "15 papers · sorted by relevance within each batch".
- Race: new search while a load-more is pending: no duplicate ids, scope matches rows (stale response dropped).
- Mixed query (topic + id) -> 1 row, no load-more.
Chat scope: empty DB -> "Run a search first. Chat only answers from papers triaged here.", `#question` and `#ask` disabled, load-more hidden. After search -> "Chatting about 10 papers from this search." (15 after load more). Question about a loaded paper cites only that id, all within the shown set; request `paper_ids` = 15 shown ids.
Keyboard: skip links, query, submit, example chips; per row Tab order abs link, pdf link, critique summary. Enter on `#load-more` moves focus to the first new row (`paper-2401.00013`, tabindex -1); Shift+Tab/Tab continue normally (no trap). If the user moves focus to `#question` while loading, focus is not stolen. `aria-disabled=true` while loading.
Reduced motion (`reduced_motion=reduce`): no running animations in `#working`, verb text unchanged until ~5 s then swaps once with no animation (FR-012 says "static"; behavior is slow text swap; see checklist note), no progress element or percent, `.paper--new` animation none, scroll-behavior auto.
Widths 320/768/1440 (empty, 10 rows, 15 rows + chat turn): scrollWidth == clientWidth, no overflowing element. Targets below 40 px high at 320: external links 31 px and critique summary 32 px; all >= 24 px (WCAG 2.5.8, brief section "every interactive element >= 24x24").
Only console error seen: the 500 I injected on purpose. Pypdf stderr noise "invalid pdf header" comes from the bundled mock sample PDF; harmless.

## README v2 (T042) accuracy
- Contract facts match the API and UI: abs/pdf URL forms, `abs_url` null for direct PDFs, load-more 10 then 5 via `offset`/`next_offset`/`has_more`, 422 on offset > 0 with ids/URLs, chat scope = shown set max 50 via `paper_ids`, empty set refused without a model call, 1 to 3 minute note, port 8766 / `E2E_PORT`, chromium skip, `uv run playwright install chromium`.
- Commands: `uv run pytest -q`, `uv run ruff check .`, `uv run pytest -q -m e2e`/`MOCK_LLM=1 ...` work. `MOCK_LLM=1 uv run uvicorn paper_triage.app:app` fails in THIS checkout (`Failed to spawn: uvicorn`) because the local `.venv/bin/uvicorn` has a stale shebang pointing at `/Users/mahdisahil/Desktop/agentic-job-hunt/.venv/bin/python` (the ignored .venv was copied). Verified the README command on a clean env (`UV_PROJECT_ENVIRONMENT=<scratch> uv sync --offline`): server starts and shuts down cleanly. Local fix: `rm -rf .venv && uv sync`. Not a repo defect.
- Minor: README still says "Up to 10 papers per run" correctly; it does not mention the `impeccable detect` gate (checklist CHK028 gap).

## Checklist
specs/001-paper-triage/checklists/v2-requirements.md: ticked CHK001, 002, 006, 007, 009, 019-024 (11 of 28), each backed by spec/contract text plus the browser evidence above. Left open: CHK003, 004 (stop-word list only "e.g."), 005, 008, 010-018, 025-028 (spec gaps or decisions). Notes appended (scope line resolved, empty-state hidden during run, reduced-motion wording, detect findings).

## Findings
- F-002 [BE] low pre-existing: re-running an already stored topic does not update "last run"; reload then shows an older topic.
- F-003 [FE] low: `.paper--new` reduced-motion inset stripe trips impeccable `side-tab` (app.css:570).
- F-004 [FE] low: e2e gaps (no 1-link PDF case; order-dependent cites-only assertion; no positive control).
- F-005 [BE] low: harness does not detect a busy port.

## v2 re-verification after fixes (HEAD 568d480) 2026-10-01: GREEN, F-002..F-005 closed
- `uv run pytest -q`: 230 passed. `uv run pytest -q -m e2e` x3: 9 passed each (6.0-7.1 s), first combined run with the new harness. `ruff check .`: clean.
- `npx impeccable detect`: 2 findings, both the known wave D false positives (cramped-padding on `.intro`, flat-type-hierarchy). side-tab on `.paper--new` is gone.
- F-002 (6cd65e0): regression tests fail on pre-fix source and pass on HEAD; API repro returns the re-run topic as last run.
- F-003 (a04adfc): reduced-motion new row uses a cream background tint; the working verb stays static ("Triaging papers…"); no overflow at 320/768/1440.
- F-004 (568d480): direct-PDF e2e (1 link), refusal positive control, self-seeded cites-only. Residual: cites-only cannot detect a leak by itself because of the mock's first-match rule; the out-of-set refusal test covers it.
- F-005 (bbbe244): busy port raises `RuntimeError: port 8766 is already in use; stop that server or set E2E_PORT`.
- Servers killed (8766/8768 free).

## v3 final pass (HEAD 42fbfc3, 2026-10-03): GREEN

Run with `MOCK_LLM=1`, offline. Designer re-check: docs/design/v3-audit.md (17/20, toolbar accepted).

### Gates
- `uv run pytest -q` x2: 503 passed each (87 s). `uv run ruff check .`: clean.
- `uv run pytest -q -m e2e`: 138 passed in 14 of 15 runs (3 on port 8766, 12 more on E2E_PORT=8770). One run (run 3 of the first three) ended `1 failed, 137 passed`; the failing test name was not captured and 12 later runs plus 1 more set of 3 were all green. Logged as F-015 (accepted, watch).
- Static guard `tests/frontend/test_static_assets.py`: 16 passed.
- F-012 solo (`-k highlight_persists`): 3 of 3 passed. The earlier solo failure is gone.
- `npx impeccable detect src/paper_triage/static`: 4 findings, all known or accepted:
  1. `app.css:661` `[layout-transition] transition: height` is the accepted row-collapse (Library row collapses out after a move).
  2. `index.html` `[cramped-padding]` on `<section> intro`: known false positive.
  3. `index.html` `[cramped-padding]` on `<div> pv-tabbar` (border-bottom, children flush): new in v3, tab strip is meant to sit on the rule. Accepted with the toolbar decision in v3-audit.md.
  4. `index.html` `[flat-type-hierarchy]` body/h1/h2 all 16 px: known false positive (DESIGN.md compact scale).
- No-mistakes gate: SKIPPED. Still deferred; it needs a bare repo the user has not set up.

### Hygiene
- `git ls-files`: no `.db`, `.env`, `paper_triage_data/` or `pdfs/` content tracked (only `.env.example`). `.gitignore` covers `.env`, `*.db`, `paper_triage_data/` (`git check-ignore` confirms).
- Vendored pdf.js: `src/paper_triage/static/vendor/pdfjs/LICENSE` and `VERSION` tracked.
- tasks.md: T001-T065 all ticked; each has a matching commit subject in `git log`.
- `app.css` has one `rgba()` left, inside the `--shadow-button` token definition (F-013 closed).

### Live smoke (MOCK_LLM=1, uvicorn :8766, temp DB and data dir, killed afterwards)
Search "diffusion distillation" (10 rows) -> Save 2401.00001 -> Library row "PDF ready" -> tag chip `diffusion` filters to 1 -> create directory `network`, move (status "Moved to network.", directory_id set) -> Open preview, page 1 text layer ready -> highlight "Abstract" + note "smoke note" (GET /api/annotations returns it) -> Ask tab, starter "What is the main claim?" answers "Mock answer from this paper [p.1]." with a p. 1 cite chip (API body `pages:[1]`) -> "What is the capital of France?" refused, text "This paper does not cover that." -> unsave from the card with confirm: library total 0, annotations 404, `data/pdfs` empty. No off-host requests, no page errors.
Note: "real-API" was run against the app's own HTTP API with `MOCK_LLM=1` (the expected strings are mock-specific; no key used).
- Tab order at 390 px (real keyboard, `#pv-back` start). Failed state (2401.00005): back, `#pv-sheet-open`, critique summary, then wraps to browser chrome; controls row hidden. Ready state: back, `#pv-export`, `#pv-external`, prev, page input, next, zoom, find, highlight, colour, `#pv-sheet-open`, pages. Every in-preview step moves down or right (focus order = visual order). Export notes and Open PDF sit above the page controls.
- F-006..F-008 re-run on a fresh DB, normal and reduced motion: first search note hidden; load-more resets chat once ("Chat now covers 15 papers. Earlier questions were cleared."), status carries the sentence once, Ask stays enabled while a stale reply is held, stale reply dropped, new-scope ask sends 15 ids, stale settling while the new ask is pending keeps Ask disabled, 50-paper cap note, failed-rows note. No console errors.

### README v3 spot-check
Matches behavior: Save/"Saved" state and unsave confirm, PDF `pending/ready/failed` with "Not a PDF." for 2401.00005, tag example (`Diffusion models, for VIDEO generation` -> `diffusion, models, video, generation`, verified with `tags.keywords`), directories and move, viewer controls, 3 highlight colours, notes, lazy paper chat with `[p.N]` in the API body (UI renders it as a "p. 1" chip), refusal text, mock ids 2401.00001-15, sample.pdf. No discrepancies found.

### Failures
F-009, F-011, F-012, F-013, F-014 resolved; F-010 accepted deviation; F-015 accepted flake. No open [BE] items. See failures.md.

---

# v4 final pass (Carbon redesign, T066-T076) - HEAD 14af76e, 2026-10-04

Run in the main tree at HEAD. MOCK_LLM=1; e2e port 8766. The designer ran a read-only audit on 8767 in parallel; no collision.

## Results
| check | result |
|---|---|
| `pytest` full, run 1 / run 2 | 638 passed / 638 passed (about 109 s each) |
| `ruff check .` | clean |
| `pytest -m e2e` x3 | 231 passed x3 (about 102-109 s each) |
| Design e2e with `V4_SHOTS_DIR=<scratch>` (README command) | 85 passed; 9 screenshots written: `{triage,library,preview}-{390,820,1440}.png`. I viewed `triage-1440` and `preview-390`: Plex type, square controls, grey layer chat panel, sheet on "Ask this paper"; nothing off-spec |
| F-023 solo (`test_e2e_design.py -k opaque_fills`, 3 params) x12 | 12 of 12 runs passed (36 of 36 tests); the full design file also passed inside the e2e x3 runs |
| Static guard + font asset + design-token tests | 41 passed (`test_static_assets.py`, `test_design_tokens.py`) |
| `impeccable detect` | 10 findings + 1 advisory, all known or spec-mandated (see below) |
| No-mistakes gate | SKIPPED, as in v3: `.local/` holds only `wt-fix`, no bare repo exists |

## impeccable detect (HEAD)
- 6 `side-tab` hits: 3px rules on error and info notifications (DESIGN.md 8.5), the `.hl-item__quote` highlight-colour rule (T072), and the forced-colours rail bar (`Highlight`, D7). All spec-mandated.
- `intro` and `pv-tabbar` cramped-padding, `flat-type-hierarchy` (body, h1, h2 all 16px): known false positives from earlier passes.
- `plex.css:78` `Ibm Plex Sans Fallback`: the generated metric-fallback face from the vendored Plex CSS.
- Advisory: `input` `border-top rgb(0,0,0)` (UA default before styling). Low, accepted.
- Compared with the v4-start baseline (2 heuristic hits + 8 design-system advisories): the 8 colour/radius/font-size advisories are gone, and the old `layout-transition` row-collapse hit is gone as well.

## Real-API smoke (MOCK_LLM=1, uvicorn :8766, temp DB and data dir, killed)
Script run against the app's own HTTP API: status mock -> `POST /api/triage` "diffusion distillation" (10 ranked) -> save `2401.00006` (201, again 200) -> library item PDF `ready`, 3 pages -> `GET /api/library/pdf` 200 `application/pdf` -> `POST /api/paper-chat` answer "[p.1]" with `refused: false` -> paper-chat for an unsaved id 404 -> `POST /api/chat` over the 10 results cites `2401.00005` -> `app.css` references IBM Plex -> `/vendor/fonts/plex-sans-latin-400.woff2` served as `font/woff2` -> unsave 200. All 12 checks passed. Port 8766 free afterwards.

## Tasks and hygiene
- tasks.md: 76 of 76 tasks ticked, none open. The commit log has a subject starting with each of T001-T076.
- README v4 section matches reality: 8 woff2 files totalling 125,228 bytes ("about 125 KB"), Carbon light-only note, `V4_SHOTS_DIR` command works as printed (writes `<view>-<width>.png`). SETUP_LOG v4 line present.
- Hygiene: no `.env`, `.db`, `paper_triage_data`, tarball, zip or `.DS_Store` tracked (checked on the master tree listing). `.gitignore` covers `.env`, `*.db`, `paper_triage_data/`. Fonts and OFL licence text tracked.
- Untracked junk, not committed: a directory literally named `$S/` in the repo root (about 164 KB, contains `t72.png`, a stray screenshot from a mis-expanded shell variable in a UI check). Delete it before any commit. Not mine to remove (I only write under docs/qa). Logged as F-024, low.

## Failures
F-016 to F-023 all resolved (F-021, F-022 and F-023 verified in this v4 pass). F-024 (stray `$S/` dir) is open, low, hygiene only. No open [BE] items. No open [FE] product items.

## Verdict
v4 PASS. The suite is green (638 x2, e2e 231 x3), the design e2e is green and screenshotted, and the smoke is clean. The no-mistakes gate stays deferred (no bare repo).

## v4 audit fixes re-verify (HEAD 04b299b, 2026-10-04)

Fixes under test: fa4c533 (item 1), 7d6885f (item 2), 3f21547 (item 3), bf43594 (item 4), c32275c (item 5), 04b299b (item 6), from `docs/design/v4-audit.md`. Main tree at HEAD, port 8766. The e2e harness uses temp DBs; the smoke probes ran from a frozen copy of master with the harness temp DB and data dir, never `./paper_triage.db`. `specs/001-paper-triage/spec.md` has an uncommitted planner amendment (FR-030 (f), the "Not in your Library" h1); expected, left for the user to commit.

### Results
| check | result |
|---|---|
| `pytest` full, run 1 / run 2 | 646 passed / 646 passed (about 110 s each) |
| `ruff check .` | clean |
| `pytest -m e2e` x2 | 239 passed x2 |
| `test_e2e_design.py` x1 | 93 passed |
| `impeccable detect` | 10 findings + 1 advisory: identical to the v4 final baseline (same 6 spec-mandated side-tabs, 2 cramped-padding, flat-type, Plex fallback face, 1 advisory); nothing new |
| Mobile toolbar | 249px at 390 (limit 260); 105px at 820; 117px at 1280; `scrollWidth` equals the viewport at all three |
| Focus order | unchanged at 390, 820 and 1280: skip links, back, export, external, pager, page field, zoom, find, highlight, colour, sheet button |

### Item by item (probes with Playwright)
1. Rail count contrast, FIXED. Current item: count `rgb(82,82,82)` (ink-muted) on `rgb(224,224,224)` = 5.92:1. Hovered non-current item: `rgb(82,82,82)` on `rgb(232,232,232)` = 6.38:1. Current + hover stays 5.92:1. The idle count (ink-subtle `rgb(111,111,111)`) sits on the white canvas at 5.0:1. All at least 4.5:1.
2. Forced colours, FIXED. With `forced_colors=active` the current nav link has a 2px `Highlight` bottom border and the other link's is `Canvas` (white); same for `Highlights` / `Ask this paper` tabs (selected `Highlight`, other white), on both Triage and Library routes. With forced colours off the original blue and transparent borders are unchanged.
3. Preview back button, FIXED. `#pv-back` is transparent with a transparent 1px border, `link` text `rgb(15,98,254)`, 40px tall. Hover gives `surface-hover` `rgb(232,232,232)` and `link-hover` `rgb(0,67,206)` text, and the chevron follows (`currentColor`). Focus keeps the inset -2px `rgb(15,98,254)` outline.
4. Primary submits, FIXED. Directory-form submit (`Create` / rename `Save`) and `Save note` are `btn btn--primary btn--small`, 32px, `rgb(15,98,254)`. The note editor panel has exactly one visible primary button.
5. Spacing, FIXED. At 390px the gap between the Save button and the authors line is 12px (was 4px); `.confirm` has `margin-bottom: 12px` and sits 12px above the authors line.
6. Not-saved Preview, FIXED. Route `#/library/paper/9999.99999`: h1 text and `title` attribute are both `Not in your Library`; the document title stays `Preview · Paper Triage`. `.pv-stage > .empty` is 640px wide and centred (offset 0.0px at 1440), its title is 20px weight 400 (heading-sm). The Triage `.empty__title` is unchanged at 16px. Library load error (stubbed 500): h1 `Preview`, state title `Could not load your library.`.

### Failures
None. Observation only, not logged: on the library load-error path the h1 `title` attribute is not set (it only receives a value in the loaded branch), so a stale value can survive navigation from a not-saved paper. The visible h1 is correct. Cosmetic.

### Verdict
All six audit items verified fixed; suite green; no regressions. No servers left running.
