# Implementation Plan: Paper Triage Assistant

**Branch**: `001-paper-triage` (no git branch; orchestrator commits on current branch) |
**Date**: 2026-10-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-paper-triage/spec.md`

## Summary

Local FastAPI app + one static page. Input (topic or ids/URLs) -> Fetcher (arXiv API, throttled,
cached; PDF via pypdf, abstract fallback) -> Summarizer -> Critic -> Ranker (three LLM calls per
paper, each its own module + prompt file, Pydantic-validated) -> SQLite. Grounded chat stuffs top
20 stored papers into context, validates `[id]` citations server-side, refusal sentinel. One LLM
wrapper with a mock twin; `MOCK_LLM=1` also swaps HTTP to fixtures. See [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.11+ (uv-managed)

**Primary Dependencies**: fastapi, uvicorn, httpx, pydantic v2, anthropic, pypdf. Dev: pytest,
ruff. (No others; constitution I.)

**Storage**: SQLite via stdlib `sqlite3`; schema in [data-model.md](data-model.md)

**Testing**: pytest (+ FastAPI `TestClient`), ruff; all offline with `MOCK_LLM=1`

**Target Platform**: local macOS/Linux, browser at 127.0.0.1

**Project Type**: single project web app (API + static page)

**Performance Goals**: mock 5-paper triage < 5 s (SC-001); live bound by arXiv 3 s/request

**Constraints**: offline tests; arXiv 1 req/3 s; <=20 papers/run; 40k chars text per LLM call;
model from `ANTHROPIC_MODEL` (default `claude-opus-5-5` in `config.py` only);
T025: `LLM_PROVIDER=openai` swaps in `OpenAIClient` (`OPENAI_API_KEY`, `OPENAI_MODEL`), same wrapper

**Scale/Scope**: 1 user, tens to low hundreds of stored papers

## Constitution Check

*Pre-research and post-design: PASS.*

| Principle | Check | Status |
|---|---|---|
| I Small | 6 runtime deps, one module per agent, prompts for 4 LLM agents, fetcher LLM-free | PASS |
| II Offline | `llm.get_client()` mock twin; `httpx.MockTransport` fixtures; tests need no key/net | PASS |
| III Grounded | `[id]` regex validation vs store, `NOT_IN_STORED_PAPERS`, empty-store short-circuit | PASS |
| IV One page | one `index.html`, no auth/deploy/queue; sync triage request | PASS |
| V Honest critique | `basis` field + UI flag, "not stated" prompt rule, rank clamp | PASS |

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
└── test_e2e_mock.py      # full flow smoke through HTTP
```

**Structure Decision**: single `src/paper_triage` package (src layout), flat modules; runtime
agents are top-level modules named after the agent.

## Key Design Notes

- Pipeline per paper: fetch -> summarize -> critique -> rank, sequential; any agent failure
  marks result `failed` with reason, others continue. Existing (paper_id, topic) result reused.
- Ranker input: topic + title + abstract + summary (not full text) to keep cost low.
- Mock fixtures: Atom feed with 5 entries; mock transport returns `sample.pdf` for 4 and invalid
  bytes for 1 (exercises abstract fallback). Unknown arXiv id -> empty feed -> "not found".
- UI (one page): input + submit on top; ranked list (rank, title, id, reason; basis flag);
  expandable critique (`<details>`); chat panel beside (wide) / below (narrow); citations as
  anchors to `#paper-<id>`; refusal styled as a distinct, calm state; mock label in header;
  loading state on submit. Builder MUST re-read DESIGN.md + PRODUCT.md and apply
  frontend-design / impeccable guidance before UI tasks.

## Complexity Tracking

None. No constitution violations.
