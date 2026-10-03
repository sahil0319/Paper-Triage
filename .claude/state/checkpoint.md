# Checkpoint: v4 Build In Progress

**Phase**: v4 build (Carbon redesign, FR-030)

**Status**: Wave R1 complete (MIME type + fonts + token layer). T066-T067 done. T075 (README) landed. T068-T074 started (FE strict sequence). Tester verified F-016..F-019 + T066-T067: pytest 532 x2, ruff clean, docs/qa/v4-fixes.md green.

## Summary

### Completed (v4 wave R1)

- **T066**: woff2 MIME type registration (BE)
- **T067**: IBM Plex fonts vendored (FE; 8 woff2 files, 125 KB, OFL 1.1)
- **T075**: README + SETUP_LOG v4 design note (BE; Carbon, font fetch, design e2e command)
- **F-016, F-017, F-019 fix commits**: previous results stay interactive during search, highlight selection, preview opens on Ask tab (landed d323ef9, 57a8e71, 6a1912c)

### In Progress (FE strict sequence)

- **T068**: Token layer + global type, focus, hover, motion (started)
- T069-T074: Shell, nav, buttons, query → Library → Preview toolbar → Panel, notes, paper chat → States, motion, forced colours
- T076: Design e2e sweep + screenshots (needs T068-T074, T066 font GET)

### Tests Status

- **v3 final**: pytest 532 pass, ruff clean (42fbfc3)
- **v4 in-flight fixes**: F-016 highlight selection, F-017 previous results opacity, F-019 preview tab
- **Tester gate** (docs/qa/v4-fixes.md): all fixes PASS, ready for v4 build

## Files Touched (Last Wave)

- `pt/app.py` (T066: mimetypes, T050)
- `pt/static/vendor/fonts/**` (T067: woff2 files, plex.css, README)
- `pt/static/index.html` (T067: font CSS link)
- `tests/frontend/test_static_assets.py` (T067: font validation)
- `README.md`, `SETUP_LOG.md` (T075: v4 design note, build-time font fetch)
- `.claude/state/` (this checkpoint)

## Known Open Items

1. **T068-T074**: FE tasks edit `app.css` sequentially; no parallelism. Each task:
   - Test first (parse tokens, visual assertions)
   - Update CSS (global tokens, per-component styles)
   - Keep all v2/v3 UI hooks + e2e checks
   - One commit with `app.css` + tests only
2. **T076**: Screenshot proof at 390/820/1440 px, contrast checks, animation assertions
3. **Post-T076**: tester full pytest + ruff + e2e sweep; designer re-audit on screenshots; any fixes become T077+

## Exact Next Command

FE continues at T068: read DESIGN.md + PRODUCT.md, implement token layer + global type styles, test design tokens parse, commit. Loop until T074 done, then T076 design e2e sweep, then tester final pass.

---

**Task Count**: T001-T067, T075 done (68 total); T068-T074, T076 in progress (8 remaining).
**DONE flag**: false.
**Blocker**: None. FE on task.
**Next agent**: frontend-builder (T068).
