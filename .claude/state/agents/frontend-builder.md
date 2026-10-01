
## Wave A (T017, T021 ui, T020)
- T017 cb8e547: kept prior app.js; fixed h() array-child bug (ul lists threw), added authors line. Verified vs real mock server via fake-DOM harness (scratchpad, not in git).
- T021 ui 0c025df: load /api/status (mock label, model) + /api/papers (stored list, "Showing N stored papers..."). Ticked (api commit ca2e161 exists).
- T020 chat UI: log role=log, [id] markers -> links only for validated citations, dropped markers stripped, "Cited papers" list w/ titles, refusal = calm bordered block "Not covered by your papers", errors inline. Cites to papers not in current list render as plain text (chat store spans topics).
- No real-browser visual check (no browser tool). detect: tight-leading on .lead (21px/1.19, from T016) -> T023.
- Next: T023 (polish, a11y, visual pass in a browser).
