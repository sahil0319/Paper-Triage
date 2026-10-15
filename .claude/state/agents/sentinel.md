## Checkpoint: Wave D complete, Wave E in progress (2026-10-01)

**Task**: v2 wave D final checkpoint after tester GREEN
**Status**: DONE
**Findings**: Wave D (T027-T042) complete and tested. 219 pytest pass, e2e 1, ruff clean. Wave E (FE T038-T041) queued for next spawn.

### Actions taken
- Updated progress.json: added T027-T042, phase="v2-wave-E-in-progress", DONE=false, tasks T038-T041→in-progress
- Wrote checkpoint.md: phase, active tasks, done list, wave D summary, wave E queue, decisions, open items, exact next command
- Appended sentinel.md (this file)

### Verified
- Wave D tester report green: docs/qa/wave-d.md (219 tests, e2e 1, ruff clean, no blocking failures)
- Git log confirms T027-T042 all have matching commits (63fc73e last, 0311833 T042 latest)
- Tasks.md wave structure verified: D done, E queued (dependencies met)
- Backend-builder.md API facts up-to-date (abs_url/pdf_url, offset paging, chat paper_ids)
- Frontend-builder.md T037 complete, T038-T041 ready

### Open (non-blocking)
- A1: impeccable detect false positives (optional CSS fix)
- A3: mock chat first-keyword-match behavior (expected per contract)
- analysis.md: planner write deferred, retry when planner active
- checklist: v2-requirements.md 28 items unchecked (for review)
- no-mistakes gate: deferred (needs .local/bare.git setup)

### Next
When FE wave E reports → spawn tester (T038-T041 full suite) → sentinel → final pass.

---

## Final Checkpoint: v2 Complete (2026-10-01)

**Task**: v2 project completion checkpoint after wave E + tester final pass
**Status**: DONE
**Findings**: All 42 tasks done. Tester GREEN: 230 pytest, 9 e2e (x3 stable), ruff clean.

### Wave E completion
- T038 ad4980c: paper links (arXiv page, PDF, a11y labels)
- T039 98066a2: load 5 more (offset paging, dedupe, focus, error retry)
- T040 51587b9: chat scope wiring (paper_ids from rows, disabled when empty)
- T041 0abd7b4: browser e2e specs (indicator, links, load-more, chat scope/refusal)

### Fixes landed & verified
- F-002 6cd65e0: re-run refreshes last-run marker
- F-003 a04adfc: reduced-motion new-row cue as background tint
- F-004 568d480: direct-PDF row, self-contained cites-only, refusal positive control
- F-005 bbbe244: e2e harness fails fast when port in use

### Actions taken
- Updated progress.json: T038-T041→done, phase="done (v2)", DONE=true
- Rewrote checkpoint.md: final status, all waves, verification, open items for user
- Appended sentinel.md (this file)

### Verified
- Tasks: T001-T042 all ticked in tasks.md, all have matching `T00X` commits
- No task mismatches (git log matches ticks)
- Tester final pass GREEN: docs/qa/final.md
- Repo clean: .db/.env ignored, no secrets, uv.lock tracked, fresh clone feasible

### Open for user
1. analysis.md: planner write blocked; user choose write/ask-router/skip
2. .venv shebangs: stale; fix: `rm -rf .venv && uv sync`
3. no-mistakes gate: deferred (needs .local/bare.git)
4. load-more e2e gaps: error/50-cap/empty-set not covered (manually verified)
5. checklist: 11/28 ticked; rest spec gaps/decisions
6. advisories: A1 impeccable false positives, A3 first-word-match citation (per contract)

### Next
None. Await user.


## Checkpoint: v3 Amendment Planning (2026-10-03)

**Task**: v3 amendment phase checkpoint (research + design + spec phase 1 complete, planner phase 2 queued)
**Status**: DONE
**Findings**: v2 complete (all 42 tasks, fixes F-006/F-007/F-008 shipped GREEN). v3 research/design/spec amendment phase 1 done. Planner ready for phase 2 (constitution 2.0.0, plan, data-model, contracts, tasks, analyze).

