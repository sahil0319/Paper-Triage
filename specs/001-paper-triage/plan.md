# Implementation Plan: Paper Triage Assistant

**Branch**: `001-paper-triage` (no git branch; orchestrator commits on current branch) |
**Date**: 2026-10-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-paper-triage/spec.md`

## Summary

Local FastAPI app + one static page. Input (topic or ids/URLs) -> Fetcher (arXiv API, throttled,
cached; PDF via pypdf, abstract fallback) -> Summarizer -> Critic -> Ranker (three LLM calls per
paper, each its own module + prompt file, Pydantic-validated) -> SQLite. Grounded chat stuffs the
current result set (v2: `paper_ids` sent by the page, max 50; v1 was top 20 stored) into
context, validates `[id]` citations server-side against that set, refusal sentinel. One LLM
wrapper with a mock twin; `MOCK_LLM=1` also swaps HTTP to fixtures. See [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.11+ (uv-managed)

**Primary Dependencies**: fastapi, uvicorn, httpx, pydantic v2, anthropic, pypdf. Dev: pytest,
ruff; v2: pytest-playwright + Playwright chromium (browser e2e only; constitution 1.1.0 I,
justified in research R12). No others.

**Storage**: SQLite via stdlib `sqlite3`; schema in [data-model.md](data-model.md)

**Testing**: pytest (+ FastAPI `TestClient`), ruff; all offline with `MOCK_LLM=1`; v2 adds
real-browser e2e (pytest-playwright, marker `e2e`, local server on `E2E_PORT`, default 8766)

**Target Platform**: local macOS/Linux, browser at 127.0.0.1

**Project Type**: single project web app (API + static page)

**Performance Goals**: mock 5-paper triage < 5 s (SC-001); live bound by arXiv 3 s/request

**Constraints**: offline tests; arXiv 1 req/3 s; <=20 papers/run; 40k chars text per LLM call;
model from `ANTHROPIC_MODEL` (default `claude-opus-5-5` in `config.py` only);
T025: `LLM_PROVIDER=openai` swaps in `OpenAIClient` (`OPENAI_API_KEY`, `OPENAI_MODEL`), same wrapper

**Scale/Scope**: 1 user, tens to low hundreds of stored papers

## Constitution Check

*Pre-research and post-design: PASS. Re-checked for v2 against constitution 1.1.0: PASS.*

| Principle | Check | Status |
|---|---|---|
| I Small | 6 runtime deps, one module per agent, prompts for 4 LLM agents, fetcher LLM-free; v2 adds only dev dep pytest-playwright (allowed in 1.1.0), no new runtime dep or module | PASS |
| II Offline | `llm.get_client()` mock twin; `httpx.MockTransport` fixtures; tests need no key/net; v2 browser e2e on 127.0.0.1, no external assets, harness aborts non-local requests | PASS |
| III Grounded | `[id]` regex validation vs the current result set (`paper_ids`), `NOT_IN_STORED_PAPERS`, empty-set short-circuit; MockClient refuses without overlap | PASS |
| IV One page | one `index.html`, no auth/deploy/queue; sync triage request; paging via request `offset`, no session; FRs = 15 (cap) | PASS |
| V Honest critique | `basis` field + UI flag, "not stated" prompt rule, rank clamp; indicator shows activity, never fake progress | PASS |

## Project Structure

### Documentation (this feature)

```text
specs/001-paper-triage/
├── spec.md  plan.md  research.md  data-model.md  quickstart.md  tasks.md
├── contracts/api.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
pyproject.toml            # uv project, deps, ruff + pytest config
.env.example              # ANTHROPIC_API_KEY=, ANTHROPIC_MODEL=, MOCK_LLM=, PAPER_TRIAGE_DB=
src/paper_triage/
├── __init__.py
├── config.py             # env settings (model default, mock flag, db path, caps)
├── models.py             # Pydantic: Summary, Critique, Rank, ChatAnswer, PaperOut
├── db.py                 # schema + CRUD (papers, arxiv_cache, results, chat_turns)
├── llm.py                # LLMClient protocol, AnthropicClient, MockClient, get_client()
├── extract.py            # extract_text(pdf_bytes) -> str (pypdf; swap point)
├── net.py                # make_http(): real httpx + 3 s Throttle, or MockTransport + 0 s
├── input_parse.py        # query -> (topic, items)
├── fetcher.py            # runtime agent: arXiv search/ids, PDF URLs, cache, fallback
├── summarizer.py         # runtime agent
├── critic.py             # runtime agent
├── ranker.py             # runtime agent
├── chat.py               # runtime agent: context build, citation validation, refusal
├── pipeline.py           # triage(query, n) orchestration + persistence
├── app.py                # FastAPI routes per contracts/api.md + static mount
├── prompts/{summarizer,critic,ranker,chat}.md
├── fixtures/{arxiv_search.xml, sample.pdf}   # mock-mode network fixtures
└── static/{index.html, app.css, app.js}
tests/
├── conftest.py           # MOCK_LLM=1, tmp db, TestClient
├── test_smoke.py  test_config_llm.py  test_models.py  test_db.py  test_net.py
├── test_extract.py  test_input_parse.py
├── test_fetcher.py  test_agents.py  test_chat.py  test_pipeline.py  test_api.py
├── test_e2e_mock.py      # full flow smoke through HTTP
├── e2e_harness.py        # v2 [BE]: LiveServer (uvicorn thread, MOCK_LLM=1, temp DB, triage delay)
├── test_e2e_harness.py   # v2 [BE]: harness smoke (server up, page loads, no external requests)
└── frontend/             # v2 [FE]
    ├── test_static_assets.py   # no external URLs, required test hooks present
    └── test_e2e_browser.py     # Playwright specs (marker e2e)
