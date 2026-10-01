
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
