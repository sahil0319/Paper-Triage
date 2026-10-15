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

## v3 final pass COMPLETE (HEAD 42fbfc3)
pytest x2 503 pass; ruff clean; e2e 138 pass x14/15 (1 unnamed flake -> F-015 accepted); static guard 16; F-012 solo 3/3; impeccable 4 hits (all known/accepted); smoke + 390px tab order + F-006..F-008 ok; README ok; hygiene ok. Gate skipped (deferred). final.md v3 section + failures.md updated. Servers killed.

## v4 fixes F-016..F-019 + T066 (2026-10-03, HEAD 6a1912c)
- Goal: verify 7b43af1..6a1912c. Status: green. pytest 532 x2, ruff check clean, e2e solo x3 for F-016/F-017/F-019 all pass, live 8766 smoke ok (fonts font/woff2), servers killed.
- F-018 build_query manual repro ok. Report docs/qa/v4-fixes.md. All four marked RESOLVED in failures.md.
- Detector: 8 design-system advisories vs new DESIGN.md, expected until T068+.
- Next: tester re-run after T067..T076 land.

## v4 T068 verify (2026-10-04, HEAD 94ed09e, worktree)
- Goal: verify token layer commit. Status: one [FE] flake. pytest 544 pass (E2E_PORT=8766), ruff clean, test_design_tokens solo x3 12 pass, assets served 200, detect 7+2 (all accepted).
- F-020 [FE] medium: sheet-up slowed 200->240ms, test_audit_sheet_header_is_one_row_on_canvas fails ~1/3 (parent 12/12). Wait for animation end in test.
- Deviations (notifications, working card surface-1, tag pressed inverse, rail bar, ink-disabled rgb(140,140,140)) all match DESIGN.md.
- Report docs/qa/v4-T068.md. Servers killed. Next: frontend-builder fixes F-020 test, then T069.

## v4 T069 + T070 + F-020 verify (2026-10-04, snapshot c41d740)
- Status: PASS. pytest 559, ruff clean, test_e2e_design x3 15 pass, F-020 test solo 12/12 (tolerance unchanged, getAnimations wait added; reflow hunks format-only), detect identical to T068 baseline (7 + 2 advisories).
- F-020 RESOLVED in failures.md. Report docs/qa/v4-T069-T070.md. No servers left. No commit (main tree).
- Next: T071 verify when FE reports.

## v4 T071 + T072 verify (2026-10-04, snapshots 3f6cc23 and d08cf70)
- Status: UI PASS, suite RED on F-021. d08cf70: pytest 571 pass + 1 fail, ruff clean, test_e2e_design x3 28 pass, test_e2e_library x3 129 pass, F-016/tab-order/mobile-toolbar subset x3 12 pass, detect +1 spec-mandated side-tab (hl-item__quote).
- F-021 [BE] medium: tests/test_api.py::test_static_css_served greps `http://`; T071 SVG data-URI xmlns trips it. Fix the guard to fetchable URLs (url(http..), @import).
- F-022 [FE] low: #pv-export 34px and #pv-external 28px vs "every control 40px"; test covers only #pv-controls.
- Mobile toolbar 243px (<=260), spacing uses --space-xxs/xs tokens, #pv-controls all 40px. Collapse reaches 0px; reduced-motion path unchanged.
- Reports docs/qa/v4-T071.md. No servers. No commit.
- Next: backend-builder (F-021), frontend-builder (F-022); then T073 verify.

## v4 T073 + F-021 re-verify (2026-10-04, snapshots 59debeb, 8d1fe79)
- T073 PASS: pytest 575 pass + known F-021, ruff clean, test_e2e_design 25/26 runs green, F-020 test 5/5, F-019 subset 7 pass. Selected Ask tab, no paper-chat request, sheet opens on Ask, backdrop = overlay token, notext/nopdf info rules, tab 40px verified.
- F-021 RESOLVED: test_api 37 pass; adversarial probe caught every external ref, data: xmlns allowed.
- F-023 [FE] low (new): mint highlight design test flaked 1/26 (detached .hl after optimistic swap, F-012 family).
- Port 8766 was held by BE pytest; tester used E2E_PORT=8786. Report docs/qa/v4-T073.md. No commit.
- Next: T074 verify when FE reports.

## v4 T074 + F-022 verify (2026-10-04, snapshot ae286b8)
- PASS. pytest 595 pass (fully green, F-021 gone), ruff clean, design e2e + tokens x3 62 pass, toolbar/F-016 subset x3 14 pass.
- F-022 RESOLVED: export/external 40px at 1440/820/390, mobile toolbar 249px, tab order same. Forced-colors probe: hl outline 2px, layer forced-color-adjust none. Reduced-motion covers every keyframe.
- detect: +1 spec-mandated forced-colors rail bar. F-023 still open (FE, after T076).
- Report docs/qa/v4-T074.md. Port 8766 free; no servers. No commit.
- Next: wait for T076 + F-023, then final full pass.

## v4 final pass (2026-10-04, HEAD 14af76e)
- PASS. pytest 638 x2, ruff clean, e2e 231 x3, design e2e + V4_SHOTS_DIR 85 pass (9 PNGs viewed ok), static/font/token 41 pass, F-023 solo 12/12 -> RESOLVED, smoke 12/12 (triage, save, pdf, paper-chat, results chat, woff2), tasks 76/76 ticked with commits, README/SETUP_LOG match, no tracked db/env/tarball.
- detect: 10 + 1 advisory, all known/spec-mandated. Gate skipped (no bare repo).
- New low F-024: stray `$S/` dir in repo root (untracked, 164 KB, t72.png). Delete before commit.
- final.md v4 section written. No commit. Ports free.

## v4 audit fixes re-verify (2026-10-04, HEAD 04b299b)
- PASS. pytest 646 x2, ruff clean, e2e 239 x2, design e2e 93, detect = final baseline, mobile toolbar 249px, focus order unchanged.
- Items 1-6 all fixed by probe: rail count 5.92/6.38:1; forced-colors underline only on current nav/tab; back ghost; primary Create/Save note; 12px confirm + save gaps; not-saved h1/title `Not in your Library` centred 640px, load-error h1 `Preview`.
- No new failures. Cosmetic note only: load-error branch does not reset the h1 title attribute. F-024 (`$S/` dir) still open.
- Appended to final.md and failures.md. No commit. Ports free.

## README screenshots (live, one-off)
- Goal: capture feature screenshots, live mode (openai/gpt-5-mini per /api/status), port 8766, isolated DB .local/screens/.
- Status: 17 PNGs in docs/screenshots/ (01..13a), all read back OK. Queries: "retrieval augmented generation evaluation" (main), "dense passage retrieval benchmark" (2nd tag set, mobile shot). 6 papers saved, PDFs ready. Server killed, port free. No commit.
- Skipped: PDF pending/failed state (live downloads all succeeded), unsave confirm, zoom variants.

## README screenshots verify (071d354)
- 17/17 images referenced and present; captions match except 2 cosmetic [BE] nits (README.md:13 "one-line reason", README.md:39 critique not visible in 03b). Quick start matches config/status; no facts dropped. ruff clean; 646 passed. Details: docs/qa/readme-screenshots.md. No commit.
