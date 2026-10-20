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
  `max_papers=20`, `default_papers=10`, `text_cap=40000`, `chat_top_k=20`. (Env naming of T001
  and T002 superseded by T077.)

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
  (Env naming and default provider superseded by T077.)
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

- [x] T038 [FE] [US1] Paper links (FR-014, SC-007), brief D10. Needs T027. `app.js` + `app.css`:
  arXiv rows render `a[data-link="abs"]` "arXiv page" and `a[data-link="pdf"]` "PDF" from
  `r.abs_url`/`r.pdf_url` (fallback derive per D10), `pdf` rows only `a[data-link="pdf"]`;
  `target="_blank" rel="noopener noreferrer"`, aria-labels per D10; `href` set only for
  `http:`/`https:` URLs; failed rows keep links. Acceptance: T034 green; manual mock check that
  hrefs equal `https://arxiv.org/abs/<id>` and `https://arxiv.org/pdf/<id>`.
- [x] T039 [FE] [US1] [US3] Load 5 more (FR-013, SC-008), brief D19-D20 (D21 superseded by
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
- [x] T040 [FE] [US2] Chat scope wiring (FR-008-FR-010), brief D23. Needs T031, T039. `app.js`,
  `index.html`, `app.css`: `paper_ids` = result-set ids (first page + load-more, max 50, display
  order); new search replaces the set; `#chat-scope` copy "Chatting about N papers from this
  search." / "… from your last run." (N = shown rows with status ok); empty set: "Run a search
  first…" and `#question`/`#ask` disabled; server refusals render per D26. Acceptance: manual
  mock run: "What is the capital of France?" -> refusal; title word of a shown paper -> cited.
- [x] T041 [FE] Browser e2e specs `tests/frontend/test_e2e_browser.py` (`@pytest.mark.e2e`,
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
- [x] T042 [BE] `README.md` v2: result links, "Load 5 more", chat scoped to the current
  results, searching indicator, browser e2e setup (`uv run playwright install chromium`, see
  `SETUP_LOG.md`) and run command, `E2E_PORT`. Needs T033.

## Phase 8: v3 amendment (save, Library, tags, directories, PDF preview, annotations, paper chat)

**Sources**: spec.md US4-US9, FR-015..FR-029, SC-009..SC-016, Clarifications "2026-10-03 (v3)";
plan.md "v3 Amendment" (touch map, design notes, v3 UI test hooks); contracts/api.md "v3
Library endpoints" (authoritative shapes, status codes, copy of server refusals);
data-model.md "v3 tables" (column rules); research R13-R18; brief
`docs/design/v3-library-brief.md` **Rev 2** (L1-L24). `pt/` = `src/paper_triage/`.
FR-008a is already shipped (F-006/F-007/F-008): no task. Every FE task: re-read DESIGN.md,
PRODUCT.md and the brief (Rev 2) first; textContent-only rendering; keep v2 and v3 UI test
hooks. Every task: tests first where cheap; ends with `MOCK_LLM=1 uv run pytest -q` and
`uv run ruff check .` green; one commit with only its own paths plus `tasks.md`.

### Wave F — BE lane (storage and API first)

- [x] T043 [BE] [US6] Tag normalizer (FR-021, R17). Test first `tests/test_tags.py`:
  `keywords("Diffusion models, for VIDEO generation")` -> `["diffusion", "models", "video",
  "generation"]`; surrounding punctuation stripped (`"(rag)."` -> `"rag"`), inner hyphen kept
  (`"self-supervised"`); 1-character tokens and stop words dropped; duplicates removed keeping
  first order; `""` and `"the of and"` -> `[]`. Then `pt/tags.py` `keywords(topic: str) ->
  list[str]` with a fixed English stop-word frozenset in the module.
- [x] T044 [BE] [US5] Multi-page fixture + mock PDF cases (R14, R16). Regenerate
  `pt/fixtures/sample.pdf` as 3 pages (< 50 KB, pypdf-readable): page 1 text identical to the
  current single page; page 2 contains the marker word "Quartzite"; page 3 contains
  "Obsidian"; neither marker appears on other pages or in `arxiv_search.xml`. Keep the
  generator as `pt/fixtures/make_sample_pdf.py` (stdlib only, writes raw PDF objects).
  Test first `tests/test_extract.py`: 3 pages; existing `extract_text` assertions still hold.
  `pt/net.py` mock: keep `2401.00005` non-PDF bytes; hosts ending `.invalid` -> 404 (already);
  `export.arxiv.org/pdf/<id>` served like `/pdf/` (host check). Audit tests that assumed one
  page.
- [x] T045 [BE] [US4] Config + Library schema/CRUD (data-model "v3 tables": directories,
  saved_papers, saved_tags). `pt/config.py`: `data_dir` from `PAPER_TRIAGE_DATA_DIR` (default
  `./paper_triage_data`), `pdf_max_bytes = 52_428_800`, `paper_chat_cap = 300_000`,
  `paper_chat_history = 6`. `pt/db.py` tables exactly per data-model (`name` "trimmed, 1..40
  chars", `name_key` "UNIQUE casefold", `directory_id` "ON DELETE SET NULL", tags PK
  `(paper_id, tag)` with `INSERT OR IGNORE`) and functions: `save_paper(conn, paper_id,
  snapshot, topic, tags) -> bool created`, `merge_tags`, `get_saved`, `list_saved` (saved_at
  desc), `saved_ids(conn, ids) -> set`, `delete_saved`, `create_directory`,
  `rename_directory`, `delete_directory -> moved count`, `list_directories` (A-Z by name_key,
  with counts), `move_paper`. Test first `tests/test_db.py`: idempotent save keeps snapshot +
  saved_at and merges tags; directory delete moves members to NULL; unique casefold names.
  `.gitignore` adds `paper_triage_data/`; `.env.example` adds `PAPER_TRIAGE_DATA_DIR=`.
- [x] T046 [BE] [US5] [US8] Files/pages/annotations schema + CRUD (data-model: paper_files,
  paper_pages, annotations; all `ON DELETE CASCADE` from saved_papers). `pt/db.py`:
  `set_file_status(conn, paper_id, status, **fields)` (`status` "pending | ready | failed"),
  `get_file`, `pending_files`, `put_pages(conn, paper_id, texts)`, `get_pages`,
  `create_annotation`, `update_annotation`, `delete_annotation`, `list_annotations` (order
  page, top, id), `annotation_count`. Test first `tests/test_db.py`: unsave cascades to file
  row, pages and annotations; `top` = min rect y (0 for notes).
- [x] T047 [BE] [US4] Library API (contracts "GET/POST/DELETE /api/library", "v3 change to
  POST /api/triage and GET /api/papers"). Test first `tests/test_library_api.py`: save after a
  mock topic search -> 201, item has snapshot fields, tags = `keywords(topic)`,
  `directory_id null`; save again with another topic -> 200 `created false`, original
  `saved_at`/rank kept, tags merged; item query topic `""` -> no tags; unknown pair -> 404;
  failed result -> 409; triage/papers items carry `saved`; a topic search returning a saved
  paper merges its tags; DELETE -> 200 with `annotations` count, then 404; `papers`/`results`
  rows survive. Then `pt/models.py` (`LibraryItem`, `PaperOut.saved`), `pt/pipeline.py`
  (`saved` flag, tag merge), `pt/app.py` routes. (PDF download wiring comes in T050; until then
  `pdf.status` stays `pending`.)
- [x] T048 [BE] [US7] Directories API + move (contracts "Directories", "POST
  /api/library/move"). Test first `tests/test_library_api.py`: create -> 201 count 0; empty
  name -> 422 "Enter a name."; 41 chars -> 422 "Names can be up to 40 characters."; duplicate
  (case-insensitive), "Unsorted", "All saved" -> 409 `"<name>" already exists.`; rename keeps
  members; delete -> `moved` n and members `directory_id null`; move to unknown dir -> 404;
  `GET /api/library` `directories` A-Z with counts, `unsorted_count`, `total`. Files
  `pt/app.py`, `pt/models.py`, `tests/test_library_api.py`.
- [x] T049 [BE] [US5] PDF store module (R14, contracts "PDF download rules"). Test first
  `tests/test_pdfstore.py` with the mock transport and a tmp data dir: arXiv paper -> file at
  `data_dir/pdfs/<sha256(paper_id)>.pdf`, row `ready`, `bytes`, `sha256`, `pages == 3`;
  `2401.00005` -> `failed` "Not a PDF."; body > `pdf_max_bytes` (monkeypatched small cap) ->
  `failed` "PDF is larger than 50 MB." and no file left; export host 404 -> falls back to
  `arxiv.org/pdf`; direct PDF URL uses `papers.pdf_url` and skips the throttle (assert the
  `Throttle` was not waited on); `.invalid` host -> `failed`; old id `math.GT/0107001` makes a
  safe file name; `sweep_pending` turns `pending` into `failed` "Download interrupted. Try
  again."; zero `paper_pages` rows after download. Then `pt/pdfstore.py` (`download`,
  `sweep_pending`, `delete_file`; stream with cap, `%PDF-` check, temp file + `os.replace`,
  connect 10 s / read 60 s, network outside the lock) and `pt/extract.py`
  `page_count(pdf_bytes)`.
- [x] T050 [BE] [US5] PDF API wiring (FR-018, FR-019). Test first `tests/test_library_api.py`:
  save -> background download done by TestClient -> `GET /api/library` shows `ready`, `pages
  3`; `GET /api/library/pdf?paper_id=` -> 200 `application/pdf` inline, Range `bytes=0-99`
  -> 206; failed paper -> 404 on pdf, `POST /api/library/retry` -> 202 then `ready`/`failed`;
  retry on `ready` -> 409; unsave deletes the file from disk; after `create_app()`,
  `mimetypes.guess_type("a.mjs")[0] == "text/javascript"`. Then `pt/app.py`: `BackgroundTasks` on new save and retry,
  lifespan creates `data_dir` and calls `sweep_pending`, `mimetypes.add_type`, FileResponse
  route with `Cache-Control: private, max-age=3600`.
- [x] T051 [BE] [US8] Annotations API (FR-025, FR-026; contracts "Annotations"). Test first
  `tests/test_annotations_api.py`: create highlight (color default "yellow", rects fractions
  0..1, quote 1..500) -> 201; color outside `yellow|mint|peach` -> 422; rect value 1.2 -> 422;
  0 or 51 rects -> 422; page > `pdf.pages` -> 422; PDF not ready -> 409; page note with note
  1..500 chars and `rects []` -> 201; note 501 chars -> 422; PATCH color/note; PATCH note ""
  on a note -> 422; DELETE -> 204 then 404; list ordered page, top, id; unsaved paper -> 404;
  `highlight_count` in `GET /api/library`; persists across app restart (new TestClient on same
  DB). Files `pt/app.py`, `pt/models.py`, tests.

### Wave F — FE lane (static or stubbed data only)

- [x] T052 [FE] Vendor pdf.js + static guard (constitution 2.0.0 I, R13). Test first
  `tests/frontend/test_static_assets.py`: scan every file under `pt/static/` except
  `pt/static/vendor/` for external URLs and forbidden APIs (`app.js` rule kept; `viewer.js`
  may use static `import` only, no `import(`); assert `vendor/pdfjs/{pdf.min.mjs,
  pdf.worker.min.mjs, LICENSE, VERSION}` exist, VERSION names `pdfjs-dist 6.3.289` (modern
  `build/`), and both `.mjs` files contain the same version string. Then download those two
  files + LICENSE once from the npm registry tarball (`pdfjs-dist-6.3.289.tgz`) and write
  VERSION with source URL and sha256 of each file. Files `pt/static/vendor/pdfjs/**`,
  `tests/frontend/test_static_assets.py`.
- [x] T053 [FE] [US5] Shell, nav and hash routes (brief L1, L2, sections 5-7). `pt/static/index.html`:
  `nav.views` with `a[data-view="triage"]`, `a[data-view="library"]` + `.views__count`;
  empty `#library` and `#preview` sections (hidden), per-view skip links; `app.js` router for
  `#/`, `#/library?dir=&tags=&q=`, `#/library/paper/<encoded id>`: toggles `hidden`, keeps
  triage state in memory, sets `document.title`, focuses the view heading, announces via
  `#status`. `app.css` per brief. Test `tests/frontend/test_e2e_library.py` (`e2e`): Back/
  Forward switch views without re-fetching triage results. Returning from Preview to Library
  restores the hash filters and the list scroll position and focuses that paper's `Open
  preview` (FR-024, brief L2).
- [x] T054 [FE] [US4] Save toggle on result rows (FR-015..FR-017; brief L3-L6 Rev 2).
  `app.js` + `app.css`: `.paper__head` with `button.save[aria-pressed]` (not on failed rows);
  states Save/Saving…/Saved/Removing…; renders `saved` from triage and papers responses;
  click Save -> `POST /api/library {paper_id, topic}`; click Saved -> always the inline confirm
  `[data-confirm="unsave"]` (copy per L6 with highlight count when known) -> `DELETE
  /api/library?paper_id=`; errors per L5; nav count update; announcements. e2e with
  `page.route` stubs shaped per contracts: save, saved-on-load, confirm/keep, confirm/remove,
  error line.
- [x] T055 [FE] [US5] Viewer shell (FR-019, FR-024; brief L15-L17, L21). New ES module
  `pt/static/viewer.js` (static import `./vendor/pdfjs/pdf.min.mjs`, worker
  `/vendor/pdfjs/pdf.worker.min.mjs`): open `#/library/paper/<id>` -> `getDocument({url:
  "/api/library/pdf?paper_id=<id>"})`; `section.pdf-page[data-page]` per page with canvas +
  `.textLayer` rendered near the viewport only; toolbar back, title h1, `#pv-page-input`
  ("page n of m", prev/next, clamp), `#pv-zoom` (fit width default, fit page, 50-200%),
  "Open PDF in new tab"; viewer keyboard keys `+ - 0 n p`; states Opening / Downloading /
  Unavailable / Render failed / Not saved per L21. e2e with `page.route` serving
  `pt/fixtures/sample.pdf` and a stub library item: canvas count >= 1, text layer contains a
  page-1 word, next page and zoom change page width, zero non-local requests.
- [x] T056 [FE] [US5] Find in paper (brief L24, R18). `viewer.js` find row: input, count
  `<n> matches on <p> pages`, result buttons `Page N: …snippet…` from
  `page.getTextContent()`, activate -> jump + outline; disabled until ready. e2e (stubbed PDF):
  finding a page-1 word lists page 1; nonsense -> "No matches.".

### Wave G — BE lane (paper chat, harness)

- [x] T057 [BE] [US9] Page extraction + MockClient page mode (R16). Test first
  `tests/test_extract.py`: `extract_pages(sample.pdf)` -> 3 strings, page 2 contains
  "Quartzite"; `tests/test_config_llm.py`: prompt with `<page n="1">..</page><page n="2">
  ..Quartzite..</page>` and `<question>Where is quartzite discussed?</question>` ->
  `"Mock answer from this paper [p.2]."`; "What is the capital of France?" -> starts with
  `NOT_IN_STORED_PAPERS`; results-chat mock behaviour unchanged. Then `pt/extract.py`
  `extract_pages`, `pt/llm.py` `MockClient.text` page mode (prompt contains `<page n=`).
- [x] T058 [BE] [US9] Paper chat agent + endpoint (FR-027, FR-028; contracts "POST
  /api/paper-chat"). Test first `tests/test_paper_chat.py`: after save + list + pdf fetch +
  annotation calls there are zero `paper_pages` rows and zero LLM calls (spy client); first
  question with "Quartzite" -> `pages [2]`, rows now stored; "capital of France" -> refused;
  model answer citing `[p.9]` -> `dropped_pages [9]`, refused when no valid page; PDF pending
  or failed -> refused "Chat needs the PDF text. It is not ready yet." with no LLM call and no
  extraction; all-empty pages -> "This PDF has no extractable text."; `history` > 6 turns ->
  422; unsaved -> 404; LLM error -> 502; annotations never appear in the prompt (spy). Then
  `pt/paper_chat.py` (context `<page n>` blocks, 300,000-char cap, history, `[p.N]`
  validation), `pt/prompts/paper_chat.md`, `pt/models.py`, `pt/app.py`.
- [x] T059 [BE] Harness + v3 API smoke offline. `tests/e2e_harness.py`: LiveServer sets
  `PAPER_TRIAGE_DATA_DIR` to a temp dir and cleans it up. `tests/test_e2e_mock.py` (socket
  guard on): search -> save -> library `ready` -> pdf 200 -> highlight -> paper chat cites
  `p.2` -> directory create/move/delete -> unsave leaves no file. `tests/test_e2e_harness.py`:
  `/vendor/pdfjs/pdf.min.mjs` served as `text/javascript` once T052 landed (skip with reason if
  the file is absent).

### Wave G — FE lane (real API)

- [x] T060 [FE] [US5] [US6] Library view (FR-020, FR-022; brief L7, L10, L11, L12, L14).
  `pt/static/library.js` + `index.html` + `app.css`: loads `GET /api/library`; rows
  `li.lib-row[data-paper-id]` (title, authors, tags line, meta with `[data-pdf-status]`,
  `Saved <d Mon>`, highlight count, links, rank `for "<topic>"`, critique disclosure, `Open
  preview` -> preview route); filter `#lib-filter` (tags + title, L10a rules, debounce 150 ms,
  `/` and Esc); tag bar `#lib-tags` (count desc then A-Z, AND, pressed first, two rows + Show
  all, summary line, Clear filters); filter state in the hash; states loading/error/empty/no
  match; poll every 3 s while any row is `pending`; `Try again` -> `POST
  /api/library/retry`. Needs T047, T050. e2e (real harness): tag AND filter and title filter
  give exact rows (SC-012); status reaches "PDF ready".
- [x] T061 [FE] [US7] Directories UI + row actions (FR-023; brief L8, L9, L10b, L13). Rail
  `#dir-rail` (All saved, Unsorted, A-Z), `#dir-new` inline create, rename/delete in header
  with inline confirm, validation copy from API `detail`, native select below 1024 px with
  "Manage directories"; row `select[data-act="move"]` -> `POST /api/library/move`, row
  collapse when filtered out; `Remove from Library` -> always-confirm group -> DELETE. Needs
  T048. e2e: create, move, rename, delete (papers back in Unsorted, SC-015 no loss).
- [x] T062 [FE] [US8] Highlights, notes, list, export (FR-025, FR-026; brief L16 highlight
  control, L18, L19, L23). `viewer.js`: selection popover (3 swatches yellow/mint/peach + Add
  note), toolbar Highlight split control, rects as page-box fractions, `.hl[data-annotation-id]`
  layer redrawn on zoom (multiply blend), cross-page selection clipped with status copy;
  panel tab "Highlights n" `#pv-hl-list` (Go to, Edit note with 500 counter, Color select,
  Delete + 8 s Undo, page notes); `Export notes` Markdown download. A page with no text layer
  (scanned) shows a plain "No selectable text on this page" message for highlighting while
  page notes still work. Needs T051. e2e: highlight persists after reload and keeps
  proportional size after zoom; note saved; Go to jumps.
- [x] T063 [FE] [US9] Ask this paper panel + sheet (FR-027; brief L20 Rev 2, L22). New
  `pt/static/paperchat.js` (+ `index.html`, `app.css`, `viewer.js` hook-up). Tab
  "Ask this paper": idle copy, starters, `#pv-chat-question` + `#pv-chat-ask`; no request
  before the first submit; `POST /api/paper-chat` with the last 6 turns as `history`;
  `#pv-chat-log li.turn`, `[p.N]` -> `.cite[data-page]` buttons that jump; refusal
  `.turn__a--refused`; error + Ask again; input disabled with the not-ready / unavailable copy
  when `pdf.status` is not `ready`; transcript reset on reload and on closing the preview
  (copy says so); < 1024 px panel as `<dialog>` sheet. Needs T058 (stub with `page.route`
  until it lands).

### Wave H — final

- [x] T064 [FE] Browser e2e v3 on the real harness `tests/frontend/test_e2e_library.py`
  (`e2e`, port 8765 for FE runs): save from results -> Library row reaches "PDF ready" within
  5 s -> preview renders page 1 within 2 s of opening (SC-011) ->
  highlight + note survive server restart (SC-013) -> paper chat question with "Quartzite"
  cites `p. 2` and jumps; "capital of France" refused; network-panel check: no paper-chat
  request before the first question (SC-014) -> unsave from the card with confirm removes the
  row (SC-015) -> card-to-PDF in 3 actions (SC-016); `2401.00005` shows "PDF unavailable" and a
  disabled chat input; zero non-local requests in every case. Needs T059-T063.
- [x] T065 [BE] `README.md` + `SETUP_LOG.md` v3: Library, tags, directories, PDF preview,
  annotations, paper chat; `PAPER_TRIAGE_DATA_DIR`; vendored pdf.js (version, license, source);
  note that stored arXiv PDFs are for personal use only (do not deploy publicly). Needs T059.

## Phase 9: v4 amendment (Carbon visual redesign)

**Sources**: spec.md FR-030 (clauses a-f), FR-012, SC-017..SC-022, Clarifications "Session
2026-10-03 (v4)"; plan.md "v4 Amendment" (touch map, design notes, in-flight fixes gate);
research R19-R21; root DESIGN.md v2.0 (section refs D2..D10); `docs/design/redesign-brief.md`
items 1-34 (scope note B-a, B-b); `docs/research/ibm-verify.md` (font packages and sizes).
`pt/` = `src/paper_triage/`. Visual only: no API, data, copy, DOM order, id, ARIA, hash-route or
keyboard change. Class names stay; restyle existing selectors. Every FE task: re-read DESIGN.md
and PRODUCT.md first; keep all v2/v3 UI test hooks; if an existing e2e asserts an old visual
value (0.4 opacity, radius, Airtable colour), update it to the DESIGN.md value in the same task
and say so in the commit message. Keep the in-flight fixes: F-016 (highlight selection), F-017
(previous results stay at full opacity and interactive during a new search; brief B-b), F-018
(long multi-keyword search; BE, landed d323ef9), F-019 (preview opens on `Ask this paper`,
chat lazy; brief B-a). Every task: tests first where cheap; ends with `MOCK_LLM=1 uv run pytest
-q` and `uv run ruff check .` green; one commit with only its own paths plus `tasks.md`. FE e2e
runs use `E2E_PORT=8765`.

### Wave R1 — BE lane

- [x] T066 [P] [BE] woff2 MIME type (FR-030b, SC-017; brief item 32). Test first in
  `tests/test_api.py`: after `create_app()`, `mimetypes.guess_type("a.woff2")[0] ==
  "font/woff2"`; `GET /vendor/fonts/plex-sans-latin-400.woff2` -> 200 with `content-type:
  font/woff2` (`pytest.skip` with reason "fonts not vendored yet (T067)" while the file is
  absent). Then `pt/app.py`: `mimetypes.add_type("font/woff2", ".woff2")` next to the existing
  `.mjs` registration. Files `pt/app.py`, `tests/test_api.py`.

### Wave R1 — FE lane (starts after the F-016, F-017 and F-019 fix commits land)

- [x] T067 [FE] Vendor IBM Plex fonts + static guard (FR-030b, SC-017; brief items 1, 2; D3.1,
  D3.2; R19). Test first `tests/frontend/test_static_assets.py`: the 8 files
  `pt/static/vendor/fonts/{plex-sans-latin-400,plex-sans-latin-600,plex-sans-latin-ext-400,
  plex-sans-latin-ext-600,plex-sans-greek-400,plex-sans-greek-600,plex-mono-latin-400,
  plex-mono-latin-ext-400}.woff2` exist, are non-empty, start with the `wOF2` signature and total
  <= 250,000 bytes; `LICENSE-IBM-Plex.txt` contains "SIL Open Font License"; `README` names
  `@fontsource/ibm-plex-sans@5.3.0`, `@fontsource/ibm-plex-mono@5.3.0` and `@ibm/plex-sans@1.1.0`;
  `plex.css` has one `@font-face` per file, each with `font-display: swap` and a
  `unicode-range` (Greek faces `U+0370-03FF`), plus the "IBM Plex Sans Fallback" face using
  only `local()`; every `url()` in `plex.css` is relative (no scheme, no `//`, no leading `/`);
  `index.html` links `vendor/fonts/plex.css` with a relative href before `app.css`; the
  existing "no `@font-face` in own CSS" and no-external-URL rules still pass. Then do the one
  approved build-time fetch into the session scratch dir (`npm pack` of the three pinned
  packages, or `curl` of the same registry tarballs if npm is absent; install nothing, commit no
  tarball), copy and rename the files per the DESIGN.md section 3.1 table (Greek: the official
  split `fonts/split/woff2/` Regular and SemiBold Greek files; list the tarball for exact
  names), copy the `unicode-range` values verbatim from the Fontsource `latin`/`latin-ext` CSS of
  the same version, copy the OFL text, and write `plex.css` (pattern D3.2) and `README` (sources,
  versions, file mapping, sha256 per file). Files `pt/static/vendor/fonts/**`,
  `pt/static/index.html` (the one `<link>`), `tests/frontend/test_static_assets.py`.
- [x] T068 [FE] Token layer + global type, focus, hover and motion (FR-030a, FR-030c, FR-030e;
  brief items 3, 4; D2, D3.2, D3.3, D4, D5, D6, D7, D9; R21). Test first new
  `tests/frontend/test_design_tokens.py` (static parse of `pt/static/app.css`): `:root` declares
  `--color-*` per D2 (exact hex for `primary #0f62fe`, `ink #161616`, `ink-muted #525252`,
  `ink-subtle #6f6f6f`, `surface-1 #f4f4f4`, `border-strong #8d8d8d`, `error #da1e28`,
  `info-surface #edf5ff`), `--hl-yellow #ffde66`, `--hl-mint #9fe0c0`, `--hl-peach #ffc29e`,
  `--type-*` roles of D3.3, `--space-*`, `--radius-*`, `--control-sm/md/lg`, `--dur-fast 110ms`,
  `--dur-moderate 240ms`, `--dur-flash 1600ms`, `--ease-standard/entrance/exit`,
  `--shadow-overlay`, layout sizes, `--font-sans` starting with `"IBM Plex Sans"` and
  `--font-mono` starting with `"IBM Plex Mono"`; none of the old tokens remain (`--color-body`,
  `--color-muted`, `--color-hairline`, `--color-edge-input`, `--color-surface-soft`,
  `--color-surface-strong`, `--color-coral`, `--color-cream`, `--color-info-border`,
  `--color-yellow`, `--color-mint`, `--color-peach`, `--type-title-sm`, `--type-reason`,
  `--type-caption`, `--type-chip`, `--type-body-md`, `--type-display-md`); every `var(--…)` used
  in `app.css` is declared; `color-scheme: light`; `font-synthesis: none` on `html`;
  `font-variant-numeric: tabular-nums` on `body`; every `:hover` rule sits inside `@media
  (hover: hover)`; `@keyframes ray` and `breathe` and the `prefers-reduced-motion` and
  `forced-colors` blocks remain (`test_css_has_reduced_motion_rules` still passes). Then
  `app.css`: replace the whole `:root` block (header comment "Carbon-based, see DESIGN.md"),
  remap every `var()` use with the brief item 3 table in the same commit so the page renders
  coherently, set the font stacks on `html`/`body`, implement the one focus system of D7
  (inset `-2px` for fields, selects, icon buttons, tabs, rail items, outline and ghost buttons;
  inset white ring for filled buttons; no ring on `tabindex="-1"` targets), wrap hovers in
  `@media (hover: hover)`, switch transitions to the D6 tokens and update the reduced-motion and
  forced-colors blocks. Files `pt/static/app.css`, `tests/frontend/test_design_tokens.py`,
  existing `tests/frontend/test_e2e_*.py` only for old visual values.

### Wave R2 — FE lane (sequential: every task edits `app.css`)

- [x] T069 [FE] [US1] Shell, nav, buttons and query (FR-030a-c; brief items 5-8; D8.1, D8.2,
  D8.3, D8.4 intro band). `app.css`: `.global-nav` 48px with `border-subtle` bottom rule; view
  links 48px `ink-muted`, current link `ink`, weight 600, 2px `primary` bottom rule; brand
  `body-emphasis`; mock badge pill with 1px `info` border and `info` `label` text;
  `.mock-label__more` / `.model` per D8.3; skip links; buttons mapped per brief item 7 table
  (primary 40px / 48px in `.triage-form`, secondary charcoal for `#load-more` and notification
  `Try again`, outline, `.btn--small` 32px, danger outline `.btn--remove`, `.btn--on-dark`
  retired to secondary, ghost `.text-btn`/`.ext-link`, square 40px `.icon-btn`); Carbon text
  field (D8.2) for `#query`; intro title `heading-md` / `heading-lg` (>= 768), lead `prose`
  `ink-muted`, help line `label` `ink-subtle`. Test first new `tests/frontend/test_e2e_design.py`
  (`e2e`, real harness): at 1440 px `body` computed font-family starts with "IBM Plex Sans" and
  `document.fonts.check('16px "IBM Plex Sans"')` is true after `document.fonts.ready`; nav
  height 48; `nav a[data-view="triage"][aria-current="page"]` has font-weight 600 and a 2px
  `rgb(15, 98, 254)` bottom border; `#submit` background `rgb(15, 98, 254)`, border-radius
  `0px`, height 48 at 1440 and full width at 390; `#query` height 48 with a 1px bottom border
  `rgb(141, 141, 141)`. Files `pt/static/app.css`, `tests/frontend/test_e2e_design.py`.
- [x] T070 [FE] [US1] [US2] Result rows and results chat (FR-030a-c; brief items 9, 10, 11, 15,
  16; D8.4 rows, critique, save, confirm; D8.6). `app.css`: `.paper` rank column 56 / 72px,
  padding-block 16 / 24, 1px `border-subtle` top rule except the first; `.rank__n`
  `numeral-md` / `numeral-lg`, `.rank__of` `label` `ink-subtle`, `.rank__meter` 4px square bar
  (`rank-track` / `rank-fill`, 48px, 32px mobile); `.paper__title` `heading-xs`;
  `.paper__reason` `prose` `ink` max 72ch; `.paper__id` `mono`; `.flag` square `surface-2` tag,
  `.flag--failed` `error` text and border; `.disclosure` / `.critique` square `surface-1`,
  heads `body-emphasis`, chevron over `dur-moderate`; `.save` outline 32px with min-width kept,
  `.is-saved` `surface-2` no border; `.confirm` danger outline + outline `Keep`; `.chat` square
  `surface-1` no border, `h2` `heading-sm`, `.turn__q` `body-emphasis`, `.turn__a` `body`,
  `.turn__a--refused` info notification (`info-surface`, 3px `info` left rule); `.cite` `mono`
  on `cite-surface`, radius 2px, hover and active `cite-surface-active`, `.cite--off` dashed
  `border-strong` with `ink-muted` text; chat fields canvas on the panel. Test first, add to
  `tests/frontend/test_e2e_design.py`: after a mock search, `.rank__n` font-size 32px at 1440
  and 24px at 390; `.rank__meter` height 4px and radius `0px`; `.paper__id` and `a.cite`
  font-family start with "IBM Plex Mono"; `a.cite` background `rgb(224, 224, 224)` and radius
  `2px`; a refusal `.turn__a--refused` has background `rgb(237, 245, 255)` and a 3px left border
  `rgb(15, 98, 254)`; a saved row's `button.save[aria-pressed="true"]` background `rgb(224,
  224, 224)`. Files `pt/static/app.css`, `tests/frontend/test_e2e_design.py`.
- [x] T071 [FE] [US5] [US6] [US7] Library view (FR-030a-c; brief items 18-22; D8.7). `app.css`:
  `.rail` items 32px (40 on `pointer: coarse`), `.rail__item[aria-current="true"]`
  `surface-selected` fill, weight 600, `box-shadow: inset 3px 0 0 var(--color-primary)`, hover
  `surface-hover`, counts `label` `ink-subtle`; `.tag` pill 32px, 1px `border-strong`, `label`,
  `[aria-pressed="true"]` `surface-inverse` with white text and the check glyph kept, filled
  focus ring; `.lib-filter input`, `.select`, `.lib-dir__select`, `.dir-form input` Carbon field
  with an inline SVG data-URI chevron (row select 32px); library rows as T070 plus `.lib-pdf`
  `label`, `.lib-pdf--failed` `error`, `.lib-saved` / `.lib-hl` `ink-subtle`, `.dir-manage`
  square `surface-1`; `.lib-row.is-collapsing` opacity plus `grid-template-rows` collapse with
  `ease-exit` at `dur-moderate` (no `height` transition). Test first, add to
  `tests/frontend/test_e2e_design.py` (real harness, two saved papers): the current rail item
  font-weight 600 and box-shadow contains `inset 3px 0px 0px` with `rgb(15, 98, 254)`; a pressed
  `#lib-tags button.tag` background `rgb(22, 22, 22)` and color `rgb(255, 255, 255)`;
  `.lib-row select[data-act="move"]` height 32 and `appearance` none; the computed
  `transition-property` of `.lib-row` does not contain `height`. Files `pt/static/app.css`,
  `tests/frontend/test_e2e_design.py`.
- [x] T072 [FE] [US5] [US8] Preview toolbar, find, well, highlights and popover (FR-030a-d;
  brief items 23-27; D2.4, D8.8). Keep F-016: change only visuals (`.textLayer ::selection` uses
  `color-mix(in srgb, var(--color-primary) 25%, transparent)`), never the selection or
  highlight code paths; the F-016 e2e check passes unchanged. `app.css`: `.pv-toolbar` controls
  40px square, title `heading-xs`, pager/zoom/find as icon or ghost buttons, `.pv-hlctl` joined
  outline button + select (`margin-left: -1px`, focused part `z-index: 1`), `.pv-sheet-open`
  outline, wrap and order rules below 1024 unchanged; `.pv-find` Carbon field, `label` count,
  `.find-hit` hover `surface-hover`, `.find-match` `body-emphasis`; `.pv-well` `well` fill,
  `.pdf-page` canvas with 1px `border-page` edge and no shadow, page flash 2px `focus` outline;
  `.hl--yellow/mint/peach` opaque fills from `--hl-*` (no alpha, no `color-mix`), radius 2px,
  `mix-blend-mode: multiply` kept on `.hl-layer`, failed-save highlight 1px dashed `error`
  outline; swatches and `.dot` circles with a 1px `border-strong` edge; `.hl-item__quote` 3px
  left rule in the highlight colour; `.pv-popover` square canvas, `shadow-overlay`, 1px
  `border-subtle`, `.swatch.is-last` 2px `ink` ring offset 2px. Test first, add to
  `tests/frontend/test_e2e_design.py` (real harness, saved mock paper): every toolbar control in
  `#pv-controls` is 40px tall; a created yellow `.hl` has background `rgb(255, 222, 102)` with
  alpha 1 and its layer `mix-blend-mode: multiply`, same check for mint `rgb(159, 224, 192)` and
  peach `rgb(255, 194, 158)`; `section.pdf-page` border `1px solid rgb(198, 198, 198)`; the
  popover border-radius `0px` and non-empty box-shadow; swatches border-radius `50%`; the
  highlight list prints the colour name (SC-019). Files `pt/static/app.css`,
  `tests/frontend/test_e2e_design.py`.
- [x] T073 [FE] [US8] [US9] Preview side panel, notes, Ask this paper and bottom sheet (FR-030a-c,
  FR-030f; brief items 28-31; D8.6, D8.8). Keep F-019: `Ask this paper` is the selected tab on
  every preview open (panel and sheet) and no paper-chat request happens before the first
  question. `app.css`: `.pv-panel` `surface-1` with a 1px `border-page` left edge; `.pv-tab`
  40px, selected tab 2px `primary` underline and weight 600, count `label`; `.note-editor
  textarea` canvas field on the panel, `.note-counter.is-max` `error`; `.pv-chat__nopdf` info
  notification; `.pv-chat__form` sticky on `surface-1` (canvas inside the sheet); `button.cite`
  same chip as T070; `.pv-sheet` square, canvas, `shadow-overlay`, `overlay` backdrop, tabs and
  Close in one header row, slide in with `ease-entrance` at `dur-moderate`, no slide under
  reduced motion; `.pdf-page__notext` info notification look. Test first, add to
  `tests/frontend/test_e2e_design.py`: at 1440 the selected `.pv-tab` is `Ask this paper` with
  font-weight 600 and a 2px `rgb(15, 98, 254)` bottom border, and zero `/api/paper-chat`
  requests before the first question; at 390 the sheet opens on `Ask this paper`, has
  border-radius `0px` and a non-empty box-shadow; `2401.00005` shows `.pv-chat__nopdf` with
  background `rgb(237, 245, 255)`. Files `pt/static/app.css`, `tests/frontend/test_e2e_design.py`.
- [x] T074 [FE] [US1] States, motion and forced-colours sweep (FR-030a, FR-030c, FR-030e,
  FR-030f; brief items 12, 13, 14, 17; D6, D7, D8.4 previous results, D8.5, D9). Keep F-017:
  `.is-stale` keeps opacity 1 and gets no `pointer-events`, overlay or `inert` (the class hook
  stays). `app.css`: `.working` in normal flow above the list, `surface-1`, square, padding 24
  (`.working--compact` 12/16); `.notes` `surface-1`; `.alert` error notification
  (`error-surface`, 3px `error` left rule, ink text, secondary `Try again`, coral fill and white
  text removed, `.ext-link--on-dark` a normal ghost link); `.empty` title `heading-xs`, body
  `prose` `ink-muted`, example chips 32px outline; `.paper--cited` / `.paper--new` fade
  `info-surface` over `dur-flash`; reduced motion per D6 (static 2px `focus` outline on the cited
  row, static `info-surface` on new rows, static working glyph with rays at full opacity, no
  sheet slide, no chevron rotation, no row-collapse animation); forced colours per D7 for
  controls, notifications, chips, panels, sheet, meter and highlights. Test first: add to
  `tests/frontend/test_design_tokens.py` no literal hex or `rgb(`/`rgba(` outside `:root`
  (allowed: system colours inside `@media (forced-colors: active)` and `data:` URIs), no
  declared-but-unused token, only font-weight 400, 600 or `normal` (no `bold`, 300, 500,
  700), every transition and animation
  disabled inside `prefers-reduced-motion: reduce`; add to `tests/frontend/test_e2e_design.py`
  (harness triage delay): during a second search the previous `li.paper` rows have computed
  opacity 1 and their `button.save` and `a[data-link="abs"]` are clickable while `#working` is
  visible (F-017); a failed load shows `.alert` with background `rgb(255, 241, 241)`. Files
  `pt/static/app.css`, `tests/frontend/test_design_tokens.py`,
  `tests/frontend/test_e2e_design.py`.

### Wave R2 — BE lane

- [x] T075 [P] [BE] `README.md` + `SETUP_LOG.md` v4 design note: Carbon-based DESIGN.md (light
  theme only), vendored IBM Plex Sans/Mono (8 woff2 files, about 125 KB, OFL 1.1, packages and
  versions from `pt/static/vendor/fonts/README`), the one-time build-time font fetch (no runtime
  network), and the design e2e command with `V4_SHOTS_DIR`. Needs T067. Files `README.md`,
  `SETUP_LOG.md`.

### Wave R3 — FE lane (final)

- [x] T076 [FE] Design e2e sweep + screenshots (SC-017..SC-022; R20). Extend
  `tests/frontend/test_e2e_design.py` (`e2e`, real harness, port 8765 for FE runs), each case
  at viewport widths 390, 820 and 1440: zero non-local requests on Triage, Library and Preview,
  and every woff2 response from `/vendor/fonts/` has `content-type: font/woff2`;
  `document.fonts.check('12px "IBM Plex Mono"')` and `document.fonts.check('16px "IBM Plex
  Sans"')` are true once a paper id is on screen; WCAG contrast
  computed in the page from computed `color` and the first opaque ancestor `background-color`
  for this selector list, each >= 4.5: `.paper__title`, `.paper__reason`, authors, `.rank__of`,
  `.paper__id`, `a[data-link]`, nav links (current and not), `.pv-tab`, `.turn__a`,
  `.turn__a--refused`, `.alert`, `a.cite`, `.lib-saved`, `.views__count`; `.rank__n` >= 3; edge
  colour of `#query`, `button.save` and `.tag` against their background >= 3; Tab to `#submit`
  shows a 2px `rgb(15, 98, 254)` outline; with `reduced_motion="reduce"`, after a cite click and
  a load-more, `document.getAnimations()` on `.paper--cited`, `.paper--new`, the critique
  disclosure and the sheet is empty while the cited and new rows still show their static marker
  (SC-020); with `forced_colors="active"`, `#submit` and `.cite` show a non-transparent border;
  screenshots of Triage results, Library and Preview (panel at 1440, sheet at 390 and 820)
  written to `$V4_SHOTS_DIR` (default: a pytest temp dir) as `<view>-<width>.png` (SC-022). Then
  run the full `MOCK_LLM=1 uv run pytest -q -m e2e` green, including the F-016, F-017 and F-019
  checks (SC-021). If a fix commit for F-016, F-017 or F-019 shipped without a browser check,
  add it here: F-016 = after selecting text on page 1 and releasing, the selection and the
  popover stay until a swatch is chosen and the new `.hl` covers the selected words; F-017 = as
  in T074; F-019 = as in T073. Needs T066, T068-T074. Files `tests/frontend/test_e2e_design.py`.

## Phase 10: LLM config amendment (three provider-neutral variables)

**Sources**: spec.md FR-011 and Clarifications "Session 2026-10-20 (LLM config)"; plan.md "LLM
config Amendment" (variable table, Constitution Check 2.1.0, T077 touch map); research R22;
constitution 2.1.0 Technical Constraints; contracts/api.md `GET /api/status` (T077 note).
User-approved. Backend only: no API shape, data model, UI or copy change. Supersedes the env naming of T001, T002 and T025 (those stay ticked as
history). Ends with `MOCK_LLM=1 uv run pytest -q` and `uv run ruff check .` green, offline; one
commit with only its own paths plus `tasks.md`.

### Wave L1 — BE lane

- [x] T077 [BE] Three LLM env variables (FR-011, R22). Test first `tests/test_config_llm.py`
  (monkeypatch env; clear all seven names first; fake SDK constructors, no network, no real key):
  (a) `get_settings()` with `LLM_PROVIDER` unset or blank -> `provider == ""`, no exception;
  `" OpenAI "` -> `"openai"`; (b) `AGENT_MODEL` blank -> `"claude-opus-5-5"` for `anthropic` and
  `"gpt-5-mini"` for `openai`; `AGENT_MODEL=x` -> `"x"` for both; (c) with `MOCK_LLM` unset,
  `get_client()` raises `LLMError` whose message contains `LLM_PROVIDER` when the provider is
  unset, blank or `"gemini"` (message also names `anthropic` and `openai`); (d) provider set and
  `AGENT_API_KEY` unset or blank -> `LLMError` whose message contains `AGENT_API_KEY`, for both
  providers; (e) old names ignored: `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` set without
  `AGENT_API_KEY` -> still the `AGENT_API_KEY` error; `ANTHROPIC_MODEL`/`OPENAI_MODEL` set with
  `AGENT_MODEL` blank -> model is still the provider default; (f) key passed explicitly: with a
  monkeypatched `anthropic.Anthropic` / `openai.OpenAI` that records its kwargs, the first
  `parse`/`text` call constructs it with `api_key=<AGENT_API_KEY>`; (g) `MOCK_LLM=1` with all
  three unset -> `MockClient`, no error; (h) importing `paper_triage.app` and `create_app()` with
  all unset and `MOCK_LLM` unset raise nothing (errors only at the first LLM call); replace the
  existing default-provider and `OPENAI_API_KEY` tests. `tests/test_e2e_mock.py`: delete
  `LLM_PROVIDER`, `AGENT_API_KEY`, `AGENT_MODEL` and the four old names from the env at the start
  of the mock flow and keep every existing assertion green (mock needs none of them); replace any
  old-name setup or assertion. Then `src/paper_triage/config.py` `get_settings()` (current lines
  35-48): `provider = (os.environ.get("LLM_PROVIDER") or "").strip().lower()`; new
  `Settings.api_key: str = ""` from `AGENT_API_KEY` (stripped); `model = (AGENT_MODEL or
  "").strip() or` the default for a known provider (`DEFAULT_MODEL` for `anthropic`,
  `DEFAULT_OPENAI_MODEL` for `openai`, else `""`); `Settings.provider` default becomes `""`;
  `get_settings()` never raises; the old names are not read anywhere. `src/paper_triage/llm.py`:
  `AnthropicClient` and `OpenAIClient` take `api_key` and build `anthropic.Anthropic(api_key=...)`
  / `openai.OpenAI(api_key=...)` lazily (replace the line-192 `openai.OpenAI()  # reads
  OPENAI_API_KEY`); `get_client()` (current lines 241-247): mock first; then `""` ->
  `LLMError("LLM_PROVIDER is not set (use 'anthropic' or 'openai')")`; unknown ->
  `LLMError("unknown LLM_PROVIDER '<value>' (use 'anthropic' or 'openai')")`; missing key ->
  `LLMError("AGENT_API_KEY is not set (required for LLM_PROVIDER=<provider>)")`; pass
  `api_key=s.api_key` and `model=s.model`. `pt/app.py` is unchanged: `GET /api/status` keeps
  returning 200 when the variables are unset (provider and model may be empty strings, per the
  T077 note in contracts/api.md `GET /api/status`; assert this in `tests/test_config_llm.py`).
  `.env.example`: remove `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_MODEL` and
  `OPENAI_MODEL`; add `LLM_PROVIDER=` with a comment "required: anthropic or openai",
  `AGENT_API_KEY=` "required: key for the chosen provider", `AGENT_MODEL=` "optional; blank =
  claude-opus-5-5 (anthropic) or gpt-5-mini (openai)"; keep `MOCK_LLM` and the other entries.
  `README.md`: configuration table and live-mode steps use the three variables (both marked
  required), the two model defaults, and one line that the old names are no longer read. Never
  read or print `.env`. Files `src/paper_triage/config.py`, `src/paper_triage/llm.py`,
  `tests/test_config_llm.py`, `tests/test_e2e_mock.py`, `.env.example`, `README.md`. If another
  test outside this list sets or asserts an old name or the old default provider, report it as
  a blocker instead of editing it.

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

v3 waves (spawn both lanes in one message; tester after each wave; failures go back tagged):

| Wave | BE lane | FE lane | Cross-lane needs |
|---|---|---|---|
| F | T043 -> T044 -> T045 -> T046 -> T047 -> T048 -> T049 -> T050 -> T051 | T052 -> T053 -> T054 -> T055 -> T056 | none: FE stubs the API with `page.route` per contracts/api.md and serves `pt/fixtures/sample.pdf` |
| G | T057 -> T058 -> T059 | T060 -> T061 -> T062 -> T063 | T060 needs T047+T050, T061 needs T048, T062 needs T051 (all Wave F); T063 stubs until T058 lands, verified in T064 |
| H | T065 | T064 | T064 needs T059 + T060-T063; T065 needs T059 |

- Shared files: none across lanes. BE never edits `pt/static/**` or `tests/frontend/**`;
  FE reads (never writes) `pt/fixtures/sample.pdf`. The `.mjs` MIME registration is BE (T050);
  FE's T052 guard and T055 e2e do not depend on it when stubbing (Playwright `route.fulfill`
  sets the content type), but a real-server run of the viewer needs T050.
