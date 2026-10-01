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
- [ ] T013 [P] [US1] Test first `tests/test_agents.py::test_ranker*`, then
  `pt/prompts/ranker.md` + `pt/ranker.py`: `rank(paper, summary, topic, client) -> Rank`;
  rubric anchors; empty topic -> "overall reading priority" wording; clamp.
- [ ] T014 [US1] Test first `tests/test_pipeline.py`, then `pt/pipeline.py`:
  `triage(query, n, conn, http, llm) -> {topic, results, errors}`: parse -> fetch -> per paper
  summarize/critique/rank (one retry on validation error; `LLMError`/`LLMRefusal` -> result
  `failed` with reason, others continue); reuse existing (paper_id, topic) result; cap n<=20;
  return sorted per contracts/api.md.
- [ ] T015 [US1] Test first `tests/test_api.py` (status, triage, papers, 422s), then
  `pt/app.py`: FastAPI app; startup opens db + `init_schema`; deps from `config`/`get_client`/
  `make_http`; `GET /api/status`, `POST /api/triage`, `GET /api/papers`; static mount at `/`.
- [ ] T016 [US1] UI structure. Re-read DESIGN.md + PRODUCT.md first; apply frontend-design /
  impeccable guidance. `pt/static/index.html` + `pt/static/app.css`: one page, header with mock
  label slot, query input + submit on top, ranked list region, chat region (beside wide / below
  narrow, empty for now); system font stack, one accent, generous whitespace; semantic landmarks.
- [ ] T017 [US1] `pt/static/app.js` triage flow (re-read DESIGN.md + PRODUCT.md): submit ->
  `POST /api/triage`; loading, empty ("No papers found"), and per-item error states; each row
  shows rank, title, id, reason at a glance, "abstract only" flag; critique in `<details>`
  (weak claims / overclaims / missing baselines / "not stated"); rows have `id="paper-<id>"`;
  fully keyboard operable.

## Phase 4: User Story 2 – Grounded chat (P2)

**Goal**: answers cite stored ids only; explicit refusals.
**Independent test**: stored fixture papers, mock mode: in-scope -> valid citations; out of
scope -> `refused: true`; empty store -> refused, LLM not called.

- [ ] T018 [US2] Test first `tests/test_chat.py`, then `pt/prompts/chat.md` + `pt/chat.py`:
  `answer(question, conn, client) -> ChatAnswer`; empty store -> refusal without calling client
  (assert via spy); context = top-k papers as `<paper id title>` with abstract, summary,
  critique; regex `\[([^\[\]\s]+)\]` validation, strip unknown ids into `dropped_citations`;
  sentinel or zero valid citations -> `refused: true`.
- [ ] T019 [US2] Extend `tests/test_api.py`, then `pt/app.py`: `POST /api/chat` (422 on empty
  question), persists `chat_turns`.
- [ ] T020 [US2] Chat UI (re-read DESIGN.md + PRODUCT.md; frontend-design / impeccable):
  `pt/static/index.html`, `app.css`, `app.js`: question input + send; answers in an
  `aria-live` log; citations rendered as links to `#paper-<id>`; refusal is a distinct,
  calm, intentional state (not an error look); keyboard send.

## Phase 5: User Story 3 – Revisit earlier results (P3)

**Goal**: reload shows stored results without refetching.
**Independent test**: triage, new app instance on same db, `GET /api/papers` returns same list.

- [ ] T021 [US3] Extend `tests/test_api.py` (new TestClient on same db file returns same
  results, no fetch), then (re-read DESIGN.md + PRODUCT.md) `pt/static/app.js`: on load call `/api/status` (toggle mock label,
  show model) and `/api/papers` to render stored list.

## Phase 6: Polish

- [ ] T022 E2E mock smoke `tests/test_e2e_mock.py`: with `MOCK_LLM=1`, no key, and
  `socket.socket.connect` monkeypatched to raise: status mock=true; triage topic -> 5 results,
  >=1 `basis="abstract"`; mixed ids+URL input; chat in-scope cites only stored ids; out-of-scope
  refused; 5-paper triage < 5 s (SC-001).
- [ ] T023 UI polish + a11y (re-read DESIGN.md + PRODUCT.md; impeccable audit/polish): focus
  rings, contrast AA, `prefers-reduced-motion`, no motion-dependent info, narrow-width layout,
  anti-references checked (no gradient hero, no card grid, no chat gloss). Files
  `pt/static/*` only.
- [ ] T024 `README.md`: what it does, setup (`uv sync`, `.env`), run (mock and live), test
  commands, arXiv rate-limit note, pypdf/PyMuPDF swap note, layout of runtime agents + prompts.

## Dependencies

T001 -> T002 -> {T003, T005, T006, T007, T008} ; T004 after T002+T003.
US1: T009 -> T010 (needs T005-T007); T011-T013 need T003+T004 (parallel); T014 needs
T008-T013; T015 needs T014; T016 -> T017 need T015.
US2: T018 needs T004+T005; T019 needs T015+T018; T020 needs T017+T019.
US3: T021 needs T017. Polish: T022 needs T019; T023 after T020+T021; T024 last.

## Parallel Examples

- Foundational: T003, T005, T006, T007, T008 together.
- US1 agents: T011, T012, T013 together.

## Implementation Strategy

MVP = Phases 1-3 (stop and validate quickstart steps 1-3). Then US2, US3, polish, README.
Story -> tasks: US1 T009-T017 (9), US2 T018-T020 (3), US3 T021 (1).
