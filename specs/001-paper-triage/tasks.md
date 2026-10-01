---
description: "Task list for Paper Triage Assistant"
---

# Tasks: Paper Triage Assistant

**Input**: `specs/001-paper-triage/` (plan.md, spec.md, research.md, data-model.md, contracts/api.md,
quickstart.md)

**Tests**: included (constitution II). Write the test first where cheap; every task ends with
`MOCK_LLM=1 uv run pytest -q` and `uv run ruff check .` green.

**Rules**: one task = one small commit (orchestrator commits). Paths are repo-relative.
Package = `src/paper_triage/` (abbrev `pt/` below means `src/paper_triage/`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizable (different files, no unfinished deps)
- **[USn]**: user story from spec.md

## Phase 1: Setup

- [x] T001 Create `pyproject.toml` (uv project `paper-triage`, Python >=3.11, deps fastapi, uvicorn,
  httpx, pydantic>=2, anthropic, pypdf; dev pytest, ruff; src layout; pytest `pythonpath=["src"]`,
  ruff line-length 100), `.env.example` (ANTHROPIC_API_KEY=, ANTHROPIC_MODEL=, MOCK_LLM=1,
  PAPER_TRIAGE_DB=), `src/paper_triage/__init__.py`, `tests/conftest.py` (sets `MOCK_LLM=1`,
  fixture `tmp_db` path), `tests/test_smoke.py` (imports package). Verify `uv sync` + pytest.
- [x] T002 Test first `tests/test_config_llm.py::test_config_*`, then `pt/config.py`: `Settings`
  read from env at call time: `model` (env `ANTHROPIC_MODEL`, default `"claude-opus-5-5"` – the
  only model id in code), `mock` (`MOCK_LLM=="1"`), `db_path` (default `./paper_triage.db`),
  `max_papers=20`, `default_papers=10`, `text_cap=40000`, `chat_top_k=20`.

## Phase 2: Foundational (blocks all stories)

- [x] T003 [P] Test first `tests/test_models.py`, then `pt/models.py`: Pydantic `Summary`,
  `WeakClaim`, `Overclaim`, `Critique` (basis Literal), `Rank` (validator clamps 0-10),
  `ChatAnswer`, `PaperOut` per data-model.md.
- [x] T004 MOCK LLM wrapper. Test first in `tests/test_config_llm.py`, then `pt/llm.py`:
  `LLMClient` Protocol (`parse(system, user, schema)`, `text(system, user)`); `MockClient`
  (deterministic schema instances keyed by sha256 of `<paper id="...">` in prompt; chat text
  cites first `<paper id>` in context as `[id]`, returns `NOT_IN_STORED_PAPERS ...` when the
  question contains "out of scope" or no paper tags); `AnthropicClient` (lazy SDK import;
  `messages.parse(..., output_format=schema, output_config={"effort": "low"})` ->
  `parsed_output` (check installed SDK merges `output_config` effort with the parse format; if
  not, drop effort); text via `messages.create`; no temperature; `stop_reason=="refusal"` ->
  `LLMRefusal`; SDK errors wrapped as `LLMError`); `get_client()` returns mock when
  `MOCK_LLM=1`. Tests use a fake SDK object for AnthropicClient (no network, no key).
- [x] T005 [P] Test first `tests/test_db.py`, then `pt/db.py`: `connect(path)`, `init_schema`
  (papers, arxiv_cache, results, chat_turns per data-model.md), `upsert_paper`, `get_paper`,
  `cache_get/put`, `save_result`, `get_result(paper_id, topic)`, `list_results(topic)` (rank
  desc, failed last), `latest_topic()`, `top_papers(k)`, `paper_ids()`, `save_chat_turn`. Test
  persistence across reconnect.
- [x] T006 [P] Test first `tests/test_net.py`, then `pt/net.py`: `Throttle(min_interval=3.0,
  clock, sleep)` (injectable; test with fake clock that 3 calls are spaced >=3 s) and
  `make_http(mock: bool) -> (httpx.Client, Throttle)`: real client (timeout 20 s, follow
  redirects) + 3.0 s throttle, or `httpx.MockTransport` client serving `pt/fixtures/` + 0 s
  throttle (keeps SC-001 achievable). Add fixtures: `arxiv_search.xml`
  (Atom, 5 entries with ids, titles, authors, abstracts, pdf links), `sample.pdf` (minimal
  hand-written 1-page PDF, >500 chars of extractable text). Mock routing: arXiv query/id_list ->
  feed (unknown id -> empty feed); 4 PDF links -> sample.pdf; 1 PDF link -> invalid bytes.
- [x] T007 [P] Test first `tests/test_extract.py`, then `pt/extract.py`:
  `extract_text(pdf_bytes) -> str` via pypdf; `ExtractError` on failure or <500 chars;
  `prepare_for_llm(text, cap)` drops trailing "References" section (heading after 50%) and caps.
- [x] T008 [P] Test first `tests/test_input_parse.py`, then `pt/input_parse.py`:
  `parse_query(q) -> (topic, items)` per contracts/api.md (new/old arXiv ids, arxiv abs/pdf URLs
  -> normalized id, other URLs -> pdf items, rest -> topic; empty -> ValueError).

## Phase 3: User Story 1 – Triage a topic into a ranked list (P1) MVP

**Goal**: topic or ids/URLs -> ranked list with summary, critique, rank+reason.
**Independent test**: `MOCK_LLM=1`, POST `/api/triage` "diffusion distillation" -> 5 ranked results.

- [x] T009 [US1] Test first `tests/test_fetcher.py` (search), then `pt/fetcher.py` part 1:
  `search(topic, n)` and `by_ids(ids)` hitting arXiv API through injected client + shared
  `Throttle`; Atom parse with `xml.etree`; id/version normalization; `arxiv_cache` read-through;
  unknown id -> error entry `{"input", "reason": "not found"}`.
- [x] T010 [US1] Extend `tests/test_fetcher.py`, then `pt/fetcher.py` part 2: download PDF
  (throttled for arxiv.org), `extract_text`, store `full_text` + `basis="fulltext"`, else
  `basis="abstract"`; non-arXiv URL -> id `pdf:<sha256(url)[:12]>`, title from PDF `/Title` or
  URL basename, abstract = first 1,500 chars; unreachable URL -> error entry, others continue.
  Already-stored paper -> no download (test asserts zero requests). Upserts into `papers`.
- [x] T011 [P] [US1] Test first `tests/test_agents.py::test_summarizer*`, then
  `pt/prompts/summarizer.md` + `pt/summarizer.py`: `summarize(paper, client) -> Summary`; prompt
  wraps `<paper id basis>`, <=120 words, "not stated" rule.
- [x] T012 [P] [US1] Test first `tests/test_agents.py::test_critic*`, then
  `pt/prompts/critic.md` + `pt/critic.py`: `critique(paper, client) -> Critique`; skeptical
  reviewer; only supported claims; basis set from paper, not LLM.
- [x] T013 [P] [US1] Test first `tests/test_agents.py::test_ranker*`, then
  `pt/prompts/ranker.md` + `pt/ranker.py`: `rank(paper, summary, topic, client) -> Rank`;
  rubric anchors; empty topic -> "overall reading priority" wording; clamp.
- [x] T014 [BE] [US1] Test first `tests/test_pipeline.py`, then `pt/pipeline.py`:
  `triage(query, n, conn, http, llm) -> {topic, results, errors}`: parse -> fetch -> per paper
  summarize/critique/rank (one retry on validation error; `LLMError`/`LLMRefusal` -> result
  `failed` with reason, others continue); reuse existing (paper_id, topic) result; cap n<=20;
  return sorted per contracts/api.md.
- [x] T015 [BE] [US1] Test first `tests/test_api.py` (status, triage, papers, 422s), then
  `pt/app.py`: FastAPI app; startup opens db + `init_schema`; deps from `config`/`get_client`/
  `make_http`; `GET /api/status`, `POST /api/triage`, `GET /api/papers`; static mount at `/`.
- [x] T016 [FE] [US1] UI structure. Re-read DESIGN.md + PRODUCT.md first; apply frontend-design /
  impeccable guidance. `pt/static/index.html` + `pt/static/app.css`: one page, header with mock
  label slot, query input + submit on top, ranked list region, chat region (beside wide / below
  narrow, empty for now); system font stack, one accent, generous whitespace; semantic landmarks.
- [x] T017 [FE] [US1] `pt/static/app.js` triage flow (re-read DESIGN.md + PRODUCT.md): submit ->
  `POST /api/triage`; loading, empty ("No papers found"), and per-item error states; each row
  shows rank, title, id, reason at a glance, "abstract only" flag; critique in `<details>`
  (weak claims / overclaims / missing baselines / "not stated"); rows have `id="paper-<id>"`;
  fully keyboard operable.

## Phase 4: User Story 2 – Grounded chat (P2)

**Goal**: answers cite stored ids only; explicit refusals.
**Independent test**: stored fixture papers, mock mode: in-scope -> valid citations; out of
scope -> `refused: true`; empty store -> refused, LLM not called.

- [x] T018 [BE] [US2] Test first `tests/test_chat.py`, then `pt/prompts/chat.md` + `pt/chat.py`:
  `answer(question, conn, client) -> ChatAnswer`; empty store -> refusal without calling client
  (assert via spy); context = top-k papers as `<paper id title>` with abstract, summary,
  critique; regex `\[([^\[\]\s]+)\]` validation, strip unknown ids into `dropped_citations`;
  sentinel or zero valid citations -> `refused: true`.
- [x] T019 [BE] [US2] Extend `tests/test_api.py`, then `pt/app.py`: `POST /api/chat` (422 on empty
  question), persists `chat_turns`.
- [x] T020 [FE] [US2] Chat UI (re-read DESIGN.md + PRODUCT.md; frontend-design / impeccable):
  `pt/static/index.html`, `app.css`, `app.js`: question input + send; answers in an
  `aria-live` log; citations rendered as links to `#paper-<id>`; refusal is a distinct,
  calm, intentional state (not an error look); keyboard send.

## Phase 5: User Story 3 – Revisit earlier results (P3)

**Goal**: reload shows stored results without refetching.
**Independent test**: triage, new app instance on same db, `GET /api/papers` returns same list.

- [x] T021 [BE+FE] [US3] Extend `tests/test_api.py` (new TestClient on same db file returns same
  results, no fetch), then (re-read DESIGN.md + PRODUCT.md) `pt/static/app.js`: on load call `/api/status` (toggle mock label,
  show model) and `/api/papers` to render stored list.

## Phase 6: Polish

- [x] T022 [BE] E2E mock smoke `tests/test_e2e_mock.py`: with `MOCK_LLM=1`, no key, and
  `socket.socket.connect` monkeypatched to raise: status mock=true; triage topic -> 5 results,
  >=1 `basis="abstract"`; mixed ids+URL input; chat in-scope cites only stored ids; out-of-scope
  refused; 5-paper triage < 5 s (SC-001).
- [x] T023 [FE] UI polish + a11y (re-read DESIGN.md + PRODUCT.md; impeccable audit/polish): focus
  rings, contrast AA, `prefers-reduced-motion`, no motion-dependent info, narrow-width layout,
  anti-references checked (no gradient hero, no card grid, no chat gloss). Files
  `pt/static/*` only.
- [x] T024 [BE] `README.md`: what it does, setup (`uv sync`, `.env`), run (mock and live), test
  commands, arXiv rate-limit note, pypdf/PyMuPDF swap note, layout of runtime agents + prompts.
- [x] T025 [BE] OpenAI provider for LLM wrapper: `LLM_PROVIDER=anthropic|openai` (default anthropic,
  MOCK_LLM=1 wins), `OpenAIClient` (`OPENAI_API_KEY`, `OPENAI_MODEL`), `/api/status.provider`,
  `.env.example` + README, fake-SDK tests. Files `llm.py`, `config.py`, `app.py`, tests, docs.
- [x] T026 [BE] Live-run fixes: concurrent per-paper LLM work in `pipeline.triage()` (`TRIAGE_CONCURRENCY`,
  default 4, 1 = sequential; DB stays on calling thread; summarizer || critic) + `ranker.md` score
  calibration (5-8 typical, 9-10 rare). Tests, README, `.env.example`.

## Phase 7: v2 amendment (redesign, searching indicator, links, load-more, chat scope, browser e2e)

**Sources**: spec.md FR-008..FR-014, SC-002..SC-008, Clarifications "2026-10-01 (v2)";
plan.md "v2 Amendment" (incl. UI test hooks); contracts/api.md (authoritative shapes);
data-model.md; research R9-R12; brief `docs/design/brief-v2-redesign.md` (D1-D35, B1-B3).
Every FE task: re-read DESIGN.md + PRODUCT.md + the brief first; keep the textContent-only
rendering rule; keep the UI test hooks from plan.md. Every task ends with
`MOCK_LLM=1 uv run pytest -q` and `uv run ruff check .` green.

### Wave D — BE lane (no FE dependency)

- [x] T027 [BE] [US1] B1 source links (FR-014). Test first: `tests/test_pipeline.py` and
  `tests/test_api.py` assert every result item of `POST /api/triage` and `GET /api/papers` has
  `abs_url`/`pdf_url`: arXiv `2401.00001` -> `"https://arxiv.org/abs/2401.00001"` and
  `"https://arxiv.org/pdf/2401.00001"` (no version, https); a direct PDF URL item ->
  `abs_url is None`, `pdf_url == <input URL>`. Then: `pt/models.py` `PaperOut` adds
  `abs_url: str | None = None`, `pdf_url: str | None = None`; `pt/pipeline.py` adds
  `source_urls(paper_id, source, pdf_url) -> (abs_url, pdf_url)`, extends `_OUT_KEYS`/`to_out`
  and passes the paper's `pdf_url` in `triage()`; `pt/db.py` `list_results` also selects
  `papers.pdf_url`. Files: `pt/models.py`, `pt/pipeline.py`, `pt/db.py`,
  `tests/test_models.py`, `tests/test_pipeline.py`, `tests/test_api.py`.
- [x] T028 [BE] [US1] Mock feed for paging. `pt/fixtures/arxiv_search.xml`: grow to 15 entries
  `2401.00001`..`2401.00015` (ids, abstracts and PDF links of entries 1-5 unchanged; invalid-PDF
  id `2401.00005` kept; entries 6-15 have valid PDF links); every title contains one unique
  marker word (>= 6 letters, e.g. "Basalt", "Cobalt") that appears nowhere else in the feed;
  no entry contains the words "capital" or "france" (used by refusal tests);
  declare `xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"`. `pt/net.py`
  `_feed(ids, n, start)` returns `entries[start:start+n]` for searches (honours the `start`
  query param, default 0) and writes `<opensearch:totalResults>` = 15 for searches, = matched
  count for `id_list`. Test first `tests/test_net.py`: `start=10&max_results=5` -> ids
  `2401.00011`..`2401.00015`, totalResults 15; `start=15` -> 0 entries. Audit and fix tests
  that assumed "default 10 returns 5" (pin `max_results=5` or expect 10): `tests/test_api.py`,
  `tests/test_pipeline.py`, `tests/test_fetcher.py`, `tests/test_e2e_mock.py`.
- [x] T029 [BE] [US1] B2 offset paging (FR-013, contracts/api.md POST /api/triage). Test first
  `tests/test_fetcher.py`: `search(topic, n, offset)` sends `start=offset`; cache key
  `q:<terms>:<n>:<offset>`; total read from `opensearch:totalResults`; missing total -> fallback.
  `tests/test_pipeline.py`: topic offset 0 n 10 -> `offset 0, next_offset 10, has_more true`;
  offset 10 n 5 -> 5 results `2401.00011`..`2401.00015`, `next_offset 15, has_more false`;
  id query -> `next_offset None, has_more False`; id query with offset > 0 -> `ValueError`.
  `tests/test_api.py`: `offset` -1 or 1001 -> 422; id query + `offset: 5` ->
  `422 {"detail": "offset only applies to topic searches"}`; `FetchError` -> `has_more false`.
  Then `pt/fetcher.py` (`search(topic, n, offset=0) -> (papers, total)`; `fetch(topic, items,
  n, offset=0) -> (papers, errors, page)` with `page = {"next_offset", "has_more"}`),
  `pt/pipeline.py` (`triage(..., offset=0)` returns `offset`, `next_offset`, `has_more`),
  `pt/app.py` (`TriageIn.offset: int = 0`, range 0..1000).
- [x] T030 [BE] [US2] MockClient scope fix (FR-010, contracts/api.md mock rule). Test first
  `tests/test_config_llm.py`: with a chat prompt of two `<paper id title>` blocks and
  `<question>` "What is the capital of France?" -> text starts with `NOT_IN_STORED_PAPERS`;
  question containing paper B's title marker word -> `"... [B]"`; question naming id A ->
  cites A; no paper tags -> sentinel. Only the text inside `<question>...</question>` is matched
  against titles/abstracts inside `<paper>` blocks; stop words in `_MOCK_STOP_WORDS`; content
  word = lowercase, >= 4 letters. Then `pt/llm.py` `MockClient.text`. Update existing tests that
  relied on the old "out of scope" substring or on generic questions being answered
  (`tests/test_chat.py`, `tests/test_api.py`, `tests/test_e2e_mock.py`) to use a fixture title
  word for in-scope questions.
- [x] T031 [BE] [US2] B3 chat scope (FR-008-FR-010, contracts/api.md POST /api/chat). Test first
  `tests/test_chat.py`: `paper_ids=[]` -> refused, client spy not called; ids none stored ->
  refused, no call; a stored paper not in `paper_ids` never appears in the prompt (spy) and a
  citation of it lands in `dropped_citations`; a load-more id in the set can be cited.
  `tests/test_api.py`: missing `paper_ids` -> 422; 51 ids -> `422 {"detail": "paper_ids: at
  most 50 ids"}`; earlier-search scenario: triage topic (10), triage `2401.00001`, chat with
  `paper_ids=["2401.00001"]` asking `2401.00002`'s marker word (question = the marker word
  plus "?", nothing else, so no other word can overlap) -> `refused: true`,
  `citations: []`; `chat_turns` still stored. Then `pt/db.py` `papers_by_ids(conn, ids)`
  (paper + latest result per id, input order, unknown skipped), `pt/chat.py`
  `answer(question, paper_ids, conn, client)` (context = set only, citations validated against
  set, `NO_SET_TEXT` per contract), `pt/config.py` `chat_max_ids = 50`, `pt/app.py`
  `ChatIn.paper_ids: list[str]` (required, dedupe, max 50), `pt/prompts/chat.md` (context is
  the user's current result set; anything else -> sentinel).
- [x] T032 [BE] Playwright harness (constitution 1.1.0 I/II, research R12). `pyproject.toml`:
  dev dep `pytest-playwright`, pytest marker `e2e: real-browser tests (need chromium)`;
  `uv lock`; run `uv run playwright install chromium` once; `SETUP_LOG.md`: date, both commands,
  purpose, "browser download only at install time; tests run offline". `tests/e2e_harness.py`:
  `LiveServer` runs `uvicorn.Server` in a daemon thread on `127.0.0.1:${E2E_PORT:-8766}` with
  `MOCK_LLM=1` and a temp `PAPER_TRIAGE_DB`, app = `create_app()` wrapped in a test-only ASGI
  middleware that awaits `asyncio.sleep(self.triage_delay)` before `POST /api/triage`;
  `.url`, `.set_triage_delay(seconds)`; start waits for `GET /api/status` 200 (10 s timeout).
  `tests/conftest.py`: session fixture `live_server`, session override `base_url` ->
  `live_server.url`, fixture `offline_page(page)` that aborts and records every request whose
  host is not `127.0.0.1`/`localhost` and fails the test if any was recorded; browser tests skip
  with "chromium not installed: run `uv run playwright install chromium`" when the browser is
  missing. `tests/test_e2e_harness.py`: status via httpx (`mock: true`); triage with delay 1 s
  takes >= 1 s; `@pytest.mark.e2e` page `/` has title "Paper Triage" and zero external requests.
  `README.md`: test commands incl. `MOCK_LLM=1 uv run pytest -q -m e2e`. Files: `pyproject.toml`,
  `uv.lock`, `SETUP_LOG.md`, `README.md`, `tests/e2e_harness.py`, `tests/conftest.py`,
  `tests/test_e2e_harness.py`.
- [x] T033 [BE] API-level v2 smoke, offline (`tests/test_e2e_mock.py`, socket guard on):
  topic triage `max_results` 10 -> 10 results, all with `abs_url`/`pdf_url`, `has_more` true,
  `next_offset` 10; `offset` 10 + `max_results` 5 -> 5 new ids, `has_more` false (SC-008 API
  half); chat with the 15 ids and a title marker word cites only set ids (SC-002); "What is the
  capital of France?" refused; id-only set + question about another stored paper refused
  (SC-003); SC-001 timing kept.

### Wave D — FE lane (no new API needed)

- [x] T034 [FE] Static asset guard test first `tests/frontend/test_static_assets.py` (stdlib
  only, no browser): `pt/static/index.html`, `app.css`, `app.js` reference no external URL
  (no `http(s)://` in `src`/`href`, no `@import`, no `@font-face`, no `url(http`); the UI test
  hooks from plan.md that exist today are present in `index.html` (`#query`, `#submit`,
  `#paper-list`, `#question`, `#ask`, `#chat-log`, `#status`, `#alert`). Later FE tasks extend
  the hook list.
- [x] T035 [FE] [US1] Redesign shell (FR-012). Re-read DESIGN.md + PRODUCT.md + brief. Files
  `pt/static/index.html`, `pt/static/app.css`: brief D1 tokens (whole `:root`), D2 font stacks
  (no `@font-face`), D3 base/focus/forced colors, D4 shell + grid + skip links, D5 nav, D6 query
  band, D7 results header (`#results-count`, `#status` sr-only), D13 notes box, D22 chat panel,
  D23 `#chat-scope` element (fallback copy), D29/D30 empty-state markup, D31 alert surface,
  D32 mock badge, D33 breakpoints, D34 contrast, D35 target sizes. Brief section 0 deviations
  apply (system fonts, `#8e939c` input edge, 12px button radius, 32/48 spacing). Acceptance:
  T034 test green with `#chat-scope`, `#results-count` added to its hook list; manual check on
  port 8765 at 320/768/1024/1440 px, no horizontal scroll, keyboard reaches every control.
- [x] T036 [FE] [US1] [US2] Redesigned rendering in `pt/static/app.js` (+ `app.css`): D8 paper
  row, D9 rank block, D11 flags/failed rows, D12 disclosure (h4 sections), D13 notes, D24 turns,
  D25 citation chips (`a.cite`, `cite--off`), D26 refusal (`.turn__a--refused`), D27 chat error
  with "Ask again", D28 suggestions, D29/D30/D31 states, D35 keyboard (`/`, Escape). Chat requests
  already send `paper_ids` = ids of the rows shown (forward-compatible; the current server
  ignores the extra field), so the chat never breaks when T031 lands. Acceptance: T034 green;
  manual mock run shows ranked rows, critique disclosure, refusal and error states.
- [x] T037 [FE] [US1] Searching indicator (FR-012, SC-006), brief D14-D18. Files `index.html`
  (`#working`, `role="group"`, `aria-label="Triage in progress"`, hidden by default),
  `app.css` (cream card, 8-ray glyph, `ray`/`breathe` keyframes, verb transition, D17
  reduced-motion rules), `app.js` (show 300 ms after submit; verb loop every 2.4 s per D15;
  `m:ss` timer from `performance.now()`; note copy by elapsed time incl. mock copy; D16
  announcements in `#status`; results `aria-busy`; D18 busy state: `#submit` disabled
  "Triaging…", `#query` readonly, previous list `inert` + opacity .4; hidden and restored on
  success, zero results, or error). Acceptance: T034 extended to require `#working` with its
  role/label; manual mock run shows the card while running and removes it after.

### Wave E — FE lane (needs landed BE API) || BE README

- [ ] T038 [FE] [US1] Paper links (FR-014, SC-007), brief D10. Needs T027. `app.js` + `app.css`:
  arXiv rows render `a[data-link="abs"]` "arXiv page" and `a[data-link="pdf"]` "PDF" from
  `r.abs_url`/`r.pdf_url` (fallback derive per D10), `pdf` rows only `a[data-link="pdf"]`;
  `target="_blank" rel="noopener noreferrer"`, aria-labels per D10; `href` set only for
  `http:`/`https:` URLs; failed rows keep links. Acceptance: T034 green; manual mock check that
  hrefs equal `https://arxiv.org/abs/<id>` and `https://arxiv.org/pdf/<id>`.
- [ ] T039 [FE] [US1] [US3] Load 5 more (FR-013, SC-008), brief D19-D20 (D21 superseded by
  contracts/api.md). Needs T029, T037. `index.html`, `app.js`, `app.css`: result-set state per
  data-model.md; `#load-more` button + caption after the list; request `{query, max_results: 5,
  offset: nextOffset}`; exhaustion from `has_more` (not result count); append without
  re-sorting, dedupe by `paper_id`, `li.batch-sep` "Papers 11–15", `.paper--new` flash
  (reduced-motion variant), focus rule, `#status` announcements, `#results-count` update;
  loading state (`aria-disabled`, "Loading 5 more…", `.working--compact`), error state
  (`p.load-more__error` role=alert, "Try again"); only-duplicates page -> "No new papers in this
  batch." and button stays while `has_more`; hidden for item runs (topic `""`), during a full
  triage, when `has_more` false, or when 50 ids are shown. After reload (`/api/papers`):
  `nextOffset` = shown count, shown when topic non-empty. Acceptance: T034 green; manual mock
  run 10 -> 15 rows, then button gone.
- [ ] T040 [FE] [US2] Chat scope wiring (FR-008-FR-010), brief D23. Needs T031, T039. `app.js`,
  `index.html`, `app.css`: `paper_ids` = result-set ids (first page + load-more, max 50, display
  order); new search replaces the set; `#chat-scope` copy "Chatting about N papers from this
  search." / "… from your last run." (N = shown rows with status ok); empty set: "Run a search
  first…" and `#question`/`#ask` disabled; server refusals render per D26. Acceptance: manual
  mock run: "What is the capital of France?" -> refusal; title word of a shown paper -> cited.
- [ ] T041 [FE] Browser e2e specs `tests/frontend/test_e2e_browser.py` (`@pytest.mark.e2e`,
  fixtures `live_server`, `offline_page`, `base_url` from T032; selectors only from plan.md UI
  test hooks). Needs T032, T037-T040. Cases: (1) indicator: `set_triage_delay(1.5)`, submit
  "diffusion distillation" -> `#working` visible, then hidden within 10 s, 10 `li.paper`
  (SC-006); reset delay 0. (2) links: every arXiv row's `a[data-link="abs"]` href ==
  `https://arxiv.org/abs/<id>`, `a[data-link="pdf"]` href == `https://arxiv.org/pdf/<id>`,
  `target="_blank"`, rel contains `noopener` (SC-007). (3) load-more: click `#load-more` ->
  15 rows, unique ids, new ids `2401.00011`..`2401.00015`, then `#load-more` not visible
  (SC-008). (4) id search "2401.00001 2401.00002" -> `#load-more` not visible. (5) chat "What is
  the capital of France?" -> last `li.turn` has `.turn__a--refused` and no `a.cite` (SC-003).
  (6) id search "2401.00001", then ask with the marker word of `2401.00002`'s title (read from
  the earlier topic run; question = marker word plus "?" only) -> refused. (7) topic run, ask
  with a shown title's marker word ->
  `a.cite` whose id is in the shown list (SC-002). Every case: zero external requests.
  Acceptance: `MOCK_LLM=1 uv run pytest -q -m e2e` green offline.
