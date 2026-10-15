# QA failures

## F-001 (T010, low) fetch crashes on host-less URL  [loop 1/3] RESOLVED (verified 2026-10-01, commit e52a67a)

Spec (tasks.md T010): unreachable URL -> error entry, others continue.

Repro (offline, MOCK_LLM=1):

    unset VIRTUAL_ENV; export PATH=$HOME/.local/bin:$PATH MOCK_LLM=1
    uv run python - <<'PY'
    import tempfile, os
    from paper_triage import db, net
    from paper_triage.fetcher import Fetcher
    from paper_triage.input_parse import parse_query
    conn = db.connect(os.path.join(tempfile.mkdtemp(), "x.db")); db.init_schema(conn)
    c, t = net.make_http(True)
    topic, items = parse_query("http://")      # -> [Item('pdf', 'http://')]
    Fetcher(conn, c, t).fetch(topic, items, 10)
    PY

Actual: `AttributeError: 'NoneType' object has no attribute 'endswith'`
(src/paper_triage/fetcher.py `_pdf_paper`: `urlparse(url).hostname.endswith("arxiv.org")`, hostname is None).
Expected: `([], [{"input": "http://", "reason": ...}])`; other items unaffected.
Suggested fix: `(urlparse(url).hostname or "").endswith("arxiv.org")`; add a test in tests/test_fetcher.py.

Resolution: repro now returns `([], [{'input': 'http://', 'reason': "download failed: unknown url type: '/'"}])`; regression test `test_fetch_hostless_url_is_error_others_continue` added and passing.

## v2 final pass (2026-10-01, HEAD 0abd7b4). All LOW / optional. None blocks v2 acceptance.

### F-002 [BE] low RESOLVED (verified 2026-10-01, commit 6cd65e0), pre-existing: re-running a stored topic does not become "last run"
Where: `src/paper_triage/pipeline.py:139-142` skips `save_result` for papers whose result for that topic is already `ok`, so `results.created_at` is not refreshed; `db.latest_topic` (`db.py:172-173`) orders by `created_at`.
Repro (MOCK_LLM=1, fresh DB, port 8766, `uv run python -m uvicorn paper_triage.app:app`):
1. POST /api/triage `{"query":"diffusion distillation"}` then `{"query":"diffusion distillation","max_results":5,"offset":10}`.
2. POST /api/triage `{"query":"reduced motion probe"}`.
3. Repeat step 1 (both calls; everything is already stored).
4. GET /api/papers.
Expected: topic `diffusion distillation` (15 papers), the most recent search.
Actual: topic `reduced motion probe` (10 papers). In the browser, search "diffusion distillation" + Load 5 more, then reload: page shows the older topic and "Chatting about 10 papers from your last run." instead of 15 papers.
Suggested fix: touch `created_at` (or a `last_run` marker) for every paper returned by a run, not only for newly saved results.

### F-003 [FE] low RESOLVED (verified 2026-10-01, commit a04adfc): `.paper--new` reduced-motion fallback trips `impeccable detect` side-tab
Where: `src/paper_triage/static/app.css:570` `.paper--new { animation: none; box-shadow: inset 3px 0 0 var(--color-cream); }`.
Repro: `npx impeccable detect src/paper_triage/static` -> `[side-tab] .paper--new — inset box-shadow 3px stripe (left)`. v1 final run returned `[]`; wave D had 2 known false positives (A1); this is the third and the only one that is a real design tell.
Expected: no new finding. Suggested: use a full inset hairline (`inset 0 0 0 1px`) or a background tint for the reduced-motion marker.

