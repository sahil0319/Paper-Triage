
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
- fix(v3-audit) focus order: #pv-sheet-open now direct child of .pv-toolbar after #pv-controls; mobile order also puts export/external before controls so DOM order = visual order. Tab-order e2e at 390/820/1280 + failed/pending state test. Suite 503 pass.

## F-016 / F-017 / F-019 (user-reported fixes, 2026-10-03)
- F-016 325f7f3: root causes = (1) app.css lacked pdf.js text-layer rules (span font-size from --total-scale-factor*--font-height, scaleX) -> text ~10% narrower than canvas; (2) no .endOfContent guard -> drag leaving spans jumped focus to page end; (3) quote glued lines (br ignored by range.toString). Fix: CSS rules, viewer.js endOfContent+selecting logic, scale from sec.clientWidth, annotations.js rangeText(). Do NOT define --scale-round-x/y (rounded inline width broke drags in Chromium). 4 e2e tests (two-column PDF helper in ptstubs.two_column_pdf).
- F-017 57a8e71: removed inert + 0.4 opacity (.is-stale kept as hook); aria-busy now on #paper-list not section; focus in replaced rows -> #results-heading. 2 e2e tests (held /api/triage).
- F-019 viewer.js open(): selectTab("chat") for new paper; index.html initial tab state flipped. Narrow: sheet stays closed, chat tab preselected. 2 e2e tests; hl specs use hl_tab().
- F-018 client side: not investigated deeply; no client validation seen in runTriage (query sent as-is).

## T067 (resumed after crash) - done
- Goal: vendor IBM Plex + static guard. Status: committed.
- 6 fontsource files byte-identical (cmp) to npm pack 5.3.0; greek = @ibm/plex-sans@1.1.0 Regular/SemiBold split, cmp ok. Total 125,228 B.
- unicode-range copied verbatim from Fontsource 5.3.0 400.css/600.css (sans+mono latin, latin-ext).
- plex.css, README (sha256 per file) written; one link before app.css.
- Tests: tests/frontend 166 pass; test_api woff2 2 pass. Needed E2E_PORT=8765 (8766 held by tester).
- Next: T068 (tokens) - not started.

## T068 - done
- Test first: tests/frontend/test_design_tokens.py (12 tests). app.css :root replaced with full DESIGN.md token set (all declared, T069-T074 will use them); old tokens removed; vars remapped per brief item 3.
- Focus: one system (inset for controls, inset white ring for filled, none on script-focus containers; tabs w/ tabindex=-1 keep ring). Hover rules only in @media (hover: hover). Reduced-motion: universal transition none.
- Beyond remap (needed for coherence): alert -> error notification, refusal/no-PDF -> info notification, working card surface-1, btn--on-dark -> charcoal, icon-btn square ghost, tag pressed surface-inverse, rail current bar, tab/nav underline primary.
- Updated test_e2e_library disabled export colour (rgb(140,140,140)).
- Tests: tests/frontend 178 pass (E2E_PORT=8765). Next: T069.

## T069 - done
- Test first: tests/frontend/test_e2e_design.py (8 e2e: font loads, nav 48/600/2px primary rule, badge pill, submit 48 + full width @390, Carbon field, inset focus ring, button variants).
- app.css: Carbon text field base (surface-1, bottom rule, 40px; 48 topic; canvas in panels; invalid/disabled), all input height overrides (44px) removed; .btn 40px base; secondary charcoal = .btn--on-dark, #load-more, .alert .btn--secondary; model label ink-subtle; nav links 47px+underline overlap.
- Deferred (per tasks): selects/chevron -> T071/T072; textarea -> T073.
- Tests: tests/frontend 186 pass (E2E_PORT=8765). Next: T070.

## T070 + F-020 - done
- T070 (fb34554): tests added to test_e2e_design.py (rank/meter/mono/cite/refusal/saved/critique/chat panel/row padding). Most already held after T068/T069 remap; CSS delta: .paper grid 56px, padding 16/24, .critique .none ink-subtle, .btn--suggest 40px, .save.is-busy .6, .turn__a:has(.cite) line-height 1.9.
- F-020: test waits for sheet getAnimations().finished before bounding_box; tolerance unchanged. 12/12 solo pass on 8765.
- tests/frontend 193 pass. Next: T071.

