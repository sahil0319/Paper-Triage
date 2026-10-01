# Research: Paper Triage Assistant

Source notes: docs/research/paper-triage.md (arXiv, PDF, prompts, chat) + claude-api skill
(cached 2026-09-25). Each entry: Decision / Rationale / Alternatives.

## R1 arXiv access

- **Decision**: `httpx` GET `http://export.arxiv.org/api/query` (`search_query=all:<terms>` or
  `id_list=`), `sortBy=relevance`, `max_results<=20`; parse Atom with stdlib `xml.etree`.
  Process-wide throttle: min 3.0 s between arXiv requests (lock + last-call time; clock and
  sleep injectable). Raw responses cached in SQLite `arxiv_cache` keyed by normalized query.
  Ids normalized: strip `http(s)://arxiv.org/abs/` prefix and `vN` suffix; version kept in a
  column. PDF from Atom `<link title="pdf">`.
- **Rationale**: arXiv ToU (1 req/3 s); stdlib parser avoids a dep.
- **Alternatives**: `feedparser` (extra dep), `arxiv` pip package (hides throttle/cache).

## R2 PDF text extraction

- **Decision**: `pypdf` behind `extract_text(pdf_bytes) -> str` in `extract.py`. Truncate at a
  line matching `^references$` (case-insensitive) when found after 50% of text; cap 40,000 chars
  to LLM. Any exception or <500 chars extracted -> basis `abstract`.
- **Rationale**: BSD license, pure Python; one swap point for PyMuPDF (AGPL, not bundled).
- **Alternatives**: PyMuPDF (faster, AGPL), pdfminer.six (slow).

## R3 Non-arXiv PDF URLs

- **Decision**: any `http(s)` URL not on arxiv.org is a direct PDF. id = `pdf:` +
  `sha256(url).hexdigest()[:12]`. Title from PDF metadata `/Title`, else URL basename. Abstract
  = first 1,500 chars of extracted text. No throttle beyond one request at a time; 20 s timeout.
- **Rationale**: clarified in spec; stable deterministic id.

## R4 LLM client and structured output

- **Decision**: `llm.py` exposes `LLMClient` protocol with `parse(system, user, schema) -> BaseModel`
  and `text(system, user) -> str`. `AnthropicClient` uses `client.messages.parse(model=...,
  max_tokens=16000, system=..., messages=[...], output_format=Schema, output_config={"effort":
  "low"})` -> `.parsed_output`; chat uses `messages.create` text. No `temperature` (rejected by
  current models). `stop_reason == "refusal"` -> raises `LLMRefusal` -> item marked failed.
  Pydantic validation error -> one retry -> item failed. `MockClient` returns deterministic
  instances of the requested schema keyed by sha256 of the `<paper id=..>` in the prompt; chat
  mock cites the first stored id in context, or returns the refusal sentinel if the question
  contains "out of scope" or no ids are in context. `get_client()` picks mock when `MOCK_LLM=1`.
- **Model**: `ANTHROPIC_MODEL` env, documented default `claude-opus-5-5` in `config.py` only.
- **Rationale**: one wrapper = one mock point (constitution II); SDK helper validates schema.
- **Alternatives**: one combined call per paper (cheaper, but product requires separate
  Summarizer/Critic/Ranker modules + prompt files); server-side refusal `fallbacks` beta
  (deferred: adds beta surface; refusal handled as failed item).

## R5 Prompts

- **Decision**: `src/paper_triage/prompts/{summarizer,critic,ranker,chat}.md`, loaded at call
  time. Paper content wrapped `<paper id="..." basis="fulltext|abstract">..</paper>`. Critic:
  "only claims supported by supplied text; write 'not stated' rather than guess". Ranker gets the
  topic, summary and abstract, rubric 0-2/3-5/6-8/9-10; rank clamped 0-10 in code. With no topic
  (id-only input), ranker rates overall reading priority and says so in the reason.
- **Rationale**: research §3; honest-critique principle V.

## R6 Grounded chat

- **Decision**: context stuffing: top 20 stored papers by latest rank, each as `<paper id=..>`
  with title, abstract, summary, critique. Instruction: cite as `[<id>]` using the exact id;
  if unanswerable reply exactly `NOT_IN_STORED_PAPERS` + one sentence. Server: regex
  `\[([^\[\]\s]+)\]`, keep ids in store, list unknown in `dropped_citations` and strip them
  from the answer text. Answer with zero valid citations and no sentinel -> treated as refusal.
  Empty store -> refusal without LLM call.
- **Rationale**: research §4; Citations API is not needed for a small corpus and keeps the
  mock simple.
- **Alternatives**: Citations API document blocks (richer spans, harder to mock); FTS5 retrieval
  (not needed at <=20 papers).

## R7 Mock network

- **Decision**: fetcher takes an `httpx.Client` + `Throttle` from `net.make_http()`; under
  `MOCK_LLM=1` it is an `httpx.MockTransport` client with a 0 s throttle serving bundled fixtures (`src/paper_triage/fixtures/`: one Atom feed of
  5 papers, one tiny PDF). Tests use the same transport.
- **Rationale**: FR-011 requires full flow offline with no key.

## R8 Web layer

- **Decision**: FastAPI, synchronous triage request (<=20 papers; sequential), static files
  served from `src/paper_triage/static/`. Run: `uv run uvicorn paper_triage.app:app`.
- **Rationale**: no job queue (constitution IV).