### F-004 [FE] low RESOLVED (verified 2026-10-01, commit 568d480): browser e2e gaps and one order-dependent assertion (tests/frontend/test_e2e_browser.py)
- No case for a direct-PDF row: SC-007 "direct PDF: 1 link" (abs link absent, pdf link only) is never asserted in a browser. Only arXiv rows are checked (lines 52-65).
- `test_chat_answer_cites_only_shown_papers` (lines 114-124): `cited <= shown` is only meaningful when stored-but-not-shown papers exist. Those come from `test_load_more_appends_five_then_ends` via the session-scoped DB; run alone (`-k cites_only`) the check is near-trivial. It also never asserts the cited id is the expected `2401.00003`.
- `test_chat_refuses_paper_outside_the_current_set` (lines 102-111) has no positive control for the same word in the full set (test 7 uses a different paper), so a mock-rule regression that refuses everything would pass it. Test 7 is the only guard.
- Not covered in a browser: load-more error and Try again, 50-paper cap, chat disabled with an empty set (all verified manually in final.md).

### F-005 [BE] low RESOLVED (verified 2026-10-01, commit bbbe244): e2e harness does not fail when its port is already in use
Where: `tests/e2e_harness.py:55-74` (`start` readiness probe only checks `GET /api/status` == 200).
Repro: start any server on 8766 (e.g. `MOCK_LLM=1 uv run python -m uvicorn paper_triage.app:app --port 8766`), then `uv run pytest -q -m e2e -k indicator`.
Expected: clear "port in use" error. Actual: the harness thread fails to bind, the probe passes against the foreign server, the test runs against it with no triage delay and fails with "Locator expected to be visible ... hidden" (misleading). Suggested: bind-check the port (or assert `server.started`) before the probe.

### Re-verification of F-002..F-005 (2026-10-01, HEAD 568d480): all RESOLVED
- F-002: original API repro now ends with `papers 'diffusion distillation' 15`. `test_touch_results_refreshes_latest_topic_only_for_given_papers` and `test_rerun_of_stored_topic_becomes_latest_topic` both FAIL against the pre-fix source (6cd65e0~1 extracted to a scratch dir outside the repo, tests from HEAD) and pass on HEAD.
- F-003: `npx impeccable detect` now 2 findings (known false positives only); side-tab gone. Reduced motion: new row background rgb(245, 233, 212), animation none, no box-shadow; no horizontal scroll at 320/768/1440. Working verb is static ("Triaging papers…" unchanged after 6 s).
- F-004: direct-PDF row asserts 1 link, href equals the URL, target and rel. Refusal test now has a positive control. `cites_only` seeds its own stored-but-not-shown paper (2401.00015). Residual note, not a defect: with the mock's "first matching paper" rule, `cited == {2401.00003}` cannot by itself detect an out-of-scope leak (a leaked paper would sit later in the context); that leak is covered by the out-of-set refusal test, which does fail on a leak.
- F-005: with a server on 8766, `pytest -m e2e` errors at setup with `RuntimeError: port 8766 is already in use; stop that server or set E2E_PORT`.

### F-007 [FE] low RESOLVED (verified 2026-10-03, commit c911fa1): new-search chat reset not announced
`render()` calls `resetChat()` but `#status` stays "1 paper ranked. Results below."; `#chat-note` has no live region. Load-more path appends the sentence, new-search path does not. Repro: 8766 MOCK_LLM=1; search "diffusion distillation" then "2401.00001"; read `#status`. Details: docs/qa/F-006.md.

### F-008 [FE] low RESOLVED (verified 2026-10-03, commit c911fa1): Ask disabled after reset while stale chat reply in flight
`chatBusy` stays true until the dropped request settles, so `#ask` is disabled and Enter is a silent no-op for the new scope. Repro: search; ask with `/api/chat` held; click `#load-more`; `#ask` disabled. Details: docs/qa/F-006.md.

F-007/F-008 re-verified at c911fa1: announced once per reset, Ask usable while a stale reply is pending, stale reply ignored, no cross-talk. See docs/qa/F-006.md.

