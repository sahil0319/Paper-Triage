
## Wave A (T017, T021 ui, T020)
- T017 cb8e547: kept prior app.js; fixed h() array-child bug (ul lists threw), added authors line. Verified vs real mock server via fake-DOM harness (scratchpad, not in git).
- T021 ui 0c025df: load /api/status (mock label, model) + /api/papers (stored list, "Showing N stored papers..."). Ticked (api commit ca2e161 exists).
- T020 chat UI: log role=log, [id] markers -> links only for validated citations, dropped markers stripped, "Cited papers" list w/ titles, refusal = calm bordered block "Not covered by your papers", errors inline. Cites to papers not in current list render as plain text (chat store spans topics).
- No real-browser visual check (no browser tool). detect: tight-leading on .lead (21px/1.19, from T016) -> T023.
- Next: T023 (polish, a11y, visual pass in a browser).

## Wave D (T034-T037)
- T034 926b609: tests/frontend/test_static_assets.py. Run via `.venv/bin/python -m pytest tests/frontend` (`uv run pytest` fails: no pytest in uv env).
- T035 (see git log): index.html shell + app.css tokens/base/nav/query/results header/notes/alert/empty/chat panel. Headless chrome: ~/Library/Caches/ms-playwright/chromium_headless_shell-1243/.../chrome-headless-shell --screenshot (no playwright pkg).
- T036 fd0d011: app.js rewritten (state.rows, chips, refusal, Ask again, suggestions as sibling above #chat-log not inside role=log, / and Escape). Verified via CDP script in scratchpad (cdp.mjs) with fetch stubs; no horizontal scroll 320-1440.
- T037 fefb167: working card + D16/D17/D18 verified via CDP (appears at ~300ms, verb rotates 2.4s / 5s reduced, inert list, removed on success/error). impeccable detect: 2 heuristic hits (cramped intro false positive, flat-type-hierarchy likely CSS-unaware). Left for wave E: T038 links slot (.paper__meta), T039 load-more, T040 scope, T041 e2e. NEEDS-BE none.
- T037 fix 717e5eb (A2: #empty hidden while running). T038 ad4980c: a[data-link] abs/pdf, safeUrl http(s) only, derive fallback. Server start: uv run python -m uvicorn ... (uvicorn bin not on uv run path).
- T039 98066a2: #load-more-wrap, compact card via startWorking(el,true), generation counter drops stale replies.
- T040 51587b9: refreshChat() scope line + disable when no rows; verified vs real server (France refused, in-set cite, id search replaces set).
- T041 0abd7b4: tests/frontend/test_e2e_browser.py, 7 cases, uv run pytest -m e2e green (8 incl. harness). Full suite 226 pass, ruff clean.
- F-003 a04adfc (reduced-motion tint, static verb 'Triaging papers…'/'Loading more papers…'; deviates from brief D17 5s swap per FR-012). F-004 568d480: +direct-PDF case (mock supports pdf URLs, no NEEDS-BE), cites-only seeds 11-15 then re-searches, refusal has positive control. Gaps left: load-more error, 50 cap, chat-disabled e2e (manual only).

## F-006 reset chat on result-set change
- Goal: load-more must clear chat transcript and rescope. Status: done.
- Root cause: transcript never cleared anywhere (load-more AND new search); scope line text only. No visible reset note.
- Fix: `resetChat()` in app.js (clears #chat-log, shows `#chat-note` "Chat now covers N papers. Earlier questions were cleared.", appends to #status). Called on load-more with added rows and on new search with prior rows. Error / no-new-rows path untouched. Stale chat replies dropped via chatGen.
- Tests: 3 e2e specs added (ids count 10 -> 15, error keeps chat, new search clears). 233 pytest pass.
- Next: tester re-verify.

## F-007/F-008 (loop 2)
- resetChat now appends scope sentence to #status once (render + load-more), clears chatBusy; stale settle guarded by chatGen. Note names failed rows when any (count = ok rows, paper_ids = all shown per contract).
- 3 e2e specs added; 236 pass. Next: tester re-verify.

## v3 Wave F (2026-10-03)
- T052 done be3cbf1: pdfjs-dist 6.3.289 modern vendored, guard extended. T053 done: nav.views, hash router (app.js), #library/#preview shells, PT global for viewer.js, tests/frontend/{ptstubs.py,test_e2e_library.py}.
- Next: T054 save toggle, T055 viewer, T056 find.
- T054 c72e508 save toggle (POST uses data.topic from triage/papers response). T055 eb16174 viewer.js (pdf.js canvas+textLayer, zoom, page nav, keys, states, poll 3s; window.__PT_POLL_MS test hook). T056 find row.
- Tests: tests/frontend 62 pass (E2E_PORT=8765), full suite 406 pass, ruff clean. Stubs: tests/frontend/ptstubs.py. One real-API e2e (save->preview).
- Hooks for Wave G: window.PT (app.js) and window.PTViewer {open, close, goToPage(n,{flash}), flashPage, openFind, els}; #pv-panel hidden aside + skip link data-skip-needs; app.js renderLibrary is a placeholder list for T060; libraryAdd/Remove keep nav count.
- No NEEDS-BE. Selection color in textLayer is info-border 30% (cream would hide canvas text).
- Selection colour deviation (info-border 30%) accepted by coordinator.

## v3 Wave G (2026-10-03)
- Fix b829885 F-009 (retry stuck: poll uses reloadLibrary, retry shows pending from a copy) + F-011 (find hit focuses well).
- T060 8be3853 library.js list/filters/tags/poll/retry. T061 700199b rail, directories, move/remove. T062 0b611ff annotations.js (highlights, notes, undo, export, scanned msg). T063 paperchat.js + sheet (viewer.js tabs).
- Test hooks (test only): window.__PT_POLL_MS, __PT_UNDO_MS, __PT_CHAT_SLOW_MS. Stubs: ptstubs.py (library, directories-less, annotations). Real-harness tests use real_library fixture (wipes library + directories).
- Counts: tests/frontend 94+ e2e; full suite 471 pass; ruff clean. Detector: only layout-transition (row collapse height, per brief) + 2 old intro hits.
- Deviation: selection colour in text layer accepted; highlight Go to / hit-layer click-to-select skipped (list is required path).
- No NEEDS-BE.

## v3 audit + Wave H (2026-10-03)
- fix(v3-audit) 6e1b9a1 (Library items 1-6) and 22781d9 (Preview items 7-13 + F-013 rgba->color-mix tokens). F-012 test fix committed. T064 committed (7 real-harness e2e: 2 s first page, 5 s PDF ready, 3 actions, lazy chat, unsave, unavailable chat, restart persistence on port E2E_PORT+30).
- Mobile toolbar 350px -> 231px (4 rows, not 3: Highlight split + sheet button need own row at 390px).
- Refusal title "Not in this paper" and hint are FE copy from brief table; refusal body is the server answer verbatim.
- Full suite 497 pass, ruff clean.
