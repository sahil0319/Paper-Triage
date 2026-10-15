# v3 Wave G FE verification (T060 8be3853, T061 700199b, T062 0b611ff, T063 0cd0726, fixes b829885)

Date 2026-10-03. Tested in the main tree at HEAD 0cd0726 (FE idle). MOCK_LLM=1, offline, own server on port 8766 with a scratch DB and data dir, Chromium via Playwright. Verdict: PASS. No [BE] defects. Two low [FE] findings (F-012 flaky test, F-013 token literals). F-009 and F-011 verified fixed.

## Automated
- `uv run pytest -q` (full): 470 passed, 1 failed once (F-012), 471 collected. `ruff check .`: clean.
- `pytest -q -m e2e` x3: 112 passed each (about 61 s), stable. `tests/frontend/test_e2e_library.py` x3: 97 passed each.
- F-012: `-k highlight_persists` alone fails every time; see failures.md for cause (optimistic `.hl` node replaced about 10 ms later; test races it). Product behaviour is fine.
- `tests/frontend/test_static_assets.py`: 16 passed. Own grep: no `import(`, `@import`, or external fetch; the only `https://` strings are the two arXiv display-link fallbacks in `app.js:228-229` and the SVG namespace.
- `npx impeccable detect src/paper_triage/static`: 3 findings. Two known false positives (cramped-padding `.intro`, flat-type-hierarchy). New: `app.css:656` `[layout-transition] transition: height` on `.lib-row.is-collapsing`. Judgement: accept. It animates a single row for 200 ms, the brief (L13) asks for height + opacity, and under reduced motion `collapse()` returns before touching the style and the CSS has `.lib-row.is-collapsing { transition: none }` (measured: row gone after 0.019 s, computed transition 0s, no running animations). Normal motion: height 280 -> 0 px in about 120 ms of samples, no layout shift elsewhere.
- Token adherence (F-013): no hex outside `:root`; literal `rgba()` at `app.css:707-709`, `:758`, `:773` (F-010 accepted). Values equal the tokens.