### F-009 [FE] medium RESOLVED (verified 2026-10-03, HEAD 0cd0726, fix b829885; found a2bf9e3): Retry on a failed PDF leaves the viewer stuck on "Downloading the PDF..."
Where: `static/viewer.js` `showUnavailable()` retry handler mutates the cached item in place (`it.pdf = {status: "pending"...}`), while `static/app.js` `loadLibrary()` only calls `setLibrary()` when the fetched JSON differs from `lib.sig` (the last server snapshot). When the retry fails again with the same error, the server JSON equals `lib.sig`, so `changed` is false, the cache keeps the fake `pending`, and the poll never sees `failed`.
Repro (MOCK_LLM=1, port 8766, `window.__PT_POLL_MS=300` optional): search `2401.00005`, click Save (mock download returns non-PDF -> `failed`, "Not a PDF."); open `#/library/paper/2401.00005`; click `Try again`. Viewer shows "Downloading the PDF..." and never leaves it (checked 6 s; `GET /api/library` says `failed`, `PT.libItem('2401.00005').pdf.status` stays `pending`). Leaving to `#/library` and returning shows the same stale card (cache not refreshed, sig equal). Only a page reload recovers.
Expected: after the retry fails again the alert "This PDF could not be downloaded." returns, with the new reason.
Fix hint: in the retry handler, do not mutate the shared item (render pending from a copy), or set `lib.sig = ""` after the mutation, or make the poll always `setLibrary` when `statusKey` differs from the viewer's key.

### F-010 [FE] low ACCEPTED (deviation, approved by router during Wave F: info-border at 30% alpha because cream hides the canvas text) (found 2026-10-03, a2bf9e3): PDF text selection uses a hard-coded blue, brief L17 says the global cream selection
Where: `static/app.css:664` `.textLayer ::selection { background: rgba(69, 143, 255, 0.3); color: transparent; }`. Brief L17: "Text selection color inside the PDF stays the global `::selection` (cream)" and the design system forbids literals outside tokens. Repro: open any ready preview, select text, compare with `::selection` at `app.css:121`. Expected: `var(--color-cream)` (or a token-based decision recorded in the brief if cream is invisible on the white page).

### F-011 [FE] low RESOLVED (verified 2026-10-03, HEAD 0cd0726, fix b829885; found a2bf9e3): activating a find result leaves focus on the result button
Brief L24 says activating a result uses "the same jump/outline as L19", and L19 says focus moves to the viewer region. Observed: jump, page flash and page input update work, but `document.activeElement` stays the `.find-hit` button; find row stays open. Repro: preview 2401.00001, press `f`, type `Quartzite`, Enter, click the result. Arguably useful for stepping through results; designer/planner to decide: either move focus to `#pv-pages` or amend the brief.

Wave F FE verification (a2bf9e3): see docs/qa/v3-wave-F-fe.md. F-009 [FE] blocks nothing in Wave G but should be fixed before the final pass.

### F-012 [FE] low OPEN (found 2026-10-03, HEAD 0cd0726): flaky e2e `test_real_highlight_persists_and_scales_with_zoom` (tests/frontend/test_e2e_library.py:1776-1782)
Repro: `MOCK_LLM=1 uv run pytest -q tests/frontend/test_e2e_library.py -k highlight_persists` fails every time when run alone (`Locator.evaluate: TypeError: Cannot read properties of null (reading 'clientWidth')` at line 1781); in the full file it passes (3 of 3) and failed once in 1 of 5 full-suite runs. Cause: the optimistic `.hl` node is replaced by the server-confirmed node about 10 ms after creation (MutationObserver log: `add@669, rm@679, add@679`). `expect(hls(page).first).to_be_attached()` can return on the first node, and the next `.evaluate` then runs on a detached node (`closest('.pdf-page')` is null). Product is fine: the swap is not visible. Fix hint (test only): read the ratio through `page.wait_for_function` or re-query after `wait_for_load_state`/after the POST response (`page.expect_response("**/api/annotations")`), or have the page not swap the node when the id arrives.

