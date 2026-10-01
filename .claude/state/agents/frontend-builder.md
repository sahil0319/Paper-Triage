
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
