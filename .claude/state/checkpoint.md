# Checkpoint: v4 Build (T074-T076, Tester Final Pass)

**Phase**: v4 build (Carbon redesign, FR-030). Wave R2 CSS implementation (T068-T073 done).

**Status**: T068-T073 committed and ticked (token layer, nav, rows, library, preview, panel). T075 README done. Tester verified T068 and T069+T070+F-020; currently verifying T071+T072; T073 not yet tested. T074 (states, motion, forced-colours) and T076 (design e2e sweep, screenshots) remain.

## Summary

### Completed
- **T068**: Token layer, global type, focus, hover, motion (app.css + test_design_tokens.py)
- **T069**: Shell, nav, buttons, query (brief items 5-8)
- **T070**: Result rows and results chat (brief items 9-11, 15-16)
- **T071**: Library view (brief items 18-22)
- **T072**: Preview toolbar, find, highlights, popover (brief items 23-27)
- **T073**: Preview side panel, notes, Ask this paper, bottom sheet (brief items 28-31)
- **T075**: README + SETUP_LOG v4 design note
- **fix(F-020)**: Sheet animation timing (test wait for animation end)

### In Progress
- **Tester**: Verifying T071+T072 snapshot method (port 8766); T073 not yet tested
- **Next FE**: T074 (states, motion, forced-colours sweep)

### Not Started
- **T074**: States, motion, forced-colours sweep (test_design_tokens.py + test_e2e_design.py additions + app.css)
- **T076**: Design e2e sweep + screenshots (SC-017..SC-022)

## Test Status
- T068: PASS (test_design_tokens solo x3, e2e x3, no hex/rgb outside :root)
- T069+T070+F-020: PASS (test_e2e_design x3, 15 assertions)
- T071+T072: VERIFYING (snapshot method on port 8766)
- T073: NOT YET TESTED
- T074: NOT STARTED
- T076: NOT STARTED

## Files Touched (Last Wave)
- `pt/static/app.css` (T068-T074: token layer, component styles, states, motion)
- `tests/frontend/test_design_tokens.py` (T068, T074: token validation)
- `tests/frontend/test_e2e_design.py` (T069-T074: design assertions, motion, colours)
- `README.md`, `SETUP_LOG.md` (T075: v4 design note)

## Known Open Items
1. **T071+T072 verification**: Tester currently running snapshot method; results pending
2. **T073 verification**: Not yet run; queue after T071+T072 pass
3. **T074 sequence**: Strict FE sequence; blocks T076
4. **T076 final sweep**: Design e2e + screenshots at 390/820/1440 px, contrast, animation
5. **Worktree cleanup**: Stale `.claude/worktrees/agent-a4628e381b8ec6bcc` and branch `worktree-agent-a4628e381b8ec6bcc` (user to remove; sandbox blocked agent)
6. **Uncommitted state**: docs/qa/* from tester (leave uncommitted; user-owned decision), .claude/agents/* edits (cache reloads next session)

## Exact Next Command
1. Tester finishes T071+T072 verification; if green, test T073
2. If T073 green, frontend-builder starts T074:
   - Read DESIGN.md + PRODUCT.md
   - Test first: add to test_design_tokens.py (no hex/rgb outside :root) and test_e2e_design.py (F-017 keep, opacity, states, motion, forced-colours)
   - Update app.css: working card, notes, alert, empty, cited/new fades, reduced motion, forced colours
   - One commit with app.css + tests
3. After T074 green, frontend-builder: T076 design e2e sweep + screenshots
4. After T076 green, tester runs final pytest + ruff + e2e sweep full project
5. If all green, set DONE=true, report complete

## Task/Commit Verification
- T001-T067: 67 tasks, all ticked, all committed ✓
- T068-T073: 6 tasks, all ticked (94ed09e, f6275a5, fb34554, 3f6cc23, d08cf70, 59debeb), all committed ✓
- T074: NOT ticked, NOT committed (waiting for FE)
- T075: 1 task, ticked, committed (40b7ac1) ✓
- T076: NOT ticked, NOT committed (waiting for FE after T074)
- fix(F-020): committed (c41d740), not a task ✓

**DONE flag**: false (T074, T076, tester final pass remain)
**Blocker**: None. Tester verifying T071+T072; when complete, FE proceeds T074.
**Next agent**: tester (finish T071+T072 verify, queue T073) → frontend-builder (T074) → frontend-builder (T076) → tester (final pass).
