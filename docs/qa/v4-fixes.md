# v4 fix verification: F-016..F-019 + T066 (HEAD 6a1912c, 2026-10-03)

Range 7b43af1..6a1912c. Run with MOCK_LLM=1. Working tree also held in-progress T067 (vendored Plex fonts, test_static_assets.py edits); no failure traced to it.

## Results
- Full pytest run 1: 532 passed (81 s). Run 2: 532 passed (79 s). No flakes, no skips.
- `ruff check .`: all checks passed. (`ruff format --check` reports 28 files; the project gates on `ruff check` only, so not logged.)
- F-016/F-019 e2e tests solo x3 (`test_e2e_library.py -k "drag_across_two or one_column or below_the_last or text_layer_matches or opens_on_the_chat_panel or narrow_preview_keeps or new_paper_opens_on"`): 7 passed, 3 of 3 runs.
- F-017 e2e solo x3 (`test_e2e_browser.py -k stay_interactive`): passed, 3 of 3 runs.
- Live server on 8766 (MOCK_LLM): `/` 200 html; `/app.js`, `/viewer.js`, `/vendor/pdfjs/pdf.min.mjs` 200 text/javascript; `/app.css` 200 text/css; `/vendor/fonts/plex-sans-latin-400.woff2` 200 `font/woff2`; `POST /api/triage {"query": ...}` returns ranked results. Server killed, port free.
- T066: woff2 GET test no longer skips (T067 fonts present) and passes.
- `impeccable detect`: only advisory design-system-color/radius notes (8) against the new DESIGN.md (Skip link, Triage button, chat aside). Expected until the v4 restyle tasks (T068+) land; not a v3 fix regression.

## F-018 manual repro (`fetcher.build_query`)
- `transformers` -> `all:transformers`
- `graph neural networks` -> `all:graph AND all:neural AND all:networks`
- `one two three four` -> 4 terms, AND-joined
- `a b c d e` (5 terms) -> OR-joined
- `foo "bar" (baz): qux & x+y` -> `all:foo AND all:bar AND all:baz AND all:qux` (punctuation stripped, 1-letter tokens dropped)
- `LLM; agents/RL` -> `all:llm AND all:"agents rl"`
- `ti:attention AND all:x` -> `all:"ti attention"` (field prefix defused, AND stop word dropped)
- blank -> `""`
- A single 200-character token passes through unbounded (low, URL-length only; no arXiv failure expected). Not logged.

## Status
- F-016 [FE] RESOLVED (325f7f3): 4 e2e tests green x3 plus two full runs.
- F-017 [FE] RESOLVED (57a8e71): e2e green x3.
- F-018 [BE] RESOLVED (d323ef9): unit tests in full suite green; manual repro above. Live arXiv not exercised (offline rule).
- F-019 [FE] RESOLVED (6a1912c): wide and narrow e2e green x3.
- T066 [BE] verified (10b7c4d).
- No new failures. Caveat: F-016 drag behavior was verified in headless Chromium against a synthetic two-column PDF; real-PDF feel (pdf.js fonts) is not covered.

## Notes
- `uv run` recreated `.venv` on first call because VIRTUAL_ENV pointed at a mamba env. Same `.venv` path afterwards; no source change.
