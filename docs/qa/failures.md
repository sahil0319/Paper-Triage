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
