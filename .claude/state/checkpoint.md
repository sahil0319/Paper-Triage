# Checkpoint: v3 Build in Progress

**Phase**: v3 build (BE complete and GREEN verified; FE Wave F in progress)

**Status**: Backend lane v3 complete T043-T051, T057-T059, T065. FE lane Wave F running T052-T055 done, T056 pending. QA verified BE: docs/qa/v3-wave-FG-be.md (pytest 344, live 88/88).

## Summary

### v2 (T001-T042) 
Complete. 236 pytest, 15 e2e stable, ruff clean.

### v3 Build

**Backend lane** (T043-T065): COMPLETE and GREEN
- T043: Tag normalizer
- T044-T051: Library, directories, files, annotations, PDF store, API wiring
- T057-T059: Page extraction, paper chat agent, harness + v3 smoke
- T065: README + SETUP_LOG v3

Tests: pytest 344 pass, live API probe 88/88 endpoints, ruff clean.
QA verified: docs/qa/v3-wave-FG-be.md (tester).

**Frontend lane** (T052-T056+): WAVE F in progress
- T052: Vendor pdfjs-dist 6.3.289 + static guard [DONE be3cbf1]
- T053: Shell, nav, hash routes [DONE 9b6ea8a]
- T054: Save toggle on result rows [DONE c72e508]
- T055: Viewer shell (pdf.js canvas, text layer) [DONE eb16174]
- T056: Find in paper [PENDING]

Next after Wave F: Wave G (T060-T063) real API; Wave H (T064) e2e browser.

## Persisted items

- analysis.md committed ba039be (speckit-analyze output)
- PRODUCT.md Library section committed 374ee23 (user request)
- Highlight colors corrected to yellow/mint/peach (was yellow/green/blue, rev 0bd9170)

## Open items

1. **T056**: Find in paper (pause until FE tester done)
2. **Wave G** (T060-T063): Library view, directories UI, highlights/notes, paper chat sheet
3. **Wave H** (T064): Browser e2e on v3 harness
4. **Pending restart**: 7 .claude/agents/*.md have report-format block (uncommitted, alongside user edits; defer to post-Wave-F tester)

## Files touched this session

- `.claude/state/checkpoint.md` (this file)
- `.claude/state/progress.json` (BE tasks done, FE T052-T055 done)
- `.claude/state/agents/sentinel.md` (appended)

## Next

**Now**: FE Wave F done pending → tester FE Wave F (T052-T055 verify; T056 smoke) → FE Wave G (spawn builders) → tester → restart → FE T064 → final test.

**After**: Verify all tasks ticked, commit checkpoint, user test.
