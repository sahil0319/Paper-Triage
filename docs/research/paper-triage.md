# Research: paper-triage

Context: Python 3.11+, FastAPI, SQLite, Anthropic SDK, `MOCK_LLM=1` offline tests. Date 2026-10-01.
Tags: [V] fetched and verified this session, [U] prior knowledge, unverified.

## 1. arXiv API
- Endpoint: `GET http://export.arxiv.org/api/query` (GET or POST). Returns Atom XML. [V] https://info.arxiv.org/help/api/user-manual.html
- Params: `search_query` (prefixes `ti: au: abs: cat: all:`, ops `AND OR ANDNOT`, quoted phrase `%22..%22`), `id_list` (comma-separated), `start` (0-based), `max_results` (cap 2000/call, 30000 total/query), `sortBy` (relevance | lastUpdatedDate | submittedDate), `sortOrder`. If both `search_query` and `id_list` are given, the ID list is filtered by the query. [V] same URL.
- Atom entry fields to store: `<id>` (abs URL), `<title>`, `<summary>` (abstract), `<author><name>` (repeats), `<published>`, `<updated>`, `<arxiv:primary_category term=..>`, `<link rel="related" title="pdf" href=..>`. [V] same URL.
- ID lookup: `?id_list=2401.01234,2402.00001v2`. New scheme `YYMM.NNNNN[vN]` (5-digit since 1501); old scheme `archive/YYMMNNN` (e.g. `math.GT/0107001`). No version means latest. Normalise by stripping the `vN` suffix and the `http://arxiv.org/abs/` prefix, but keep the version fetched. [V] https://info.arxiv.org/help/arxiv_identifier.html
- PDF URL: `https://arxiv.org/pdf/<id>` (optionally `v<n>`; `.pdf` suffix is optional). Prefer the `<link title="pdf">` href from Atom. [U for exact pattern; link element is V]
- Rate limit: max 1 request per 3 seconds, single connection at a time, shared across all your machines. [V] https://info.arxiv.org/help/api/tou.html
- Terms: metadata may be stored and shared (CC0). Do not redistribute PDFs from your own servers. Storing a local, single-user copy of extracted text for personal research is the grey zone; keep it local and do not expose it. [V, interpretation mine] same URL.
- Rec: one `httpx` client with a process-wide 3 s throttle (async lock + last-call timestamp), parse Atom with `feedparser` or stdlib `xml.etree`, cache metadata in SQLite keyed by id+version, fetch PDF only on demand. Abstract-only fallback when PDF extraction fails.

## 2. PDF text extraction (Python)
| Lib | License | Notes |
|---|---|---|
| pypdf | BSD-3 [U] | Pure Python, light install. Slowest-tier on large docs; can blow RAM on huge streams (docs cite ~10 GB for a 300 MB stream); no OCR; weak whitespace/tables. [V] https://pypdf.readthedocs.io/en/stable/user/extract-text.html |
| PyMuPDF (fitz) | AGPL-3 or commercial [V] | Fastest: 7,031 pages in ~8 s vs pypdf 101 s vs pdfminer 227 s (vendor benchmark). Binary wheels (MuPDF bundled, larger install). PyMuPDF4LLM gives markdown. [V] https://pymupdf.readthedocs.io/en/latest/about.html |
| pdfminer.six | MIT [U] | Pure Python, best layout analysis of the pure-Python options, slow. |
- AGPL matters only if the app is distributed or network-served to others. This is a local single-user tool, but the repo license should be decided before depending on it.
- Rec: default to pypdf (permissive, zero native deps, adequate for born-digital arXiv PDFs); put extraction behind one `extract_text(path) -> str` function so PyMuPDF can be swapped in as an optional extra. Cap pages/characters (e.g. first N chars, drop references) before any LLM call. Two-column layout will scramble ordering; accept it for triage.

