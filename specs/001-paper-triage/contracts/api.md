# HTTP Contract (local only, JSON)

All errors: `{"detail": "<plain message>"}` with 4xx/5xx.

## GET /

Single-page UI (`static/index.html`).

## GET /api/status

`200 {"mock": bool, "model": str, "provider": "anthropic"|"openai", "paper_count": int}`
(`provider` additive, T025; `model` is the active provider's model.)

## POST /api/triage

Request `{"query": str, "max_results": int = 10, "offset": int = 0}` (`max_results` 1..20,
`offset` 0..1000, else 422). v2: `offset` > 0 is load-more paging and is allowed only for topic
searches; a query that contains any item (arXiv id or URL) with `offset` > 0 ->
`422 {"detail": "offset only applies to topic searches"}`. Load-more calls send the same
`query`, `max_results: 5`, and `offset` = the previous response's `next_offset`.
Parsing of `query`: tokens split on whitespace/commas. Tokens matching an arXiv id
(`\d{4}\.\d{4,5}(v\d+)?`, old `[a-z\-]+(\.[A-Z]{2})?/\d{7}`, or arxiv.org abs/pdf URL) or any
other `http(s)` URL are items; remaining words joined form `topic`. No items -> topic search.
Items and no topic -> topic `""`. Empty query -> 422.

`200`:

```json
{"topic": "str",
 "results": [{"paper_id": "2401.01234", "title": "..", "authors": [".."], "source": "arxiv",
   "basis": "fulltext", "rank": 8, "rank_reason": "..", "summary": {..}, "critique": {..},
   "status": "ok", "error": null,
   "abs_url": "https://arxiv.org/abs/2401.01234",
   "pdf_url": "https://arxiv.org/pdf/2401.01234"}],
 "errors": [{"input": "9999.99999", "reason": "not found"}],
 "offset": 0, "next_offset": 10, "has_more": true}
```

`results` sorted by rank desc (failed last). Zero found -> `results: []` (UI: "No papers found").

v2 fields (additive):

- `abs_url` (str | null) and `pdf_url` (str | null) on every result item, derived by the server:
  `source == "arxiv"` -> `abs_url = "https://arxiv.org/abs/<paper_id>"`,
  `pdf_url = "https://arxiv.org/pdf/<paper_id>"` (id without version, always https);
  `source == "pdf"` -> `abs_url = null`, `pdf_url` = the original URL stored in `papers.pdf_url`.
- `offset` (int): echo of the request offset.
- `next_offset` (int | null): topic search -> `offset` + number of entries the source returned
  for this page (before failures/dedupe); item (id/URL) search -> `null`.
- `has_more` (bool): topic search -> `true` iff the source's reported total
  (`opensearch:totalResults`) > `next_offset`; if the total is missing, `true` iff the page
  returned `max_results` entries. Item search, empty topic page, or `FetchError` -> `false`
  (`FetchError` also sets `next_offset: null`).
- Results of a load-more page contain only that page's papers (may include papers already shown;
  the UI dedupes by `paper_id`).

## GET /api/papers?topic=<t>

Stored results; default topic = most recent run's topic. Same item shape (incl. `abs_url`,
`pdf_url`), same order. No paging fields; after a reload the UI uses `offset` = number of shown
results for its next load-more call when `topic` is non-empty.

## POST /api/chat

Request (v2) `{"question": str, "paper_ids": [str]}`. `question` non-empty, else 422.
`paper_ids` is REQUIRED (missing -> 422) and holds the current result set: the ids the page
shows for the active search, first page plus load-more pages, in display order; 0..50 entries
(more than 50 -> `422 {"detail": "paper_ids: at most 50 ids"}`); duplicates ignored.
`200 {"answer": str, "citations": [str], "refused": bool, "dropped_citations": [str]}`.
Rules:

- Scope = ids in `paper_ids` that exist in `papers` ("set"). Context = the set's papers in the
  order sent (title, abstract, latest summary and critique); no other stored paper is sent.
- Empty `paper_ids`, or none of them stored -> `refused: true`, no LLM call,
  `answer` = "No search results to ask about yet. Run a search first, then ask about its
  results."
- Sentinel `NOT_IN_STORED_PAPERS` or zero valid citations -> `refused: true`.
- Every id in `citations` is in the set. A cited id outside the set (even if stored from an
  earlier search) goes to `dropped_citations`.
- Mock mode (`MOCK_LLM=1`): `MockClient.text` answers only when the question contains a set
  paper id, or a content word (>= 4 letters, lowercase, not in its stop-word list, e.g.
  "paper", "papers", "which", "what", "about", "does", "this", "that", "with", "from") that
  appears in a context paper's title or abstract; it cites the first such paper as `[id]`.
  Otherwise it returns `NOT_IN_STORED_PAPERS ...`. The old "out of scope" substring rule is
  replaced by this rule.
Refusal `answer` is a plain sentence (never contains the sentinel). Each call (answered or refused,
not 422/502) is stored in `chat_turns`. Model failure -> `502 {"detail": "model call failed: .."}`.