### Actions taken
- Collected v2 tail state: F-006 c205d59, F-007/F-008 c911fa1 (236 pytest, 15 e2e x3, ruff clean)
- Collected v3 state: research docs/research/v3-library-preview.md, design docs/design/v3-library-brief.md (Rev 2), spec amendment 753d0a5
- Updated checkpoint.md: phase="v3 planning", summary of v2 fixes, v3 research/design/spec, user decisions, planner phase 2 next
- Updated progress.json: phase="v3 planning", DONE=false, T001-T042 all done
- Appended sentinel.md (this file)

### Verified
- v2 tester final: 236 pytest, 15 e2e x3, ruff clean (docs/qa/F-006.md, failures.md)
- v3 research: docs/research/v3-library-preview.md complete (pdfjs, pypdf, Range, throttle facts)
- v3 design: docs/design/v3-library-brief.md (Rev 2) complete (L1-L24 FE, B1-B8 BE)
- v3 spec amendment: 753d0a5 (US4-US9, FR-008a, FR-015..029, SC-009..016, 7 entities, 9 edge cases)

### Next
When planner phase 2 reports → spawn backend-builder + frontend-builder in parallel on v3 wave 1 per tasks.md Lanes → tester → sentinel.

## Checkpoint: v3 Build in Progress (2026-10-03)

**Task**: Update checkpoint after BE lane complete and FE Wave F running
**Status**: DONE
**Findings**: Backend lane v3 complete (T043-T051, T057-T059, T065), verified GREEN. FE Wave F in progress (T052-T055 done, T056 pending). BE: pytest 344, live 88/88, ruff clean.

### Actions taken
- Updated checkpoint.md: phase="v3 build", BE complete, FE Wave F progress, Wave G/H pending, exact next step
- Updated progress.json: T043-T065 statuses (done/pending), phase="v3 build", DONE=false
- Appended sentinel.md (this file)

### Verified
- BE lane: 65381fc (T065) matches commit list T043-T051, T057-T059
- FE Wave F: be3cbf1 (T052), 9b6ea8a (T053), c72e508 (T054), eb16174 (T055) done; T056 pending
- QA verified BE: docs/qa/v3-wave-FG-be.md (pytest 344, live probe 88/88)
- Tasks.md ticks: T043-T055 ✓, T056 ☐, T060-T064 ☐, T065 ✓

### Items persisted
- analysis.md committed ba039be (speckit-analyze output from planner)
- PRODUCT.md Library section committed 374ee23 (user request)
- Highlight colors corrected yellow/mint/peach (commit 0bd9170)

