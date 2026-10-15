# v3 BE lane, Waves F+G: QA results

Date: 2026-10-03. Scope: T043-T051 (cea8d6d..b585d63) and T057-T059 (c678faf, b86b1fd, 6d9f720), HEAD 6d9f720.
BE scope only (frontend-builder mid-wave, README being edited).

## Result: PASS, 0 failures

## Automated
- `MOCK_LLM=1 uv run pytest -q --ignore=tests/frontend`: 344 passed.
- `uv run ruff check src tests --exclude tests/frontend`: all checks passed.
- No network: `tests/conftest.py` fixture asserts no non-local request is made; the app builds its HTTP client through `net.make_http(mock)`, which uses `httpx.MockTransport` under `MOCK_LLM=1`.

## Live API probe
Server: `MOCK_LLM=1 uvicorn paper_triage.app:app --port 8766`, temp `PAPER_TRIAGE_DB` and `PAPER_TRIAGE_DATA_DIR` under the session scratchpad. 88 checks, all pass. Servers killed after the run.

| Area | Checked | Result |
|---|---|---|
| Save | 201 `created: true`, `pdf.status` pending in the response, tags `["diffusion","models"]`, directory null; 404 "no stored result for this paper"; 422 missing `paper_id` | pass |
| PDF states | 2401.00001 pending -> ready (pages 3); 2401.00005 -> failed "Not a PDF." | pass |
| Re-save | 200 `created: false`; `saved_at`, topic, directory, pdf unchanged; tags merged to `["diffusion","models","guidance"]`; no duplicate row (total 2); re-save with the original topic leaves tags unchanged | pass |
| Saved flag | `saved` on every triage result and on `GET /api/papers`; true for saved, false otherwise; false again after unsave | pass |
| Retry | failed -> 202 `{"pdf":{"status":"pending","error":null,"pages":null}}`; ready -> 409; pending -> 409; unsaved -> 404 | pass |
| PDF route | 200 `application/pdf`, `Content-Disposition: inline`, `Cache-Control: private, max-age=3600`, `Accept-Ranges: bytes`, length 3117; `Range: bytes=0-99` -> 206 `bytes 0-99/3117`; suffix and open-ended ranges 206; `bytes=9999-` -> 416; failed/pending/unsaved -> 404 "PDF not available"; missing param 422 | pass |
| Directories | create 201 trimmed; empty/blank 422 "Enter a name."; 41 chars 422 "Names can be up to 40 characters."; 40 chars ok; duplicates "network"/"NETWORK" 409 with name as typed; "Unsorted", "all saved" 409; rename 200, rename to duplicate 409, rename to own name in other case 200; unknown id 404; list A-Z | pass |
| Move | to directory, count updates, `unsorted_count` updates; to null; unsaved paper 404; unknown directory 404 | pass |
| Delete directory | `{"deleted": true, "moved": 2}`; papers land in Unsorted | pass |
| Annotations CRUD | highlight 201 default yellow, mint ok; note 201 with `rects: []`, `quote: ""`; shape has exactly the 12 documented keys; list ordered by page; PATCH color+note, `note: ""` ok on a highlight, 422 on a note, 422 bad color, 404 unknown; DELETE 204 empty body, second delete 404 | pass |
| Annotation validation (422, plain string detail) | page 0; page 4 > pages 3; bad color; bad kind; no rects; 51 rects; rect value >1 and <0; rect with 3 values; empty quote; quote 501; note 501; note kind without note, with rects, with quote | pass |
| Annotation boundaries | 50 rects, quote 500 chars, values 0 and 1 -> 201 | pass |
| Annotation state errors | unsaved 404; PDF failed or pending 409 | pass |
| `highlight_count` | counts kind highlight only (2 highlights plus 1 note -> 2) | pass |
| Paper chat | "Quartzite" -> `pages [2]`, answer has `[p.2]`; "Obsidian" -> `[3]`; "capital of France" -> `refused: true`, `pages []`; PDF failed or pending -> 200 refused "Chat needs the PDF text. It is not ready yet."; unsaved 404; empty, whitespace or missing question 422; history of 6 ok, 7 -> 422 "history: at most 6 turns" | pass |
| Lazy extraction | `paper_pages` has 0 rows before the first chat and 3 after it; none for the failed-PDF paper | pass |
| Unsave | 200 `{"deleted": true, "annotations": 3}`; PDF file gone from disk; no rows left in annotations, paper_pages, paper_files, saved_papers, saved_tags; second unsave 404; PDF route 404 | pass |
| Startup sweep | set a row to pending in the DB, restart: status `failed`, error "Download interrupted. Try again." | pass |
| 50 MB cap, not-a-PDF | live: not-a-PDF via 2401.00005. 50 MB: unit tests `test_too_big_fails_and_leaves_no_file`, `test_content_length_over_cap_fails_early` (error "PDF is larger than 50 MB.", no file left) | pass |

## Observations (not failures)
- `POST /api/library` needs `topic` exactly as the triage response returns it. The response normalizes the query ("Guidance, Diffusion" -> "Guidance Diffusion"); posting the raw query returns 404 "no stored result for this paper". The contract says to use the response `topic`, so this is by design. The page must send `data.topic`, not the typed query.
- `Range: items=1-2` (unknown unit) returns 400. RFC 9110 says a server may ignore an unknown unit and send 200. pdf.js sends `bytes`, so no impact.
- Save of a failed result (409 "only completed results can be saved") is covered by `tests/test_library_api.py`; the mock feed cannot produce a failed topic result for a live probe, and a direct-PDF 404 returns an error entry with no stored result.
- Paper chat while PDF pending/failed returns 200 with `refused: true`, per the contract (not 409).

## Not run (out of scope for this pass)
Full suite with `tests/frontend`, e2e browser tests, `impeccable detect`, no-mistakes gate (frontend and README still in flight).