- API handoff as in v2: contracts/api.md is the source of truth; BE records landed facts in
  `.claude/state/agents/backend-builder.md` "API facts"; FE gaps go back as `NEEDS-BE:`.

v4 waves (Carbon redesign; spawn both lanes in one message; tester after each wave; failures go
back tagged):

| Wave | BE lane | FE lane | Cross-lane needs |
|---|---|---|---|
| R1 | T066 | T067 -> T068 | FE starts only after the F-016, F-017 and F-019 fix commits land (same files: `index.html`, `app.css`, `app.js`, `viewer.js`, `paperchat.js`). T066's font GET test skips until T067 lands; the tester re-runs it after both. |
| R2 | T075 | T069 -> T070 -> T071 -> T072 -> T073 -> T074 | T075 needs T067. All FE tasks edit `app.css`: strict sequence, no FE parallelism. |
| R3 | none | T076 | T076 needs T066 (real-server `font/woff2`) and T068-T074. |

- After R3: tester runs brief item 33 (full pytest + ruff, e2e at 390/820/1440, contrast spot
  check of DESIGN.md section 2 pairs, F-017/F-019 = B-b/B-a still hold) with
  `V4_SHOTS_DIR=docs/qa/screenshots/v4`; then the designer re-audit (brief item 34) on those
  screenshots, one ordered fix list, at most one confirm pass. Fix items become new tasks
  (T078+; T077 is the LLM config task) re-checked with speckit-analyze.
