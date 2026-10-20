# HTTP Contract (local only, JSON)

All errors: `{"detail": "<plain message>"}` with 4xx/5xx.

## GET /

Single-page UI (`static/index.html`).

## GET /api/status

`200 {"mock": bool, "model": str, "provider": "anthropic"|"openai", "paper_count": int}`
(`provider` additive, T025; `model` is the active provider's model.) T077 (LLM config,
2026-10-20): `provider` is the trimmed, lowercased `LLM_PROVIDER` value and `model` is
`AGENT_MODEL` or the provider default. The endpoint never fails on LLM config: when
`LLM_PROVIDER` is unset or unknown, `provider` is that value (`""` when unset) and `model` is
`AGENT_MODEL` or `""`; the configuration error surfaces only on the first LLM call. Shape and
field names unchanged.

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

v3 page behavior (FR-008a, shipped as F-006/F-007/F-008): whenever the visible result set
changes (new search, load-more, reload) the page clears the transcript and sends the new set.

---

## v3 Library endpoints

Paper ids may contain `/` (old arXiv ids such as `math.GT/0107001`), so paper ids travel in the
JSON body or the `paper_id` query parameter, never as a path segment. Data shapes:
[data-model.md](../data-model.md) "v3 tables". Status values are API values; the brief maps
them to copy (`pending` -> "Downloading PDF…", `ready` -> "PDF ready", `failed` ->
"PDF unavailable").

## v3 change to POST /api/triage and GET /api/papers

Every result item gains `saved: bool` (true when `saved_papers` has the paper). When a topic
search (topic non-empty) returns an already saved paper, `tags.keywords(topic)` are merged into
its tags (no other Library change).

## GET /api/library

`200`:

```json
{"papers": [{"paper_id": "2401.00001", "title": "..", "authors": [".."], "source": "arxiv",
   "published": "2024-01-01", "abstract": "..", "basis": "fulltext", "rank": 8,
   "rank_reason": "..", "summary": {..}, "critique": {..},
   "abs_url": "https://arxiv.org/abs/2401.00001", "pdf_url": "https://arxiv.org/pdf/2401.00001",
   "topic": "diffusion models", "tags": ["diffusion", "models"], "directory_id": null,
   "saved_at": "2026-10-03T10:00:00+00:00",
   "pdf": {"status": "ready", "error": null, "pages": 3}, "highlight_count": 2}],
 "directories": [{"id": 1, "name": "network", "count": 4}],
 "unsorted_count": 3, "total": 7}
```

`papers` ordered by `saved_at` desc. Snapshot fields are the values captured at first save.
`directories` ordered A-Z by `name_key`. Tag counts and filtering are computed by the page.

## POST /api/library

Request `{"paper_id": str, "topic": str}` (`topic` = the `topic` of the triage response or
`GET /api/papers` response that showed the card; `""` for item runs).

- New save -> `201 {"created": true, "paper": <library item>}`; snapshot built server-side from
  `papers` + the `(paper_id, topic)` result; tags = `tags.keywords(topic)`; directory Unsorted;
  `pdf.status = "pending"` and the download starts as a background task after the response.
- Already saved -> `200 {"created": false, "paper": <library item>}`; snapshot, `saved_at`,
  directory and PDF unchanged; tags of `topic` merged.
- No stored result for `(paper_id, topic)` -> `404 {"detail": "no stored result for this paper"}`;
  result `status == "failed"` -> `409 {"detail": "only completed results can be saved"}`.

## DELETE /api/library?paper_id=<id>

Unsave (the page confirms first). Deletes the saved entry, tags, file row and file on disk,
prepared page text and annotations. `200 {"deleted": true, "annotations": <n>}`. Not saved ->
`404`.

## POST /api/library/retry

Request `{"paper_id": str}`. Only when `pdf.status == "failed"`: status -> `pending`, download
restarts in the background; `202 {"pdf": {"status": "pending", "error": null, "pages": null}}`.
Status `pending` or `ready` -> `409`; not saved -> `404`.

## GET /api/library/pdf?paper_id=<id>

`200` PDF bytes, `Content-Type: application/pdf`, `Content-Disposition: inline`,
`Cache-Control: private, max-age=3600`; Range requests honored (206). Not saved or status not
`ready` -> `404`. The page and "Open PDF in new tab" both use this same-origin URL.

