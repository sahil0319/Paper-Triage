# Checkpoint: v3 Build Complete + Final Test Phase

**Phase**: v3 build (fix + T064)

**Status**: v3 FEATURE COMPLETE. T001-T063 verified. T064 final e2e pending. FE+BE running parallel (F-012/F-013 audit fixes, F-014 BE refusal) before final test wave.

## Summary

### v2 (T001-T042)
Complete. 236 pytest, 15 e2e stable, ruff clean.

### v3 Build

**Backend lane** (T043-T065): COMPLETE and GREEN
- T043-T051: Tag normalizer, library, directories, files, annotations, PDF store, API wiring
- T057-T059: Page extraction, paper chat agent, harness + v3 smoke
- T065: README + SETUP_LOG v3
- pytest 344 pass, live API probe 88/88 endpoints, ruff clean
- Verified: docs/qa/v3-wave-FG-be.md

**Frontend lane** (T052-T063): ALL WAVES DONE
- **Wave F** (T052-T055): Vendor pdfjs, shell nav, save toggle, viewer [VERIFIED]
  - F-009, F-011 fixed b829885
  - F-010: accepted deviation (selection colour)
- **Wave G** (T060-T063): Library, directories, highlights/notes, paper chat sheet [VERIFIED]
  - T060 8be3853: Library view tags/title filters, polling, retry
  - T061 700199b: Directories rail, CRUD, move/remove
  - T062 0b611ff: Highlights, notes, panel list, undo, page notes, Markdown export
  - T063 0cd0726: Ask paper panel, cite chips jump, sheet below 1024px
  - pytest 470/1 flaky, e2e 112 x3, ruff clean
  - Verified: docs/qa/v3-wave-G-fe.md
- T056: Find in paper [DONE a2bf9e3]

### Open (Low Priority, Pre-Final-Test)
- **F-012** [FE]: Flaky highlight test (test-side fix)
- **F-013** [FE]: rgba literals  
- **F-014** [BE]: Mock paper-chat starters refused + refusal wording
- **Designer audit** docs/design/v3-audit.md: 14/20, 13 must-fix [FE]

FE + BE running parallel on these before final test.

## Files Touched
- `.claude/state/checkpoint.md` (this)
- `.claude/state/progress.json` (T060-T063 marked done)
- `.claude/state/agents/sentinel.md` (appended)

## Exact Next Command
When FE + BE report → tester: full suite (pytest, e2e x3, static guard, impeccable, no-mistakes gate if feasible, audit re-check) → sentinel → mark DONE.

**Task Summary**: 22/23 v3 done (T001-T063). Only T064 (e2e harness) remains.

**DONE flag**: false (awaiting final test pass + T064).
