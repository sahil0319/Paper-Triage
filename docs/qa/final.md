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