## 3. Prompt patterns: summarize / critique / rank
- Structured output: the SDK supports `client.messages.parse(..., output_format=PydanticModel)` -> `response.parsed_output`, or raw `output_config={"format":{"type":"json_schema","schema":{...,"additionalProperties":False}}}` then `json.loads(text_block.text)`. Strict tool use (`"strict": True` with `tool_choice={"type":"tool","name":..}`) is the alternative. First call per schema has compile latency; grammars cached 24 h. [V] https://platform.claude.com/docs/en/docs/build-with-claude/structured-outputs . Confirm model ids against https://platform.claude.com/docs/en/about-claude/models/overview before pinning (page examples mix ids).
- One call per paper returning one object, so Rank is consistent and the DB row maps 1:1:
  `{summary: str(<=120 words), contributions: [str], weak_claims: [{claim, why}], overclaims: [{claim, evidence_gap}], missing_baselines: [str], rank: int 0-10, rank_reason: str(1-2 sentences)}`.
- Prompt rules (all [U], standard practice): system role "skeptical reviewer"; input is title + abstract + extracted body, delimited with XML tags (`<paper id="2401.01234">`); instruct "only claims supported by the supplied text; if the text lacks baselines/results say 'not stated' rather than guessing"; give the user's topic and a rubric for rank anchors (0-2 off-topic, 3-5 tangential, 6-8 relevant, 9-10 must read); require rank_reason to cite the topic match; temperature low. Critique from abstract-only must be flagged (`basis: "abstract" | "fulltext"` field).
- Validate with Pydantic; one retry on failure; clamp rank to 0-10.
- Mock mode: `MOCK_LLM=1` returns deterministic fixtures from the same Pydantic schema, selected by paper-id hash; UI shows an "offline/mock" label (PRODUCT.md principle 4).
- Rec: Pydantic model + `messages.parse`, one call per paper, with a small LLM client wrapper that has a mock twin behind the same interface.

## 4. Grounded chat
- Context stuffing: stored papers are few (single researcher), so put summaries + critiques + abstract for the selected set (or top-k by rank) in the prompt, each wrapped `<paper id="2401.01234" title="..">`. Fall back to keyword/FTS5 retrieval over SQLite chunks if the set outgrows the context window. [U]
- Citation format: instruct "cite every factual claim as [arXiv:ID]; never cite an id not in context", then post-validate: regex the ids from the answer and check against stored ids; strip or flag unknown ones. UI renders ids as links to the stored paper. [U]
- Native option: Citations API on `document` blocks with `"citations": {"enabled": true}`; returns `char_location` / `content_block_location` with `cited_text` (not billed as output tokens) and `document_index`; set `title` = paper id. All active models support it. Incompatible with `output_config.format` (400 error), so use it for chat only, not for the JSON triage calls. [V] https://platform.claude.com/docs/en/build-with-claude/citations
- Refusal: system instruction "answer only from the provided papers; if not answerable reply exactly `NOT_IN_STORED_PAPERS` plus one sentence on what is missing". Detect the sentinel server-side and render a deliberate refusal state. Also short-circuit before the LLM when zero papers are stored. [U]
- Rec: context-stuff stored summaries/critiques with `<paper id>` tags, use the Citations API for chat, add a server-side check that every cited id exists, and a sentinel for refusals.

## Clarification questions
1. Should the repo/app license be permissive (rules out PyMuPDF AGPL) or is AGPL acceptable?
2. Is critique allowed on abstract-only when the PDF fails, or must it be skipped?
3. Is storing extracted full text in SQLite acceptable, or only metadata + LLM outputs?
4. Which Claude model id(s) for triage vs chat, and is there a cost cap per run?
5. Expected corpus size per run (10 or 200 papers)? Drives batching, throttling, and context stuffing vs retrieval.
6. Should PDF URLs outside arXiv be supported in v1 (non-arXiv hosts have no rate-limit contract)?

DONE