- Shared files: none across lanes. BE never edits `pt/static/**` or `tests/frontend/**`; FE
  never edits `pt/app.py`, `README.md` or `SETUP_LOG.md`. The README design note is BE (README
  owner) although its content comes from FE's T067.

LLM config wave (user-approved 2026-10-20; BE only):

| Wave | BE lane | FE lane | Cross-lane needs |
|---|---|---|---|
| L1 | T077 | none | none: no API, UI or static change. Spawn backend-builder alone, then the tester (full offline `MOCK_LLM=1 uv run pytest -q` + `uv run ruff check .`). |

- Shared files: none. T077 touches no `pt/static/**`, `tests/frontend/**` or `pt/app.py`.

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
v3 BE: T043, T044 independent; T045 -> T046 -> T047 (needs T043) -> T048; T049 needs T044+T046;
T050 needs T047+T049; T051 needs T046+T050; T057 needs T044; T058 needs T050+T057; T059 needs
T050, T051, T058; T065 needs T059. v3 FE: T052 -> T053 -> T054 -> T055 (needs T052) -> T056;
T060 needs T053+T047+T050; T061 needs T060+T048; T062 needs T055+T051; T063 needs T055 (+T058
for real API); T064 needs T059-T063.
v4 (FE lane gated on the F-016, F-017, F-019 fix commits): BE T066 independent; T075 needs
T067. FE T067 -> T068 -> T069 -> T070 -> T071 -> T072 -> T073 -> T074 -> T076; T076 also needs
T066.
LLM config: T077 needs T025 (OpenAI client) and T026 (both landed); independent of every FE task.

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
v3 (23 tasks, T043-T065; BE 13, FE 10): US4 T045, T047, T054; US5 T044, T046, T049, T050, T053,
T055, T056, T060; US6 T043, T060; US7 T048, T061; US8 T046, T051, T062; US9 T057, T058, T063;
cross-cutting T052, T059, T064, T065. Increment order: Wave F = storage + full Library API
(save, directories, PDF, annotations) || UI shell, Save toggle, viewer, find on stubs (MVP
check: save a paper and read its PDF in-page = US4 + US5); Wave G = paper chat API + harness
|| Library, directories, highlights and chat UI on the real API; Wave H = full browser proof
and docs.
v4 (11 tasks, T066-T076; BE 2, FE 9; no new story, all FR-030): foundations T066-T068 (MIME,
fonts, tokens: the page already reads in Plex with Carbon colours after R1), per-view restyle
T069 (shell/nav/query), T070 (results + chat), T071 (Library), T072 (Preview toolbar, well,
highlights), T073 (panel, paper chat, sheet), T074 (states, motion, forced colours), proof
T076, docs T075. Stop-and-validate point: after T068 every view uses the new tokens and fonts
with behaviour unchanged.
LLM config (1 task, T077; BE 1, FE 0; no new story, FR-011 reworded): one commit switches config,
client wrapper, tests, `.env.example` and README together, so no commit leaves a half-renamed
config. Validate with quickstart steps 24-25 and the offline suite.
