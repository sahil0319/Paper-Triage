# HTTP Contract (local only, JSON)

All errors: `{"detail": "<plain message>"}` with 4xx/5xx.

## GET /

Single-page UI (`static/index.html`).

## GET /api/status

`200 {"mock": bool, "model": str, "provider": "anthropic"|"openai", "paper_count": int}`
(`provider` additive, T025; `model` is the active provider's model.)

## POST /api/triage

Request `{"query": str, "max_results": int = 10}` (1..20, else 422).
Parsing of `query`: tokens split on whitespace/commas. Tokens matching an arXiv id
(`\d{4}\.\d{4,5}(v\d+)?`, old `[a-z\-]+(\.[A-Z]{2})?/\d{7}`, or arxiv.org abs/pdf URL) or any
other `http(s)` URL are items; remaining words joined form `topic`. No items -> topic search.
Items and no topic -> topic `""`. Empty query -> 422.

`200`:

```json
{"topic": "str",
 "results": [{"paper_id": "2401.01234", "title": "..", "authors": [".."], "source": "arxiv",
   "basis": "fulltext", "rank": 8, "rank_reason": "..", "summary": {..}, "critique": {..},
   "status": "ok", "error": null}],
 "errors": [{"input": "9999.99999", "reason": "not found"}]}
```

`results` sorted by rank desc (failed last). Zero found -> `results: []` (UI: "No papers found").

## GET /api/papers?topic=<t>

Stored results; default topic = most recent run's topic. Same item shape, same order.

## POST /api/chat

Request `{"question": str}` (non-empty, else 422).
`200 {"answer": str, "citations": [str], "refused": bool, "dropped_citations": [str]}`.
Rules: empty store -> `refused: true`, no LLM call. Sentinel `NOT_IN_STORED_PAPERS` or zero
valid citations -> `refused: true`. Every id in `citations` exists in `papers`.
Refusal `answer` is a plain sentence (never contains the sentinel). Each call (answered or refused,
not 422/502) is stored in `chat_turns`. Model failure -> `502 {"detail": "model call failed: .."}`.