### F-013 [FE] low OPEN (found 2026-10-03, HEAD 0cd0726): literal rgba() in app.css instead of tokens
`app.css:707-709` (`.hl--yellow/mint/peach` rgba of #f4d35e/#a8d8c4/#fcab79 at 0.45), `:758` (`.pv-sheet::backdrop` rgba(24,29,38,.4)), `:773` (F-010, accepted). Values match the tokens, so no visible defect. Suggest `color-mix(in srgb, var(--color-yellow) 45%, transparent)` or add alpha tokens. Cosmetic, not blocking.

Wave G FE verification (HEAD 0cd0726): see docs/qa/v3-wave-G-fe.md. F-009 and F-011 verified fixed. No [BE] defects.

### v3 final pass closure (HEAD 42fbfc3, 2026-10-03)
- F-012 RESOLVED (commit f6bb184): `-k highlight_persists` passes 3 of 3 alone and in 14 of 15 full e2e runs.
- F-013 RESOLVED (commit 22781d9): `app.css` has no literal rgba() outside the `--shadow-button` token. F-010 stays ACCEPTED.
- F-014 [BE] RESOLVED (commit d6a6dfc): mock paper chat answers the three UI starter questions with `[p.1]` and refuses off-paper questions with "This paper does not cover that." Verified live on 8766 and by `tests/test_paper_chat.py`, `tests/test_config_llm.py`.
- F-009, F-011 RESOLVED (earlier). Focus-order fix 42fbfc3 verified at 390 px (failed and ready states).

### F-015 [FE?] low ACCEPTED (watch; found 2026-10-03, HEAD 42fbfc3): one unidentified e2e failure
`uv run pytest -q -m e2e` once ended `1 failed, 137 passed` (third of three back-to-back runs, right after two full runs). The failing test name was not captured (output was tailed). 12 further e2e runs on E2E_PORT=8770 and 3 more on 8766 were all green (138 passed). No repro, so no owner yet. If it recurs, run with `-x -rf` and record the test id; the F-012 pattern (async swap vs Playwright check) is the likely family.

All entries in this file are now RESOLVED or ACCEPTED.

### v4 fixes closure (HEAD 6a1912c, 2026-10-03): see docs/qa/v4-fixes.md
- F-016 [FE] RESOLVED (commit 325f7f3): text-layer drag selection no longer jumps or misaligns; 4 e2e tests green x3.
- F-017 [FE] RESOLVED (commit 57a8e71): previous results stay interactive during a new search; e2e green x3.
- F-018 [BE] RESOLVED (commit d323ef9): `build_query` sanitizes terms and OR-joins more than 4 terms; manual repro and unit tests green.
- F-019 [FE] RESOLVED (commit 6a1912c): preview opens on the Ask this paper tab (wide and narrow); e2e green x3.
- T066 woff2 MIME verified (10b7c4d). Full suite 532 passed x2, ruff check clean. No new failures.

### F-020 [FE] medium RESOLVED (verified 2026-10-04, fix c41d740, solo x12 = 12/12; found 94ed09e, T068): flaky `test_audit_sheet_header_is_one_row_on_canvas`
Repro (fails about 1 in 3): `MOCK_LLM=1 E2E_PORT=8766 uv run pytest -q tests/frontend/test_e2e_library.py::test_audit_sheet_header_is_one_row_on_canvas` repeated 12 times -> 4 failures. Parent 89bda09: 12 of 12 pass.
Actual: `assert abs((tabs.y + h/2) - (close.y + h/2)) < 12` fails with 110.2 (tabs y=908, close y=799.8 at 800x900): the two `bounding_box()` reads land mid-animation.
Cause: T068 changed `.pv-sheet[open]` animation `sheet-up` from `--dur-base` 200ms to `--dur-moderate` 240ms with `--ease-entrance`, so the sheet is still sliding when the test measures. Product behaviour is fine; the test races the animation.
Fix (FE, tests/frontend/test_e2e_library.py): wait for the slide to finish before measuring (e.g. `page.wait_for_function` on `getAnimations().length === 0` for `#pv-sheet`, or poll the box until stable), same pattern as F-012. Do not relax the 12px tolerance.

### F-021 [BE] medium RESOLVED (verified 2026-10-04, fix 8d1fe79: tests/test_api.py 37 pass, guard catches url(http), url(//), @import, leftover http(s)://, data: xmlns allowed; found 3f6cc23 T071): `tests/test_api.py::test_static_css_served` fails
Repro: `MOCK_LLM=1 uv run pytest -q tests/test_api.py::test_static_css_served`.
Actual: `assert ('http://' not in ...)` fails. `app.css` now holds `url("data:image/svg+xml,...xmlns='http://www.w3.org/2000/svg'...")` for the select chevron (T071, `.select, .pv-zoom`).
Cause: the guard greps the whole stylesheet for `http://`. The SVG xmlns is a namespace URI that the browser never fetches, and the data URI needs it to render. Product behaviour is correct; the guard is too broad.
Fix (test, tests/test_api.py): keep "no CDN, no external fonts" but test fetchable references, e.g. `re.findall(r"url\(\s*['\"]?(?:https?:)?//", css) == []` and no `@import`. Do not delete the guard. Alternative for FE: none (an SVG data URI without xmlns will not render).

### F-022 [FE] low RESOLVED (verified 2026-10-04, fix ae286b8: 40px at 1440/820/390, toolbar 249px, tab order unchanged; found d08cf70): Preview toolbar row-1 ghost actions are below the 40px control size
Repro: at 390, 820 and 1280, open a Preview; `#pv-export` is 88x34 and `#pv-external` is 142x28. DESIGN.md section 8.8 Toolbar: "Every control is 40px".
Cause: `.text-btn` min-height 32px with padding, and `.ext-link` `padding: 6px 4px; margin: -6px -4px`. T072's test checks only `#pv-controls`, so row 1 is not covered.
Fix (FE): give `#pv-export` and `#pv-external` `min-height: var(--control-md)` in the toolbar, then extend the 40px check to `.pv-toolbar`. Watch the 390px toolbar height (now 243px, limit 260).

### F-023 [FE] low RESOLVED (verified 2026-10-04, fix 14af76e: 36/36 in 12 solo runs, e2e x3 green; found 59debeb; test from T072): flaky `test_highlights_are_opaque_fills_with_multiply[chromium-mint]`
Repro: run `MOCK_LLM=1 E2E_PORT=8786 uv run pytest -q tests/frontend/test_e2e_design.py` repeatedly; failed 1 of 26 runs: `assert '' == '2px'` at test_e2e_design.py:358 (`hl.evaluate(...borderTopLeftRadius)` returned `''`).
Cause: an empty computed style means the `.hl` element was detached; the optimistic highlight is replaced by the saved one between `expect(hl).to_have_css` and `evaluate` (same family as F-012). Product behaviour is fine.
Fix (test): re-query `hls(page).first` right before each `evaluate`, or wait for the `#pv-hl-list li.hl-item` entry before checking the `.hl` radius.

### F-024 [FE] low OPEN (found 2026-10-04, v4 final pass; hygiene): stray directory `$S/` in the repo root
`ls -d '$S'` in the repo root shows a directory literally named `$S` (about 164 KB, holds `t72.png`). It is untracked and not committed. It came from a shell variable that did not expand during a UI check. Remove it before the next commit: `rm -r './$S'`.

### v4 audit items 1-6 (docs/design/v4-audit.md) [FE] RESOLVED (verified 2026-10-04, HEAD 04b299b)
Items 1 (rail count contrast 5.92:1 current, 6.38:1 hover) and 2 (forced colours underline only on the current nav link and tab) were the two blockers; both fixed. Items 3 to 6 (ghost back button, primary form submits, 12px confirm and Save spacing, centred not-saved Preview with h1 and title `Not in your Library`) also fixed. pytest 646 x2, e2e 239 x2, design e2e 93, detect unchanged. Details in final.md ("v4 audit fixes re-verify"). No new failures; F-024 stays open (stray `$S/` dir).