- [ ] T042 [BE] `README.md` v2: result links, "Load 5 more", chat scoped to the current
  results, searching indicator, browser e2e setup (`uv run playwright install chromium`, see
  `SETUP_LOG.md`) and run command, `E2E_PORT`. Needs T033.

## Lanes (parallel build)
[BE] = backend-builder; [FE] = frontend-builder. Disjoint files: FE owns `src/paper_triage/static/**` + `tests/frontend/**`; BE owns the rest. T021 is split: BE commits the API test half first as "T021 (api): ...", FE then does the UI half and ticks the box as "T021 (ui): ...".
Waves: A (parallel) BE T018 -> T019 -> T021(api) -> T022 || FE T017 -> T021(ui). B: FE T020 (needs T019 landed) -> T023. C: BE T024 (README) last. Tester runs after each wave on both lanes.

v2 waves (spawn both lanes in one message; tester after each wave; failures go back tagged):

- **Wave D** (parallel, no cross-lane dependency):
  BE T027 -> T028 -> T029 -> T030 -> T031 -> T032 -> T033 ||
  FE T034 -> T035 -> T036 -> T037 (needs `docs/design/brief-v2-redesign.md`, landed e169b0f).
  FE T036 already sends `paper_ids` with chat requests, so the UI keeps working when BE T031
  makes `paper_ids` required mid-wave.
