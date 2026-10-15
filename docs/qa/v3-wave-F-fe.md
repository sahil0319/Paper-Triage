# v3 Wave F FE verification (T052 be3cbf1, T053 9b6ea8a, T054 c72e508, T055 eb16174, T056 a2bf9e3)

Date 2026-10-03. Tested in an isolated worktree at a2bf9e3 (`.local/wt-feF`, `uv sync --offline` worked; removed afterwards). MOCK_LLM=1, offline. Verdict: PASS with one medium [FE] defect (F-009) and two low [FE] notes (F-010, F-011). No [BE] defects.

## Automated
- `uv run pytest -q`: 406 passed (43 s). `ruff check .`: clean.
- `pytest -q -m e2e` x3: 47 passed each (28 s), stable.
- `tests/frontend/test_static_assets.py`: 16 passed. Own grep (vendor/ exempt): no `import(`, no `@import`, no external URL except the two `https://arxiv.org/...` display-link fallbacks in `app.js:228-229` (href strings, never fetched).
- `npx impeccable detect src/paper_triage/static`: 2 findings, both the known false positives (cramped-padding `.intro`, flat-type-hierarchy).
- app.css token adherence: no hex literals outside `:root`; one literal `rgba()` at `app.css:664` (F-010). Reduced-motion block covers `.pdf-page.is-flash`; `forced-colors` block present.
- Vendor: `vendor/pdfjs/{pdf.min.mjs,pdf.worker.min.mjs,LICENSE,VERSION}` present, served as `text/javascript`, VERSION names `pdfjs-dist 6.3.289`.

## Own Playwright (port 8766, real API, MOCK_LLM=1, scratch DB/data dir, Chromium)
Routes and nav (L1, L2)
- Nav links `Triage`/`Library`, `aria-current` follows route (Preview keeps Library current), count hidden at 0, shows 10 after saves, hides after last unsave.
- `#/library`: title `Library · Paper Triage`, h1 focused, status `Library.`; triage hidden. Back returns to triage with the same 10 rows and no new `POST /api/triage`; Forward returns to Library. Deep link, unknown paper id (`This paper is not in your Library.` + `Go to Library`), params route and bogus hash all behave.
- Library scroll restore: scrolled 1652 px, opened preview, Back and the in-app `Library` button both restore scrollY (1652) and focus that paper's `Open preview`; hash filters restored (`#/library?q=attn&dir=network`).

Save toggle (L3-L6)
- States: `Save` -> `Saving…` (aria-disabled, aria-busy, pressed false, double click = one POST) -> `Saved` (pressed true); `Removing…` then `Save`. Width constant (124 px in all states). Announcements `Saved to Library.` / `Removed from Library.`.
- Unsave always opens `[data-confirm=unsave]` (group, label `Confirm removal`), focus on `Keep`, Esc = Keep with focus back on `Saved` and no DELETE. Copy `...saved PDF.` and with 2 annotations `...saved PDF and 2 highlights with their notes.`
- Errors: `Could not save. disk full` / `Could not remove from Library. boom` as `role=alert`, focus stays, retry clears the line.
- Saved flag on re-search and after reload. POST body `{paper_id, topic}`: topic is the server's response topic verbatim (`"  Diffusion   MODELS  "` -> `"Diffusion MODELS"`, whitespace collapsed, case kept, per contract); item runs send `""`.
- Failed rows without Save: covered by e2e stub (real mock cannot produce a `status: failed` row from item runs).

Viewer (L15-L17, L21)
- 2401.00001: 3 `section.pdf-page` with aria-label, canvas/text layer/hl layer, canvas painted; first page canvas + text at 0.16 s (limit 2 s). Text layer has page-1 text.
- Zoom: fit-width default (1248 px in 1280 well), 200% = 1632 px with canvas redrawn, zoom out steps 200->150, zoom in disabled at max, fit page <= well height.
- Page nav: next, out-of-range 99 -> 3, 0 -> 1 on blur, ends disabled; scroll (wheel and scrollTop) updates the page number; keys `n p + - 0` inside the region; PageDown scrolls the region.
- States: 2401.00005 failed -> `This PDF could not be downloaded.` + `Not a PDF.` + `Try again` + `Open the source page`; pending (routed list) -> Downloading card, note, open critique, then `PDF ready.` and pages; bad bytes -> `This PDF could not be displayed.` with `Open PDF in new tab`; `Opening PDF…` after 300 ms. Retry POST sent (but see F-009).
- Zero requests to non-local hosts in every run.

Find (L24, R18)
- `f` in the region opens the row and focuses the input; `Quartzite` -> `1 match on 1 page`, result `Page 2: …Quartzite…` (match span weight 500); activation jumps to page 2 and flashes the page outline (static outline under reduced motion); nonsense -> `No matches.`; Esc closes, focus on Find button.

A11y
- Preview tab order: Back, Open PDF in new tab, prev, page input, next, zoom out, zoom, zoom in, Find, PDF region. Library order: Open preview, arXiv link, PDF link, critique, next row. `#status` role=status, aria-live=polite; route changes announce. Nav links 64 px, icon buttons 40 px, focus ring 2 px solid. `aria-keyshortcuts` set (f, p, n, +, -). Skip links per view.
- Reduced motion: no running animations on the page; flash outline static. 800 px viewport: find row full width, no horizontal overflow, toolbar inside viewport.
- F-006..F-008 chat reset: transcript survives view switch; load-more clears it with note and status sentence; new search announces reset; Ask enabled.

## Findings
- F-009 [FE] medium: Retry on a failed PDF sticks on "Downloading the PDF…" when it fails again (stale cache vs `lib.sig`). Repro in docs/qa/failures.md.
- F-010 [FE] low ACCEPTED (deviation): text-layer selection uses info-border at 30% alpha; approved by router during Wave F because cream hides the canvas text.
- F-011 [FE] low: focus stays on the find result after activation (L19 says viewer region).
- Not in Wave F scope, not logged: Library filter bar, directories, rows' Move/Remove (T060-T063); the hash filters are kept but not applied yet.

## Cleanup
Server on 8766 killed, port free; worktree `.local/wt-feF` removed; scripts in the session scratchpad. No src/ or tests/ edits.
