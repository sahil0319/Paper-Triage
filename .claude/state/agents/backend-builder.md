
## T018+T019 done (7912d61, next commit) - API facts for frontend
- POST /api/chat req `{"question": str}` (blank/missing -> 422 `{"detail": str}`); model failure -> 502 `{"detail"}`.
- 200 resp `{"answer": str, "citations": [paper_id], "refused": bool, "dropped_citations": [paper_id]}` (all 4 keys always).
- citations: deduped, in order of appearance; every id is a stored paper id -> link to `#paper-<id>` (ids may contain `:` `/` `.`; escape for selectors).
- refused=true: answer is calm plain sentence (no sentinel), citations=[]; empty store also refused (no LLM). Render as distinct non-error state.
- answer text has inline `[id]` markers; dropped_citations = unknown ids the model emitted (already removed from `citations`, markers may remain in answer text; don't link them).

## Wave A BE done
- T018 7912d61, T019 63129d5 (API facts above), T021(api) ca2e161 (not ticked; FE ticks), T022 c525ee3.
- full pytest 156 pass, ruff clean. Contract api.md got +2 lines (refusal text, 502 on model failure).
- next: T024 README (wave C). FE T020 unblocked.

## T024 README
- goal: README. status: done, commit T024. verified mock server /api/status on 8767, pytest 156 pass, ruff clean.
- finding: app does not load .env (no dotenv); README says source it. .env.example unreadable by my tools, not verified content.
- next: tester

## T025 openai provider
- status: done, commit "T025: openai provider"
- API facts: GET /api/status now {mock, model, provider, paper_count}; provider additive ("anthropic"|"openai"). No other shape change.
- next: tester

## backend-builder T026
goal: concurrent triage + ranker calibration. status: done (commit T026). findings: .env.example read/write denied by permissions, TRIAGE_CONCURRENCY not appended. next: tester; user re-run live.

## Wave D BE: T027 1228e61, T028 a3e39c4, T029 cec5ee7, T030 4e0d601, T031 f3de788
API facts v2 (matches contracts/api.md, no divergence):
- POST /api/triage req `{query, max_results=10 (1..20), offset=0 (0..1000)}`. Item query (id/URL) + offset>0 -> 422 `{"detail":"offset only applies to topic searches"}`.
- resp adds `offset`, `next_offset` (int|null), `has_more` (bool). Topic: next_offset = offset + entries returned; has_more = total > next_offset. Items or FetchError: `null`/`false`. Load-more: same query, max_results 5, offset = prev next_offset. Mock feed: 15 papers 2401.00001..15, so 10 + 5.
- every result item (triage + GET /api/papers) has `abs_url`, `pdf_url`: arxiv -> https://arxiv.org/abs|pdf/<id>; pdf source -> abs_url null, pdf_url = input URL.
- POST /api/chat req `{question, paper_ids: [str]}`; paper_ids REQUIRED (missing -> 422), dupes ignored, >50 -> 422 `{"detail":"paper_ids: at most 50 ids"}`. Resp unchanged `{answer, citations, refused, dropped_citations}`.
- chat context = paper_ids only. Empty/unstored set -> refused, no LLM, answer "No search results to ask about yet. Run a search first, then ask about its results.". Citation outside set -> dropped_citations. Mock chat answers only if question has a set id or content word (>=4 letters, not stop word) in a set title/abstract; marker words: Progressive, Consistency, Adversarial, Guidance, Survey, Basalt, Cobalt, Quartz, Granite, Obsidian, Feldspar, Gypsum, Marble, Dolomite, Pumice (ids 1..15 in order).
- next: T032, T033. env note: .venv/bin/pytest shebang was broken (pointed to other project); fixed via `uv sync --reinstall-package pytest`.

## Wave D BE complete
T032 b818725 (pytest-playwright + chromium installed, harness tests/e2e_harness.py port E2E_PORT=8766, `-m e2e`), T033 committed. pytest 219 pass (+1 e2e), ruff clean. No contract deviation. top_papers/chat_top_k left in db/config unused by chat (tested, harmless). next: tester.

## T042 README v2
done (README.md only). Covers links, load-more, scoped chat, searching indicator, e2e setup (E2E_PORT 8766). UI wording ("Load 5 more", working card) taken from brief; FE wave E to confirm copy matches. next: tester.

## F-002 / F-005
F-002 6cd65e0: db.touch_results refreshes created_at of reused results in pipeline.triage; regression tests in test_pipeline/test_db. F-005 (next commit): LiveServer bind-checks port before env change + waits for server.started; test added. pytest 229 pass, -m e2e 8 pass, ruff clean. Verified foreign server on 8766 now gives "already in use". next: tester.

## v3 Wave F BE
- T043 cea8d6d tags.keywords. T044 (see log): fixture landed.
- FIXTURE for FE: src/paper_triage/fixtures/sample.pdf, 3 pages, 3117 bytes. p1 = old text, p2 has "Quartzite", p3 has "Obsidian". Generator fixtures/make_sample_pdf.py. Note: "Obsidian" also appears in arxiv_search.xml (paper 2401.00012 title); spec said it must not, but task text fixes the word. Only Quartzite asserted absent from xml.
- T045 932218b, T046 77ff018 (db.py CRUD all landed in T045).
- T047 API facts (match contracts/api.md): POST /api/library {paper_id, topic=""} -> 201|200 {created, paper}; item keys: paper_id,title,authors,source,published,abstract,basis,rank,rank_reason,summary,critique,abs_url,pdf_url,topic,tags,directory_id,saved_at,pdf{status,error,pages},highlight_count. 404 "no stored result for this paper"; 409 "only completed results can be saved"; missing paper_id 422.
  GET /api/library -> {papers,directories:[{id,name,count}],unsorted_count,total}. DELETE /api/library?paper_id= -> {deleted:true,annotations:n} | 404 {"detail":"not in the library"}. triage + GET /api/papers items have saved:bool.
  Decisions: highlight_count = kind 'highlight' only; DELETE annotations = all kinds. Tag order = insertion order (keyword order), not alphabetical.
- T048 API facts: POST /api/directories {name} 201 {id,name,count:0}; PATCH /api/directories/{id} {name} 200 {id,name,count}; DELETE /api/directories/{id} 200 {deleted:true,moved:n}; unknown id 404. Errors {"detail": ...}: 422 "Enter a name." / "Names can be up to 40 characters."; 409 '"<name>" already exists.' (name as typed, trimmed; also for Unsorted/All saved).
  POST /api/library/move {paper_id, directory_id|null} -> 200 {paper_id, directory_id}; unknown paper or dir 404. GET /api/library directories A-Z by casefold, unsorted_count, total.
- T049 771ee3d pdfstore. T050 API facts: save (new) starts bg download; in TestClient/harness bg task finishes before next request. POST /api/library response shows pdf.status "pending"; poll GET /api/library -> pdf {status: pending|ready|failed, error, pages}. Errors: "Not a PDF.", "PDF is larger than 50 MB.", "Download failed (HTTP n).", "Download timed out.", "Could not reach the server.", "PDF could not be read.", "Download interrupted. Try again.".
  GET /api/library/pdf?paper_id= -> 200 application/pdf, Content-Disposition inline, Cache-Control private max-age=3600, Accept-Ranges bytes, Range -> 206; not saved/not ready 404 {"detail":"PDF not available"}; missing param 422.
  POST /api/library/retry {paper_id} -> 202 {pdf:{status:"pending",error:null,pages:null}}; ready/pending 409; unsaved 404. DELETE /api/library removes the file. .mjs MIME text/javascript registered in create_app(). Data dir: PAPER_TRIAGE_DATA_DIR (e2e harness sets <tmp>/data).
  Mock: 2401.00005 -> failed "Not a PDF."; use 2401.00001 for ready.
- T051 API facts: annotation = {id,paper_id,page,kind,color,rects,quote,prefix,suffix,note,created_at,updated_at} (no `top`).
  GET /api/annotations?paper_id= -> {annotations:[..]} order page,top,id; unsaved 404. POST /api/annotations -> 201 annotation; 404 unsaved, 409 PDF not ready, 422 bad body or page > pdf.pages. Highlight: rects 1..50 [x,y,w,h] in 0..1, quote 1..500, prefix/suffix <=64, note <=500, color yellow|mint|peach default yellow. Note: kind "note", note 1..500, rects [] and quote "" required (else 422).
  PATCH /api/annotations/{id} {color?,note?} -> 200; note "" on kind note -> 422; 404 unknown. DELETE -> 204 (empty body) | 404. GET /api/library highlight_count counts kind=highlight only. 422 body is {"detail": "<field>: <msg>; ..."} (plain string).
- Wave F BE T043-T051 all committed. Next: Wave G T057 (paper chat), T058, T059.
- T057 c678faf MockClient page mode. T058 API facts: POST /api/paper-chat {paper_id, question (non-empty), history:[{question,answer}] (<=6, else 422 "history: at most 6 turns")} -> 200 {answer, pages:[int], refused, dropped_pages:[int]}. Unsaved 404 (detail "not in the library"); empty question 422; LLM error 502 {"detail":"model call failed: .."}. Not-ready PDF (pending|failed) -> 200 refused, answer "Chat needs the PDF text. It is not ready yet."; no text -> refused "This PDF has no extractable text."; model out-of-scope -> refused "I can only answer from this paper, and it does not cover that." Mock: question word (>=4 letters) in a page text -> "Mock answer from this paper [p.N]." (Quartzite -> p.2, Obsidian -> p.3, "capital of France" -> refused). LLM call runs outside the shared lock.
- T059: harness LiveServer now mkdtemp's PAPER_TRIAGE_DATA_DIR in start() (attr server.data_dir) and rmtree's it in stop(). v3 offline smoke in tests/test_e2e_mock.py. Real server: PDF download runs AFTER the save response (race); poll GET /api/library until pdf.status != pending. Wave G BE done: T057 c678faf, T058 b86b1fd, T059 below. pytest (excl. tests/frontend) 344 pass.
- T065: README.md + SETUP_LOG.md v3 written (Library, viewer, paper chat, data dir, vendored pdf.js, mock ids, personal-use note). UI described per spec/brief.
- F-014 fix: MockClient page mode answers the 3 UI starters (main claim -> first text page, baselines/limitations -> first page containing the word; sample.pdf: p.1, p.1, p.3) and refuses off-paper with 'This paper does not cover that.' (paper_chat strips sentinel, so API answer = that sentence). Contract wording unchanged.