- **Wave E** (starts after Wave D passes the tester):
  FE T038 (needs T027) -> T039 (needs T029, T037, T038) -> T040 (needs T031, T039) -> T041 (needs
  T032, T037-T040) || BE T042 (needs T033).
- API handoff: BE records landed field names in "API facts" of
  `.claude/state/agents/backend-builder.md`; contracts/api.md is the source of truth. FE gaps
  are reported as `NEEDS-BE:`.
- Tester port 8766 (`E2E_PORT` default); FE manual and e2e runs use `E2E_PORT=8765`.

## Dependencies

T001 -> T002 -> {T003, T005, T006, T007, T008} ; T004 after T002+T003.
US1: T009 -> T010 (needs T005-T007); T011-T013 need T003+T004 (parallel); T014 needs
T008-T013; T015 needs T014; T016 -> T017 need T015.
US2: T018 needs T004+T005; T019 needs T015+T018; T020 needs T017+T019.
US3: T021 needs T017. Polish: T022 needs T019; T023 after T020+T021; T024 last.
v2: T027 -> T028 -> T029 (T029 needs T028 fixture); T030 -> T031 (T031 tests need T028 marker
words and T030 mock rule); T032 independent of T027-T031 but ordered after them in the BE lane;
T033 needs T027-T031. FE: T034 -> T035 -> T036 -> T037; T038 needs T027+T036; T039 needs
T029+T037+T038; T040 needs T031+T039; T041 needs T032+T037-T040; T042 needs T033.

## Parallel Examples

- Foundational: T003, T005, T006, T007, T008 together.
- US1 agents: T011, T012, T013 together.

## Implementation Strategy

MVP = Phases 1-3 (stop and validate quickstart steps 1-3). Then US2, US3, polish, README.
Story -> tasks: US1 T009-T017 (9), US2 T018-T020 (3), US3 T021 (1).
v2 (16 tasks, T027-T042): US1 T027-T029, T035-T039; US2 T030, T031, T036, T040; US3 T039;
cross-cutting tests/tooling T032-T034, T041; docs T042. Increment order: Wave D gives links,
paging and scoped chat at the API plus the redesigned UI with the indicator; Wave E wires the
UI to the new API and proves it in a real browser.
