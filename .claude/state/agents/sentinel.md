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

