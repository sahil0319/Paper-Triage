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

## Final pass T001-T024 (2026-10-01)
- goal: whole-project verify both lanes. status: GREEN.
- pytest 156 pass, ruff clean, e2e ok, live smoke :8766 ok (killed), impeccable detect [] , css tokens match DESIGN, a11y static ok.
- repo hygiene ok (.db/.env ignored, 24/24 ticks match commits). fresh clone+uv sync not run (sandbox denied).
- advisory: mock chat only refuses on "out of scope" sentinel; generic OOS q gets canned cite. Not SC-003 violation. Optional [BE].
- details: docs/qa/final.md. next: none -> DONE.
T025 verify: PASS, 167 tests, ruff clean, no failures. DONE
- T026 verified: green; minor [BE] .env.example not updated
## Wave D (T027-T037) 2026-10-01
- pytest 219 pass, e2e 1 pass, ruff clean. Live API smoke 8766: links, paging (15 unique, has_more false), offset 422, chat paper_ids 422/scoped/refusals all PASS. Own Playwright run: indicator ok (aria-live, reduced motion, no external reqs, contrast ok).
- advisories only: A1 detect false positives, A2 empty-state under working card [FE], A3 mock cites first keyword match [BE info]. No failures logged.
- checklist specs/001-paper-triage/checklists/v2-requirements.md (28 items). report docs/qa/wave-d.md. Servers killed. Next: DONE.
## v2 final pass (wave E + T042) 2026-10-01 HEAD 0abd7b4
- pytest 226, e2e 8 x5 stable, ruff clean. detect: 3 findings (2 known FP + side-tab F-003).
- own Playwright (8766 uvicorn, 8768 harness): load-more error/retry, 50 cap, reload+no-new, scope line, keyboard focus, reduced motion, 320/768/1440 all PASS. no blocker.
- logged low: F-002 [BE] stale last-run topic, F-003 [FE] side-tab, F-004 [FE] e2e gaps, F-005 [BE] harness busy port.
- README ok; `uv run uvicorn` fails locally only (stale .venv shebang -> agentic-job-hunt), clean env ok.
- checklist: 11 ticked. report docs/qa/final.md (v2 section). servers killed. Next: DONE.
## v2 re-verify F-002..F-005 2026-10-01 HEAD 568d480
- pytest 230, e2e 9 x3, ruff clean, detect 2 (known FP). F-002 tests fail on pre-fix copy (scratch), repro ok. F-005 clear busy-port error. F-003 tint + static verb ok. F-004 assertions real (residual note). All closed in failures.md, final.md updated. servers killed. DONE.
## F-006 verify 2026-10-03 HEAD c205d59
- pytest 233, e2e 12 x3 stable, static 9, ruff clean, detect 2 (known FP). Own Playwright (8766, normal+reduced motion): load-more reset, error keeps chat, new-search reset, 50 cap ids, in-flight drop, focus not stolen all PASS.
- logged low: F-007 [FE] new-search reset not in #status; F-008 [FE] Ask disabled while stale reply in flight. Not run: pre-fix mutation of new specs (sandbox blocked).
- report docs/qa/F-006.md. servers killed. Next: DONE (F-006 closed; F-007/F-008 optional FE).
## F-007/F-008 re-verify 2026-10-03 HEAD c911fa1
- pytest 236, e2e 15 x3, static 9, ruff clean, detect 2 (known FP). Playwright 8766 normal+reduced: reset announced once (observer), Ask free during stale reply, stale-vs-new-ask no cross-talk, failed-row note ok. F-007/F-008 RESOLVED. servers killed. DONE.

## v3 BE Waves F+G (HEAD 6d9f720)
goal: verify T043-T051, T057-T059 BE only. status: PASS. pytest --ignore=tests/frontend 344 pass, ruff clean, live probe on 8766 88/88 (library, pdf, retry, range, dirs, annotations, paper-chat, sweep, unsave). No failures, failures.md untouched. Notes: POST /api/library topic must be response `topic` (normalized), not raw query; Range unit other than bytes gives 400. Results: docs/qa/v3-wave-FG-be.md. Not run: frontend tests, e2e, gate. next: tester full pass after FE wave.

## v3 FE Wave F (a2bf9e3, T052-T056)
goal: verify FE lane in worktree. status: PASS + F-009 medium [FE] (Retry on failed PDF stuck on Downloading: viewer.js mutates cached item, app.js loadLibrary sig unchanged), F-010 low (selection blue literal vs cream), F-011 low (find result focus). pytest 406, ruff clean, e2e 47 x3, static 16, detect 2 FP, Playwright ~110 checks. Details docs/qa/v3-wave-F-fe.md. next: frontend-builder fix F-009 before final pass.

## 2026-10-03 v3 Wave G FE verify (HEAD 0cd0726)
Goal: verify T060-T063 + fixes. Status: PASS. Full pytest 470/471 (F-012 flaky test), ruff clean, e2e x3 112 each, static guard 16, impeccable 3 (2 known + row-collapse height, accepted: reduced motion instant). F-009, F-011 RESOLVED. New low [FE]: F-012 (test race on optimistic .hl swap), F-013 (rgba literals). Report: docs/qa/v3-wave-G-fe.md. Next: Wave H T064 FE.

## v3 final pass (paused by user)
Done: pytest run1 497 pass, run2 497 pass (87s each); ruff clean; e2e run1 132 pass (runs 2-3 not confirmed, command exited 144 on pause/timeout); tasks.md T001-T065 all ticked + matching commits; .gitignore covers paper_triage_data/, *.db, .env; no db/data tracked (only .env.example); pdfjs LICENSE tracked; impeccable detect 4 findings (layout-transition app.css:661, 2 cramped-padding, flat-type-hierarchy) - not yet compared against baseline.
Remaining: e2e x2 more, static guard + F-012 solo rerun, README spot-check, real-API smoke on 8766, load-more chat reset, F-012/F-013/F-014 closure in failures.md, v3 section in final.md. No files edited. Gate skipped (no bare repo).

## v4 T068 verify (2026-10-04, HEAD 94ed09e, worktree)
- Goal: verify token layer commit. Status: one [FE] flake. pytest 544 pass (E2E_PORT=8766), ruff clean, test_design_tokens solo x3 12 pass, assets served 200, detect 7+2 (all accepted).
- F-020 [FE] medium: sheet-up slowed 200->240ms, test_audit_sheet_header_is_one_row_on_canvas fails ~1/3 (parent 12/12). Wait for animation end in test.
- Deviations (notifications, working card surface-1, tag pressed inverse, rail bar, ink-disabled rgb(140,140,140)) all match DESIGN.md.
- Report docs/qa/v4-T068.md. Servers killed. Next: frontend-builder fixes F-020 test, then T069.
