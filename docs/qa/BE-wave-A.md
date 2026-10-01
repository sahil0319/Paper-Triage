# QA BE wave A: T014 T015 T018 T019 T021(api) T022

Date 2026-10-01. Lane: backend only (static/** ignored). No-mistakes gate skipped per orchestrator.

## Gates
- `uv run pytest -q` (MOCK_LLM=1): 156 passed, 2.1 s.
- `uv run ruff check .`: clean.
- tests/test_e2e_mock.py: 6/6 pass (offline, socket.connect patched, 5-paper triage < 5 s).
- Ticks vs git: T014 c2860d8, T015 acf51b1, T018 7912d61, T019 63129d5, T021 api ca2e161 (+ ui 0c025df ticked it, as planned), T022 c525ee3. All match.
- Tracked files: no .db, no .env (only .env.example), no `sk-ant-` strings. `.gitignore` covers *.db/.env.

## Acceptance
| task | result | evidence |
|---|---|---|
| T014 pipeline | PASS | single retry (LLMError/ValidationError), per-paper `failed` with step reason + partials, reuse of ok (paper_id, topic), n capped to 20, sort rank desc / failed last |
| T015 app | PASS | status/triage/papers/static mount; startup init_schema; 422 -> `{"detail": str}` plain; max_results 1..20 |
| T018 chat | PASS | empty store -> refusal, spy asserts zero LLM calls; regex validates ids vs store, unknown -> dropped_citations; sentinel or 0 valid cites -> refused; sentinel stripped from refusal text |
| T019 chat API | PASS | 422 on blank question (not persisted); 502 `model call failed: ..` not persisted; answered and refused turns persisted |
| T021 api | PASS | fresh app on same db: status paper_count=5, /api/papers equal to first triage, re-triage with no-network transport returns same results |
| T022 e2e | PASS | all listed scenarios present in test file and green |

## Live smoke (MOCK_LLM=1, uvicorn :8766, temp db, server killed after)
- GET /api/status -> `{"mock":true,"model":"claude-opus-5-5","paper_count":0}`; after triage count=5.
- POST /api/chat on empty store -> refused:true, canned sentence, citations [].
- POST /api/chat `"  "` -> 422; POST /api/triage max_results=21 -> 422 `max_results must be 1..20`; blank query -> 422 `empty query`.
- POST /api/triage "diffusion distillation" -> 200, 5 results ranks 7,6,3,2,1 sorted desc, 1 basis=abstract, all ok, errors [].
- GET /api/papers -> same 5, same order, topic matches.
- POST /api/chat in-scope -> cites [2401.00005] (stored), refused:false, dropped [].
- POST /api/chat out-of-scope -> refused:true, citations [].
- GET / -> 200.
- Port 8766 free after kill; no stray db in repo.

## Notes (non-blocking, not failures)
- 422 detail for chat reads `question: Value error, question must not be empty`; plain string, contract OK, wording slightly noisy.
- Pipeline retries LLMError as well as ValidationError (superset of the task text); harmless, doubles calls on persistent API errors.
- Live (non-mock) path untested here by design (offline).

## Failures
None. Nothing appended to failures.md.