```

v2 file touch map: [BE] `models.py`, `pipeline.py`, `db.py`, `fetcher.py`, `net.py`,
`fixtures/arxiv_search.xml`, `llm.py`, `chat.py`, `prompts/chat.md`, `config.py`, `app.py`,
`tests/*` (not `tests/frontend/`), `pyproject.toml`, `uv.lock`, `README.md`, `SETUP_LOG.md`.
[FE] `static/{index.html, app.css, app.js}`, `tests/frontend/**`.

**Structure Decision**: single `src/paper_triage` package (src layout), flat modules; runtime
agents are top-level modules named after the agent.

## Key Design Notes

- Pipeline per paper: fetch -> summarize -> critique -> rank, sequential; any agent failure
  marks result `failed` with reason, others continue. Existing (paper_id, topic) result reused.
- Ranker input: topic + title + abstract + summary (not full text) to keep cost low.
- Mock fixtures: Atom feed with 5 entries (v2: 15, see "v2 Amendment"); mock transport returns `sample.pdf` for 4 and invalid
  bytes for 1 (exercises abstract fallback). Unknown arXiv id -> empty feed -> "not found".
- UI (one page): input + submit on top; ranked list (rank, title, id, reason; basis flag);
  expandable critique (`<details>`); chat panel beside (wide) / below (narrow); citations as
  anchors to `#paper-<id>`; refusal styled as a distinct, calm state; mock label in header;
  loading state on submit. Builder MUST re-read DESIGN.md + PRODUCT.md and apply
  frontend-design / impeccable guidance before UI tasks.

## v2 Amendment (2026-10-01)

Design source: DESIGN.md (Airtable) via `docs/design/brief-v2-redesign.md` (items D1-D35,
deviations in its section 0, backend needs B1-B3 in section 9). Contract:
[contracts/api.md](contracts/api.md) is authoritative where the brief says "planner to confirm".

- **B1 links** (FR-014): `pipeline.to_out` adds `abs_url`/`pdf_url` (arXiv: derived from id;
  `pdf`: `papers.pdf_url`). `db.list_results` and the triage path must carry `pdf_url`.
  `PaperOut` gains both fields.
- **B2 paging** (FR-013): `Fetcher.search(topic, n, offset=0)` sends `start=offset`, cache key
  `q:<terms>:<n>:<offset>`, reads `opensearch:totalResults`; `pipeline.triage(..., offset=0)`
  returns `offset`, `next_offset`, `has_more`; `TriageIn.offset` 0..1000; item query with
  offset > 0 -> 422. Mock: fixture feed grows to 15 entries (first 5 unchanged, incl. invalid-PDF
  id `2401.00005`), `net._feed` honours `start` and writes `opensearch:totalResults` = 15.
  Existing tests that relied on "default 10 returns 5" pin `max_results=5` or expect 10.
- **B3 chat scope** (FR-008-010): `chat.answer(question, paper_ids, conn, client)`; new
  `db.papers_by_ids(conn, ids)` (paper + latest result per id, order kept, unknown ids skipped);
  context = that set only; citations validated against the set; empty set -> refusal, no LLM.
  `ChatIn.paper_ids: list[str]` required, max 50 (config `chat_max_ids = 50`; `chat_top_k` no
  longer used by chat). `prompts/chat.md` states the context is the user's current result set.
  `MockClient.text` overlap rule per contracts/api.md (fixes the mock advisory: generic
  out-of-scope questions no longer get canned cited answers).
- **Indicator** (FR-012): FE-only per brief D14-D18; no progress endpoint (research R11).
- **Redesign** (FR-012): FE per brief D1-D13, D22-D35; textContent-only rendering kept.
- **Browser e2e** (SC-004, SC-006-SC-008): BE harness (research R12) + FE specs.

UI test hooks (stable selectors FE MUST keep; e2e specs use only these): `#query`, `#submit`,
`#working` (working card, visible only while a triage runs; load-more uses the compact variant
`.working--compact` near `#load-more`), `#paper-list` with
`li.paper[id="paper-<id>"]`, links `a[data-link="abs"]` and `a[data-link="pdf"]` inside each
row, `#load-more` (button; absent from the DOM or `hidden` when not offered), `#question`,
`#ask` (chat submit), `#chat-log` with `li.turn`, refusal `.turn__a--refused`, citations
`a.cite`.

## Complexity Tracking

None. No constitution violations.
