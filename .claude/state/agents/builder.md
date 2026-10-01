
## 2026-10-01 T001-T005
- goal: T001 scaffold, T002 config, T003 models, T004 llm wrapper, T005 db.
- status: all 5 done + ticked, 5 commits (T001 d5449e1, T002 d0a7a4d, T003 f3c519b, T004 e87fc36, T005 see git log). 38 tests pass offline, ruff clean.
- findings: anthropic SDK 1.11.0 messages.parse merges output_config (effort) with output_format -> effort "low" kept. ParsedMessage.parsed_output property exists. Fixed pre-existing ruff I001 in scripts/token_watch.py (in T001 commit). `unset VIRTUAL_ENV` avoids uv warning. db.py API: save_result(conn,pid,topic,*,status,summary,critique,rank,rank_reason,error); top_papers returns dicts w/ parsed summary/critique/rank. MockClient dispatches on schema class Summary/Critique/Rank; reads basis from `<paper id=".." basis="..">` tag.
- next: T006/T007/T008 (parallel-ok), then T009+. Handoff NEXT:tester.

## 2026-10-01 T006-T010
- goal: net, extract, input_parse, fetcher (search/by_ids, PDFs).
- status: all 5 done + ticked + committed (T006 37956f3, T007 be9a0b5, T008 540fa7f, T009 bd4bb10, T010 see git log). 88 tests pass offline, ruff clean.
- findings: net.make_http(True) MockTransport: arXiv feed filtered by id_list; /pdf/2401.00005 -> invalid bytes, others sample.pdf; non-arxiv *.pdf -> sample.pdf (except *.invalid -> 404). Throttle.wait() shared object. input_parse.Item NamedTuple(kind "arxiv"|"pdf", value); ids version-stripped, deduped, "arXiv:" prefix ok. Fetcher(conn, client, throttle): search(topic,n)->papers; by_ids(ids)->(papers,errors); fetch(topic, items, n)->(papers, errors) stores papers via db.upsert_paper, reuses stored, caps items at n. FetchError on arXiv HTTP failure in search (T014 should map). Empty feeds not cached. extract.pdf_title added.
- next: T011+ (tester gate first). Handoff NEXT:tester.

## 2026-10-01 F-001 + T011-T013
- goal: fix F-001; summarizer, critic, ranker agents.
- status: done + ticked + committed (F-001 e52a67a, T011, T012, T013 see git log). 101 tests pass offline, ruff clean.
- findings: F-001 root cause deeper than hostname None: httpx raises ValueError (cookie code) for "http://"; `_download` now catches (HTTPError, InvalidURL, ValueError) -> FetchError. New shared `prompting.py`: `load_prompt(name)`, `paper_block(paper, with_text=True)` -> `<paper id basis>` w/ title, abstract, capped text (fulltext basis only). `summarize(paper, client)`, `critique(paper, client)` (basis overwritten from paper), `rank(paper, summary, topic, client)` (empty topic -> "overall reading priority", no "Topic:"). Agents propagate LLMError/ValidationError unwrapped; T014 pipeline owns retry. paper arg = db paper dict (id,title,abstract,full_text,basis).
- next: T014 pipeline (tester gate first). Handoff NEXT:tester.