## T071 - done
- Tests (5, in test_e2e_design.py, LibraryStub w/ 2 items): rail current weight/shadow/fill/32px, pressed tag rgb(22,22,22), row select 32px appearance none + chevron, no height transition, filter field Carbon.
- app.css: rail 32px (40 coarse); .select Carbon + SVG data-URI chevron (canvas in .pv-panel, surface-1 in sheet; .pv-hlctl select stays outline); lib-dir/hl-item selects 32px; .lib-row collapse via grid-template-rows 1fr->0fr.
- library.js collapse(): removed inline height/overflow (needed for CSS-only collapse); timeout 250ms.
- #pv-zoom (.pv-zoom, no .select) untouched -> T072.
- tests/frontend 198 pass. Next: T072.

## T072 - done
- Tests (8 incl. 3 parametrised, hl_preview helpers imported from test_e2e_library): toolbar controls 40px square, joined hl control, opaque yellow/mint/peach fills + multiply layer + named list + 3px quote rule + dot circle, page edge rgb(198,198,198) no shadow, popover square+shadow+round swatches, find field Carbon.
- app.css: highlights opaque (no color-mix), .dot 12px, quote rule 3px, .pv-zoom folded into .select Carbon rule, #pv-hl-color outline select compact padding; <1024 toolbar row-gap 4 / padding 8 (keeps audit toolbar height <260 after 40px selects).
- F-016 text-layer rules untouched. tests/frontend 206 pass. Next: T073.

## T073 - done
- Tests (4): selected tab Ask this paper 600/2px primary/40px, panel surface-1 + border-page edge, zero paper-chat requests; notes textarea Carbon canvas; 390 sheet opens on Ask tab, square, shadow, overlay backdrop, ease-entrance; 2401.00005 no-PDF info notification.
- app.css delta small (most held from T068): .pv-tab 40px, tabs gap 16, textarea Carbon (surface-1 in sheet), .pdf-page__notext 3px info rule.
- F-019/F-020 behaviours untouched. tests/frontend 210 pass. Next: T074.

## T074 - done (f3a2946)
- Tests first: test_design_tokens.py +7 static (no rgb()/hsl() outside :root except data: URI and forced-colors; no unused token; weights 400/600/normal; every animation selector has animation:none under reduced motion + universal transition kill; forced-colors selector coverage; alert no coral; .is-stale no opacity/pointer-events). test_e2e_design.py +9 (F-017 prev rows opacity 1 + clickable, working card, alert rgb(255,241,241), empty state, flash animation names/1.6s, reduced motion static markers + getAnimations()==0, working glyph static, forced colours borders, sheet reduced/forced).
- Most T074 CSS already held after T068-T073. CSS delta: forced-colors block adds borders for .pdf-page__notext/.dir-manage/.pv-panel/fields, rail current left bar (box-shadow is dropped in forced colours), last-swatch outline, .hl-layer forced-color-adjust none.
- Gotcha: shared live server keeps stored papers, so empty-state test routes /api/papers empty. #alert Try again keeps class btn--on-dark (charcoal), not btn--secondary.

## F-022 - done
- #pv-export / #pv-external 40px via .pv-toolbar override (margin 0, padding 0 4px; external 0 inline). Padding 12px broke tablet title width (>380 audit test), so kept narrow. Test: test_toolbar_controls_are_40px_and_square extended at 1440/820/390. Mobile toolbar <260 test passes. tests/frontend 228 pass (E2E_PORT=8765).
- Next: T076.

## T076 - done (651ea2f)
- test_e2e_design.py +~40 param cases (views x 390/820/1440): woff2 content-type + zero remote, fonts.check, in-page WCAG contrast (selector list from tasks), 2px blue ring on Tab to #submit, reduced-motion getAnimations()==0 on cited/new/disclosure/sheet + static markers, forced-colours borders, screenshots to V4_SHOTS_DIR (session tmp dir default; preview = panel 1440, sheet 390/820).
- F-016/F-017/F-019 already have browser checks (test_e2e_library F-016 block, test_e2e_browser F-017, T073 tests); no extra added.
- Design e2e x3 green (83). Full -m e2e 229 pass.

## F-023 - done
- Wait for data-annotation-id digits before measuring .hl; solo x12 green. Added sheet textarea surface-1 test and .pdf-page__notext info rule test. design e2e 85 pass.

## v4 audit fixes - done
- fa4c533 rail count ink-muted (current + hover); 7d6885f forced-colours underline only current link/tab; 3f21547 .pv-back ghost; bf43594 dir form submit + Save note primary (library.js, annotations.js); c32275c .confirm margin-bottom 12 + mobile .paper__head .btn margin-bottom 8; item 6 commit: .pv-stage > .empty column 640 centred, heading-sm, h1+title attr "Not in your Library" (doc title and load-error h1 stay Preview).
- tests/frontend 279 pass, design e2e 93 pass, ruff clean. No servers left running.