## Own Playwright (real API)
Library (L10, L11, L12, L14, SC-012)
- 5 saved papers via real API: tag order count desc then A-Z (`diffusion 5, distillation 5, generation 4, video 4, guidance 2`). AND: `diffusion` = 5 rows, `diffusion` + `video` = 4 rows; summary `Showing papers tagged diffusion and video.`; pressed chips sort first; count `4 of 5 saved papers`, `#status` mirrors it.
- Tag search `guid`: chips = matching + both selected ones; rows narrow to the title match. Selecting a chip while text is present clears the text. Clear filters: 5 rows, focus on `#lib-filter`, `Filters cleared. 5 saved papers.`, button hides. Title filter `consistency` = exact row; Esc clears; `/` focuses; no-match state with `Clear filters`; hash filters restored on reload.
- Overflow: 25 tags give `Show all 25 tags`. Row content matches L11 (rank `/10`, `for "topic"`, tags line, id, `Saved 3 Oct`, PDF status, links, Directory select, Remove, critique).
- Status: failed row `PDF unavailable` + `Try again`; Retry POST sent, row goes `pending` then back to `failed` with `Try again` again (no stuck state). Polling (stub, 500 ms): `Downloading PDF…` -> `PDF ready`, polling stops after the last pending row (4 GETs, none after).
Directories (L8-L10b, L13, SC-015)
- Create: empty -> `Enter a name.` with `aria-invalid`; reserved `Unsorted` / `all saved` -> `"..." already exists.`; duplicate `NETWORK` vs `network` -> exists (case-insensitive); input `maxlength=40` truncates a 41-char entry to 40 (the 40-char name is accepted; client guard and API 422 for >40 are covered in pytest). Esc cancels and refocuses `New directory`. Created and renamed announced, rail A-Z, counts correct.
- Rename: input focused with all text selected. Delete: confirm `Delete "network"? Its 3 papers move to Unsorted.`, focus on `Keep`, Esc = Keep; confirm -> `Directory deleted. 3 papers moved to Unsorted.`, total unchanged (5), all in Unsorted. Empty directory copy `No papers in <name>.`
- Move: select commits at once, `Moved to network.`; filtered-out row collapses and focus lands on the next row's `Open preview`. Remove: always confirms (`Remove from Library? This deletes the saved PDF.`), Esc keeps focus on the trigger, confirm removes the row, `Removed from Library.`, focus to the h1 when the last row goes.
Highlights (L16-L19, L23, SC-013)
- Popover swatches `Highlight yellow/mint/peach`; toolbar `Highlight` is `aria-disabled` without a selection; three colours render (0.45 alpha, `.hl-layer` multiply, pointer-events none); `Yellow highlight added on page 1.`
- Persist across reload (3 items, rects on pages 1 and 2); rect width ratio constant at fit, 200 % and 50 % (0.2714). API rects all within 0..1.
- Notes: editor focused, maxlength 500, counter from 400 (`410/500`, coral at 500), Ctrl+Enter saves, Esc cancels, `Save note` edits, colour select persists. `Go to` scrolls and flashes the page, focus to the viewer region. Delete -> `Highlight deleted.` + `Undo` (focus on Undo), Undo restores note and colour; without Undo the row clears after 8 s.
- Export: `2401.00002-notes.md` with title, id + abs URL, quotes with `(p.N)` and notes; `Notes exported.`; button `aria-disabled` when empty.
- Scanned page (blank PDF routed): `No selectable text on this page. You can still add a note for this page.`, highlight button disabled, page note saves (`Note added on page 1.`) and exports as `Page 1 note: ...`.
- Observation (not a defect): page notes are in the list but the tab count and `highlight_count` only count highlights.
Paper chat (L20, SC-014)
- Zero `/api/paper-chat` requests on open, tab switch and typing; first submit sends `{"paper_id","question","history":[]}`. Held request: `Reading this paper. The first answer takes longer.`, Ask disabled, input editable, after 20 s `Still reading. Long papers take up to a minute.`; later turns `Reading this paper…`.
- Mock answer cites `p. 2` as `button.cite` (`aria-label="Go to page 2"`); click jumps to page 2, flashes the page, focus to the viewer. Refusal: `Not in this paper` + hint. History grows 0..6 and stays 6 over 9 requests (oldest dropped). Transcript cleared on reload and on Back + reopen; caption `This chat clears when you close the preview or reload.` 502 -> `Could not answer. model call failed: boom`, question restored, idle copy back.
- Failed PDF (`2401.00005`): `Chat needs the PDF text, and this PDF is unavailable.`, input and Ask disabled, no chat form usable, idle block and starters hidden.
Unsave and F-009 / F-011
- Library Remove with 2 highlights: confirm names `2 highlights with their notes`; afterwards annotations and PDF endpoints give 404 and the file is gone from `pdfs/`.
- F-009: failed preview, `Try again` -> Downloading, then the alert returns on its own (first and second retry); leaving and returning shows the alert. RESOLVED.
- F-011: find hit click jumps to page 2 and focus is `#pv-pages`. RESOLVED.
A11y, motion, narrow
- Tabs: `aria-selected`, `aria-controls`, roving tabindex, ArrowRight/Home/End move focus and selection; tabpanels `aria-labelledby`. `#status` role=status polite; chat log role=log, label set. Tab order in the preview follows the brief; focus ring 2 px solid `rgb(69,143,255)`.
- Reduced motion: no running animations, flash is a static 2 px outline, sheet animation none, row collapse instant.
- 800 and 390 px: rail hidden, native `Directory` select with counts, `Manage directories` disclosure (`aria-expanded`) with Rename, Delete (confirm), New directory working; no horizontal overflow in Library or Preview; panel not inline, `Highlights and chat` opens a `<dialog>` 85 % tall (765 of 900), chat works inside, citation closes the sheet and jumps, Esc and Close return focus to the toolbar button, popover `Add note` opens the sheet with the note editor focused.
Network and regressions
- Every run: zero non-local requests, zero console errors (one expected 502 from my own stub).
- F-006..F-008: `f006.py`/`f007.py` re-run: reset note and status, stale reply ignored, Ask enabled while stale reply pending, 50-paper cap; no new findings.

## Findings
- F-012 [FE] low: flaky e2e (test race), logged.
- F-013 [FE] low: rgba literals instead of tokens, logged.
- F-009, F-011 closed.

## Cleanup
Server on 8766 killed, port free. Scripts and screenshots in the session scratchpad. No src/ or tests/ edits. no-mistakes gate not run (per-wave pass).