### Pending
1. T056 (find in paper) and FE Wave F tester green
2. 7 .claude/agents/*.md uncommitted (report-format block added by router); defer restart to post-Wave-F
3. T060-T063 (Wave G real API), T064 (Wave H e2e)

### Next
When FE Wave F done → tester FE Wave F (verify T052-T055, smoke T056) → FE Wave G builders (T060-T063) → tester → restart Claude Code → FE T064 → final tester pass.

## Checkpoint: v3 Final Verification (Paused) (2026-10-03)

**Task**: v3 final verification checkpoint (tester paused by user due to context ~70%)
**Status**: DONE
**Findings**: All T001-T065 complete (T064 merged 098950a). Tester final pass 50% done (pytest x2 497 pass, ruff clean, e2e run 1 132 pass; e2e runs 2-3/static guard/README/smoke remaining). Designer re-check 90% done (13 must-fix verified PASS; 1 regression found + fix identified). FE focus-order fix pending.

### Actions taken
- Updated checkpoint.md: full summary, paused state, exact next commands for designer/FE/tester
- Updated progress.json: T064→done, all 65 tasks done, phase="v3 final verification (paused)", context_pct=70, DONE=false
- Appended sentinel.md (this file)

### Verified
- All v3 tasks T001-T065 ticked in tasks.md, all have matching commits (latest: 098950a T064, f6bb184 F-012, 22781d9 F-013, 6e1b9a1 audit, d6a6dfc F-014)
- Backend: 344 pytest, 88/88 live API, ruff clean (docs/qa/v3-wave-FG-be.md)
- Frontend: 497 pytest, ruff clean, e2e 112 pass (waves F+G verified, T064 done)
- Tester completed: pytest x2, ruff, e2e run 1, hygiene (no secrets, pdfjs LICENSE, .gitignore correct), impeccable 4 findings
- Designer re-check: all 13 must-fix visual PASS, 1 regression identified (#pv-sheet-open focus order, fix: move DOM after #pv-controls)
- No task/commit mismatches

### Paused state
- Router context ~70% (checkpoint triggered)
- Tester final pass: e2e runs 2-3 incomplete, static guard + F-012 rerun pending, README/smoke/failures.md/final.md pending
- Designer: Re-check section not written (has findings), toolbar decision pending (noted: accept per prior approval)
- FE: #pv-sheet-open focus-order fix not applied

### Next (on resume)
1. designer: write Re-check section in docs/design/v3-audit.md, commit (17/20 score)
2. frontend-builder: fix #pv-sheet-open DOM, verify F-012 solo rerun, commit [FE]
3. tester: e2e runs 2-3, static guard, README, real-API smoke, failures.md + final.md v3 section, commit docs/qa/ (all expected GREEN)
4. sentinel: mark DONE=true (all tasks + tester pass green)

**Blocker**: None. Parallel work ready to resume.
## Checkpoint: v4 Build Started (2026-10-03)

**Task**: Update checkpoint after v3 complete and v4 wave R1 complete
**Status**: DONE
**Findings**: v3 complete (T001-T065 all done, tester GREEN). v4 wave R1 complete (T066-T067, T075 done, F-016/F-017/F-019 fixes verified). FE lane T068-T074 queued (strict sequence). Phase: v4 build.

### Actions taken
- Verified tasks.md: T001-T067 and T075 ticked; T068-T074, T076 unticked
- Verified git commits: F-016 325f7f3, F-017 57a8e71, F-019 6a1912c, T066 10b7c4d, T067 3b98ff2, T075 40b7ac1 all present
- Updated checkpoint.md: phase="v4 build", R1 summary, T068-T076 queue, next: FE T068 strict sequence
- Updated progress.json: T066-T067→done, T075→done, T068-T074→in-progress/waiting, T076→waiting, phase="v4 build", DONE=false
- Appended sentinel.md (this file)

### Verified
- v3 final: all 65 tasks ticked, all commits landed, pytest 532 x2, ruff clean, docs/qa/final.md PASS
- v4 wave R1: T066 MIME (10b7c4d), T067 fonts 8 woff2 (3b98ff2), T075 README (40b7ac1) all done
- Fixes verified: F-016 highlight selection, F-017 previous results opacity, F-019 preview Ask tab
- Tester gate: docs/qa/v4-fixes.md GREEN (pytest 532 x2, ruff clean)
- No task/commit mismatches

### FE sequence ready
- T068: token layer + global type styles (in progress)
- T069-T074: per-component CSS restyle (waiting)
- T076: design e2e sweep + screenshots (waiting)

### Next
Frontend-builder continues at T068. Loop until T074, then T076 design e2e, then tester final pass.


## Checkpoint: v4 Build (T074-T076, Tester Verification In-Flight) (2026-10-04)

**Task**: Update checkpoint after T068-T073 complete and tester verifying
**Status**: DONE
**Findings**: T068-T073 all ticked and committed (94ed09e..59debeb). T075 done. Tester verified T068 and T069+T070+F-020 (F-020 test fix). Tester currently verifying T071+T072 (snapshot method). T073 not yet tested. T074 and T076 remain. No task/commit mismatches.

### Actions taken
- Verified tasks.md: T068-T073 and T075 ticked; T074 and T076 unticked
- Verified git commits: T068-T073 present (94ed09e, f6275a5, fb34554, 3f6cc23, d08cf70, 59debeb) with fix(F-020) c41d740
- Updated progress.json: T068-T073→done, T074→waiting, T075→done, T076→waiting, phase="v4 build", DONE=false
- Wrote checkpoint.md: phase, task status, tester in-flight state, exact next command
- Appended sentinel.md (this file)

### Verified
- v4 wave R2 CSS complete: T068 token layer, T069 nav, T070 rows, T071 library, T072 preview toolbar, T073 preview panel all committed
- Tester progress: T068 PASS (12 x3), T069+T070+F-020 PASS (15 x3), T071+T072 VERIFYING (snapshot method on port 8766), T073 NOT YET TESTED
- No task/commit mismatches: 67 done tasks T001-T067 + T075, 6 done CSS tasks T068-T073, 2 waiting T074-T076

### Tester state
- Verifying: T071+T072 snapshot method
- Next queue: T073, then tester wait on T074/T076 FE completion, then full final pass

### FE lane next
- T074: states, motion, forced-colours sweep (strict sequence)
- T076: design e2e sweep + screenshots (final before tester)

### Open items
- T071+T072 verification result (pending)
- T073 verification (queued)
- Worktree cleanup: stale .claude/worktrees/agent-a4628e381b8ec6bcc (user to remove)
- Uncommitted: docs/qa/* from tester (leave as-is; user-owned decision), .claude/agents/* edits (cache per-session)

### Next
1. Tester finishes T071+T072 verify (snapshot method)
2. Tester queues T073 verify
3. Frontend-builder starts T074 when T073 complete
4. After T074 green: T076 design e2e sweep
5. After T076 green: tester full final pass (pytest + ruff + e2e)
6. If all green: set DONE=true

## Final Checkpoint: v4 Complete (2026-10-04)

**Task**: Final checkpoint for v4 build after tester v4 final pass GREEN
**Status**: DONE
**Findings**: All T001-T076 ticked and committed. Tester v4 final pass GREEN: pytest 646 x2, e2e 239 x2, design e2e 93, ruff clean (docs/qa/final.md v4 sections). Designer v4 audit 17/20 items, all blockers fixed and verified. F-020..F-024 resolved. Since checkpoint 319bcc7: T074 f3a2946, fix(F-021) 8d1fe79, fix(F-022) ae286b8, T076 651ea2f, fix(F-023) 14af76e, v4-audit fixes fa4c533 7d6885f 3f21547 bf43594 c32275c 04b299b.

### Actions taken
- Updated checkpoint.md: phase="done (v4)", DONE=true, final status, test results, 7 open items, verification notes
- Updated progress.json: phase="done (v4)", DONE=true, T001-T076 all done
- Appended sentinel.md (this file) with final state summary

### Verified
- Git log confirms all commits landed (latest 04b299b v4-audit alignment)
- All T001-T076 ticked per system message summary
- Tester v4 final pass: pytest 646 x2, e2e 239 x2, design e2e 93, ruff clean
- Designer audit: 17/20 items, blockers fixed + verified (docs/design/v4-audit.md)
- Fixes verified: F-020 sheet timing, F-021 external-ref guard, F-022 toolbar actions, F-023 highlight radius, F-024 $S dir removed
- No task/commit mismatches

### Open items for user
1. paper_triage.db mutated by designer audit (4 papers re-saved, 1 mock triage, 2401.00002 moved)
2. specs/001-paper-triage/spec.md planner amendment (not-saved h1 copy) uncommitted
3. Stale worktree .claude/worktrees/agent-a4628e381b8ec6bcc + branch
4. Uncommitted docs/qa/*, docs/design/v4-audit.md, .claude/agents/* edits
5. Cosmetic: Preview load-error h1 title attribute not set (stale value can persist)
6. Proposed next feature (not started): page transitions (View Transitions crossfade)
7. No-mistakes gate deferred (no bare repo in .local/)

### Next
None. Await user decision on open items. If user approves page-transitions feature, spawn designer for DESIGN.md §6 row update.


## README screenshots checkpoint (2026-10-15, commit d355dd9)
- Recorded 071d354 restructure, c28dbd5 caption fix, 17 live PNGs in docs/screenshots/ (openai gpt-5-mini, isolated DB .local/screens/, user db untouched).
- Tester GREEN: 646 pytest, ruff clean, 17/17 images. Report docs/qa/readme-screenshots.md (uncommitted).
- Open items 1-7 kept. DONE true, context_pct preserved. Next: None; await user.
