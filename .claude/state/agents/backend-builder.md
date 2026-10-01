
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