PDF download rules (background): arXiv -> `https://export.arxiv.org/pdf/<id>`, fallback
`https://arxiv.org/pdf/<id>` on 404/5xx, shared 3 s throttle; direct PDF -> `papers.pdf_url`,
no throttle. Timeouts connect 10 s, read 60 s. Fails (status `failed`, `error` plain text) on:
HTTP error, body not starting with `%PDF-` ("Not a PDF."), more than 50 MB ("PDF is larger
than 50 MB."), timeout, unreadable by pypdf. Mock mode: mock transport serves `sample.pdf`;
`2401.00005` returns non-PDF bytes (-> failed); hosts ending `.invalid` -> 404 (-> failed).
On startup, `pending` rows become `failed` with "Download interrupted. Try again."

## POST /api/library/move

Request `{"paper_id": str, "directory_id": int | null}` (`null` = Unsorted).
`200 {"paper_id": .., "directory_id": ..}`; unknown paper (not saved) or directory -> `404`.

## Directories

- `POST /api/directories` `{"name": str}` -> `201 {"id", "name", "count": 0}`.
- `PATCH /api/directories/{id}` `{"name": str}` -> `200 {"id", "name", "count"}`.
- `DELETE /api/directories/{id}` -> `200 {"deleted": true, "moved": <n>}` (members -> Unsorted).
- Name rules: trimmed; empty -> `422 {"detail": "Enter a name."}`; > 40 chars ->
  `422 {"detail": "Names can be up to 40 characters."}`; same `casefold()` as another directory,
  or `unsorted` / `all saved` -> `409 {"detail": "\"<name>\" already exists."}`. Unknown id -> `404`.

## Annotations

- `GET /api/annotations?paper_id=<id>` -> `200 {"annotations": [<annotation>]}` ordered by
  `page`, `top`, `id`. Not saved -> `404`.
- `POST /api/annotations` -> `201 <annotation>`. Body `{"paper_id", "page", "kind":
  "highlight"|"note", "color"?: "yellow"|"mint"|"peach" (default yellow), "rects"?: [[x,y,w,h]],
  "quote"?, "prefix"?, "suffix"?, "note"?}`. Highlight: 1..50 rects, all values 0..1, quote
  1..500 chars. Note: rects `[]`, quote `""`, note 1..500 chars. `page` 1..`pdf.pages` (PDF must
  be `ready`, else `409`). Violations -> `422`.
- `PATCH /api/annotations/{id}` `{"color"?, "note"?}` -> `200 <annotation>` (`note: ""` allowed
  for highlights = remove note; `422` for kind `note`). Unknown id -> `404`.
- `DELETE /api/annotations/{id}` -> `204`. Unknown id -> `404`.

Annotation shape: `{"id", "paper_id", "page", "kind", "color", "rects", "quote", "prefix",
"suffix", "note", "created_at", "updated_at"}`.

## POST /api/paper-chat

Request `{"paper_id": str, "question": str, "history": [{"question": str, "answer": str}]}`
(`question` non-empty; `history` optional, at most 6 turns, older turns dropped by the page).
`200 {"answer": str, "pages": [int], "refused": bool, "dropped_pages": [int]}`.
Rules:

- Not saved -> `404`. PDF not `ready` -> `refused: true`, answer "Chat needs the PDF text. It is
  not ready yet.", no LLM call, no extraction.
- Lazy: page text is extracted into `paper_pages` on the first request for that paper with a
  ready PDF; opening the preview or any other endpoint never extracts.
- All pages empty -> `refused: true`, answer "This PDF has no extractable text.", no LLM call.
- Context = the paper's own pages as `<page n="N">` blocks (cap 300,000 chars) + `history` +
  `<question>`. Highlights and notes are never included. Nothing is stored.
- Citations `[p.N]`: N in 1..pages -> `pages` (unique, order of first appearance); others ->
  `dropped_pages`. Sentinel `NOT_IN_STORED_PAPERS` or zero valid page citations ->
  `refused: true` with a plain sentence.
- Mock mode: `MockClient.text` page mode answers only when the question shares a content word
  (>= 4 letters, not a stop word) with a page's text; it answers
  `"Mock answer from this paper [p.N]."` citing the first such page; else the sentinel.
- Model failure -> `502 {"detail": "model call failed: .."}`.
