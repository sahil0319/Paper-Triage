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

### F-020 [FE] medium OPEN (found 2026-10-04, HEAD 94ed09e, T068): flaky `test_audit_sheet_header_is_one_row_on_canvas`
Repro (fails about 1 in 3): `MOCK_LLM=1 E2E_PORT=8766 uv run pytest -q tests/frontend/test_e2e_library.py::test_audit_sheet_header_is_one_row_on_canvas` repeated 12 times -> 4 failures. Parent 89bda09: 12 of 12 pass.
Actual: `assert abs((tabs.y + h/2) - (close.y + h/2)) < 12` fails with 110.2 (tabs y=908, close y=799.8 at 800x900): the two `bounding_box()` reads land mid-animation.
Cause: T068 changed `.pv-sheet[open]` animation `sheet-up` from `--dur-base` 200ms to `--dur-moderate` 240ms with `--ease-entrance`, so the sheet is still sliding when the test measures. Product behaviour is fine; the test races the animation.
Fix (FE, tests/frontend/test_e2e_library.py): wait for the slide to finish before measuring (e.g. `page.wait_for_function` on `getAnimations().length === 0` for `#pv-sheet`, or poll the box until stable), same pattern as F-012. Do not relax the 12px tolerance.
