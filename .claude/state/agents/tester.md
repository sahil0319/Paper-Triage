## 2026-10-01 T001-T005
- verify: pytest 38 pass, ruff clean, ticks match 5 T00X commits, only .env.example tracked, no secrets.
- no-mistakes skipped (not init). e2e N/A until T022.
- obs: AnthropicClient only wraps APIError; pipeline (T014) must handle ValidationError retry.
- report docs/qa/T001-T005.md. no failures. Handoff DONE.
## 2026-10-01 T006-T010
- verify: pytest 88 pass, ruff clean, ticks match 5 T00X commits, no .db/.env/secrets tracked.
- offline fetcher smoke ok (5 papers, 4 fulltext 1 abstract, mixed items ok).
- F-001 low: fetch("http://") -> AttributeError (hostname None) not error entry. logged failures.md. loop 1/3.
- report docs/qa/T006-T010.md. Handoff NEXT:builder.
- 2026-10-01 F-001 verified fixed; T011-T013 PASS (101 tests, ruff clean). docs/qa/T011-T013.md
## 2026-10-01 BE wave A (T014 T015 T018 T019 T021api T022)
- pytest 156 pass, ruff clean, e2e 6/6, live smoke :8766 ok (status/triage/papers/chat), grounded-chat rules ok. ticks match git, no db/env tracked.
- no failures. 2 minor notes in docs/qa/BE-wave-A.md. Handoff DONE.
