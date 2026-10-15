# Research: v3 saved-papers library + in-app PDF preview

Date 2026-10-03. Tags: [V] fetched this session, [U] prior knowledge, [R] read from repo.
Repo facts [R]: starlette 1.7.0, fastapi 0.142.2, pypdf 6.19.0, playwright 1.63.0 already locked. `fetcher._download` already downloads the PDF during triage, then discards the bytes; no User-Agent set. `tests/frontend/test_static_assets.py` scans only `index.html`, `app.css`, `app.js`: no external URLs, and `app.js` must not contain `import(`, `importScripts`, `XMLHttpRequest`.

## 1. PDF rendering: vendored pdf.js vs native embed
- Native `<iframe>/<embed>/<object>`: browser plugin viewer. Page JS cannot read the selection or text layer, cannot overlay highlights, UI differs per browser. Cannot satisfy highlights + notes. [V] https://www.nutrient.io/blog/open-pdf-in-your-web-app/ (limited control), [U] cross-frame selection is opaque.
- pdf.js `pdfjs-dist` 6.3.289, Apache-2.0 [V] https://registry.npmjs.org/pdfjs-dist/latest . ES modules (`.mjs`). Same-origin worker is required, with an exactly matching lib/worker version [V] https://github.com/mozilla/pdf.js/wiki/Frequently-Asked-Questions .
- Files to vendor under `static/vendor/pdfjs/` [V sizes] https://unpkg.com/pdfjs-dist@6.3.289/build/?meta :
  - `build/pdf.min.mjs` 459 KB
  - `build/pdf.worker.min.mjs` 1.27 MB
  - `web/pdf_viewer.css` 164 KB (only the `.textLayer` part is needed; ~25 lines of own CSS can replace it)
  - `LICENSE` (Apache-2.0 notice)
  - Total ~1.7-1.9 MB. Skip `.map`, `cmaps/`, `standard_fonts/`, `wasm/`, `pdf_viewer.mjs`, `pdf.sandbox`. [U] cmaps/standard_fonts/wasm only matter for non-embedded CJK fonts, JBIG2/JPX images. arXiv LaTeX PDFs embed fonts. Add them later only if a test PDF renders wrong; then also set `cMapUrl`/`standardFontDataUrl`/`wasmUrl` to same-origin paths.
- Modern vs legacy: legacy build targets "Firefox ESR+, Chrome 125+, Safari 18+" [V FAQ]; legacy `pdf.min.mjs` 519 KB, worker 1.32 MB [V https://unpkg.com/pdfjs-dist@6.3.289/legacy/build/?meta ]. Rec: vendor the legacy build (single user, unknown browser; +~100 KB).
- Wiring (no CDN, passes guard): `GlobalWorkerOptions.workerSrc = "/static/vendor/pdfjs/pdf.worker.min.mjs"`. Load the lib with a static `import * as pdfjsLib from "./vendor/pdfjs/pdf.min.mjs"` in a new `viewer.js` loaded by `<script type="module" src="static/viewer.js">`. Do NOT use `import()` in `app.js` (guard). Extend the guard to scan `viewer.js` but exempt `static/vendor/` (vendored code has `import(` and URL strings in comments); add a guard that `vendor/pdfjs/LICENSE` exists.
- Gotcha [U]: module scripts need a JS MIME type. Register `mimetypes.add_type("text/javascript", ".mjs")` at app startup so StaticFiles serves `.mjs` correctly on every OS.
- Render per page: `getDocument({url})`, `page.getViewport({scale})`, canvas via `page.render`, text layer via `new TextLayer({textContentSource: await page.getTextContent(), container, viewport}).render()`, set `--total-scale-factor` on the container to the scale [V] https://github.com/mozilla/pdf.js/issues/18206 (TextLayer replaces deprecated `renderTextLayer`). Render lazily with IntersectionObserver (visible pages only), one canvas per page.
- Rec: vendored pdf.js legacy build, low-level API (canvas + TextLayer), own thin viewer. Do not embed the full pdf.js viewer app (heavy, CDN/CORS assumptions, own toolbar clashes with DESIGN.md).

## 2. Highlights + notes
- pdf.js built-in highlight editor (`AnnotationEditorType.HIGHLIGHT`, since 4.x) needs full `PDFViewer` + EventBus + `pdf_viewer.css`, and persists only via `pdfDocument.saveDocument()` into the PDF bytes; no per-annotation events [V] https://www.nutrient.io/blog/pdfjs-annotation-editor-layer/ . Poor fit for DB-stored notes. Reject.
- Hypothesis anchors with Range + TextPosition + TextQuote(prefix/suffix 32 chars) selectors and fuzzy fallback [V] https://web.hypothes.is/blog/fuzzy-anchoring/ . That machinery exists because HTML changes. Our stored PDF is immutable, so geometry is stable and robust.
- Rec: geometry primary, quote secondary.
  - On `mouseup` in the text layer: `sel.getRangeAt(0).getClientRects()`; subtract the page wrapper's `getBoundingClientRect()`; divide by wrapper width/height. Store `[[x,y,w,h],...]` as fractions 0..1, with 1-based `page`. Merge rects on the same line.
  - Store `quote` (selected text, <=500 chars), optional `prefix`/`suffix` (~32 chars) for display, find-in-text re-anchor and "jump to".
  - Re-render on zoom or resize: for each page, clear the highlight layer and draw `div`s at `left = x * wrapper.width` etc. Fractions make zoom free; no re-anchoring. Highlight layer sits above the canvas, `pointer-events:none`, `mix-blend-mode:multiply`; click handling via a small separate hit layer or the annotation list.
  - Render at rotation 0 only (PDF `/Rotate` pages: fractions still valid relative to the rendered viewport as long as the same rotation is always used).
- Schema sketch (new tables, `CREATE TABLE IF NOT EXISTS`, matches `db.py` style):
  ```sql
  CREATE TABLE paper_files (paper_id TEXT PRIMARY KEY REFERENCES papers(id),
    path TEXT NOT NULL, bytes INTEGER, sha256 TEXT, pages INTEGER,
    status TEXT NOT NULL CHECK (status IN ('ok','failed')), error TEXT, fetched_at TEXT NOT NULL);
  CREATE TABLE paper_pages (paper_id TEXT NOT NULL REFERENCES papers(id),
    page INTEGER NOT NULL, text TEXT NOT NULL, PRIMARY KEY (paper_id, page));
  CREATE TABLE annotations (id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id TEXT NOT NULL REFERENCES papers(id), page INTEGER NOT NULL,
    rects TEXT NOT NULL,            -- JSON [[x,y,w,h]] fractions of page box
    quote TEXT NOT NULL, prefix TEXT, suffix TEXT,
    color TEXT NOT NULL DEFAULT 'yellow', note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
  CREATE TABLE library (paper_id TEXT PRIMARY KEY REFERENCES papers(id), saved_at TEXT NOT NULL);
  ```
  API: `POST/DELETE /api/library/{id}`, `GET /api/library`, `GET /api/papers/{id}/pdf`, `GET|POST /api/papers/{id}/annotations`, `PATCH|DELETE /api/annotations/{id}`. Estimate ~250-350 lines of JS for select -> rects -> save -> redraw -> list.

## 3. Viewer extras, ranked value/cost
1. Zoom (fit-width, +/-): low cost, high value; falls out of the fractions design.
2. Page nav (prev/next, "page N of M" input, keyboard): low, high.
3. Annotation list sidebar with jump-to (scroll page into view, flash highlight) and edit/delete note: low-med, high. This is the main way to use notes.
4. Export notes as Markdown (`> quote (p.N)` + note, per paper, built client-side from the annotation list, download via Blob): low, med-high.
5. Find-in-paper: med. Cheap version: search `paper_pages.text` server-side or the loaded `getTextContent()` per page, list hits with page, jump. Skip in-page match painting in v3 (pdf.js `PDFFindController` needs the full viewer stack).
6. Highlight colours (3-4): low, med. Include.
7. Open-in-arXiv / download link: trivial, include.
8. Skip: thumbnails, print, outline tree, rotation, dark-mode page inversion, freehand ink.

## 4. PDF storage and serving
- Size: most arXiv PDFs under ~8 MB, some ML papers over 100 MB [V, weak] https://news.ycombinator.com/item?id=38725953 and arXiv size notes; [U] typical 0.5-5 MB.
- SQLite guidance: blobs <100 KB in DB, >100 KB as files are faster to read [V] https://www.sqlite.org/intern-v-extern-blob.html . PDFs are well above 100 KB.
- Rec: files on disk, `DATA_DIR/pdfs/<safe-name>.pdf` (env `PAPER_TRIAGE_DATA_DIR`, default beside the DB), path + sha256 + bytes + page count in `paper_files`. Safe name = sha256 hex or id with `/` -> `_` (old-style ids `math.GT/0107001` contain a slash); resolve only from the DB row, never from request path (no traversal). Cap download size (e.g. 50 MB; stream and abort); keep `.gitignore` for the data dir. Write to a temp file, then `os.replace`.
- Serving: `FileResponse(path, media_type="application/pdf", content_disposition_type="inline")`. Starlette 0.39.0 added HTTP Range support to `FileResponse` [V] https://github.com/encode/starlette/releases/tag/0.39.0 ; locked starlette is 1.7.0 [R]. pdf.js uses Range when the server supports it and falls back to full download [V FAQ]; local single-user files are small, so Range is nice-to-have, not required. Same origin, so no CORS. Add `Cache-Control: private, max-age=3600`.
- ToS: arXiv forbids hosting/redistributing PDFs; personal local storage for research is allowed ("retrieve and store e-print content for personal or research purposes") [V] https://info.arxiv.org/help/api/tou.html . Fine for local single user; note in README: do not deploy publicly.

## 5. Polite arXiv PDF fetching
- Limit: 1 request / 3 s, one connection, all machines combined [V tou.html]. Reuse the existing process-wide `Throttle(3.0)` for PDF GETs too (already done in `_add_fulltext`); one download at a time.
- Hosts: arXiv says harvesting programs should use `export.arxiv.org` [V] https://info.arxiv.org/help/bulk_data.html (search snippet); robots.txt allows `/pdf/` for all agents but states "Indiscriminate automated downloads from this site are not permitted" and sets generic crawl-delay 15 s [V] https://arxiv.org/robots.txt . Rec: use `https://export.arxiv.org/pdf/<id>v<n>`; when Atom gives a `title="pdf"` link, rewrite host to `export.arxiv.org`; fall back to `arxiv.org/pdf/...` on 404/5xx. Only fetch on user action ("Save to library" or first "Open PDF"), never bulk. Triage already downloads for the top-N; reuse those bytes instead of a second GET.
- Client: set `User-Agent: paper-triage/<ver> (personal research tool; mailto:<env CONTACT_EMAIL>)` [U convention]. `follow_redirects=True` already set [R]. Timeout: connect 10 s, read 60 s for PDFs (current `TIMEOUT=20` is OK for metadata). Validate `%PDF-` magic and `content-type`; reject HTML error pages.
- Failure: keep the paper row (metadata stays), write `paper_files.status='failed'` + `error`; library shows "PDF unavailable - Retry" and an "Open on arXiv" link. Retry only by user click. Honour `Retry-After` on 429/503; no automatic retry loops.

## 6. Per-paper chat on full text
- Extraction: keep pypdf [R]: BSD-3, pure Python, `page.extract_text()` per page gives page numbers for free (current `extract_text` joins pages: add `extract_pages(bytes) -> list[str]`). pdfminer.six is MIT, pure Python, slower, better layout, `LAParams`/`extract_pages` also page-aware [V] https://pypi.org/pypi/pdfminer.six/json . PyMuPDF is AGPL-3, fastest, page-aware [V] https://pymupdf.readthedocs.io/en/latest/about.html . Rec: pypdf; swap-point `extract.py` stays. Store per-page text in `paper_pages` at save/fetch time (not lazily), as page text is cheap.
- Context: a typical arXiv paper ~8-15k words, well under the 200k window [U]; whole-text beats chunk retrieval (no recall misses, no new deps). Rec: whole paper, pages tagged `<page n="3">...</page>`, references kept (cite-checking) or trimmed above a char cap; if over cap (~600k chars) fall back to first-N-pages + FTS5 keyword page selection [U].
- Caching: cache_control on the stable prefix (system + paper), then each turn adds history. Min cacheable 512-1,024 tokens depending on model; 5-minute TTL default, writes 1.25x, reads 0.1x; automatic request-level `cache_control` moves the breakpoint as the chat grows; check `usage.cache_read_input_tokens` [V] https://platform.claude.com/docs/en/build-with-claude/prompt-caching . Paper context stays byte-identical across turns (no timestamps).
- Lazy init: no LLM call or context build when the paper opens; the first message builds the context from `paper_pages`. Persist turns per paper (`paper_id` column on chat turns, or new `paper_chat_turns`); optionally `max_tokens=0` pre-warm on open [V same page], skip in v3.
- Page citations: instruct the model to cite `[p.N]` (and `[arXiv:ID]` for consistency with `chat.py`); post-validate N in 1..pages, drop unknown (same pattern as existing id validation [R]). Native alternative: a `document` block with plain/custom content (one block per page) and `citations.enabled` returns `content_block_location` indices = pages, with `cited_text` [V] https://platform.claude.com/docs/en/build-with-claude/citations ; incompatible with structured outputs, fine for free-text chat. Rec: start with `[p.N]` tags (simpler to mock, one code path); UI turns `[p.N]` into a jump-to-page link in the viewer.
- Refusal: reuse the existing `NOT_IN_STORED_PAPERS` sentinel, scoped to this paper; refuse without an LLM call when no text exists (PDF failed, abstract-only).

## 7. Offline test strategy
- Fixture: `src/paper_triage/fixtures/sample.pdf` exists [R]; ensure it has >=2 pages, known words per page (e.g. "alpha" p1, "beta" p2) for page-citation + selection tests. Keep it <50 KB.
- Backend: `net._mock_handler` already serves it for `/pdf/<id>` and `export.arxiv.org` (`host.endswith("arxiv.org")`) [R]; add a failure id (reuse `INVALID_PDF_ID`) and a 503 id. Tests: download -> file on disk + `paper_files` row; Range request returns 206; failed fetch keeps metadata; `extract_pages` page count/text; annotation CRUD; path-safety for old-style ids. `MOCK_LLM=1` per-paper chat returns canned `[p.1]` answer; test page-citation validation drops `[p.99]`.
- Playwright (already in project, `tests/frontend/test_e2e_browser.py` [R], FE port 8765): open the viewer, `expect(page.locator("canvas")).to_have_count(>=1)`, wait for `.textLayer span` containing "alpha", select via `locator.select_text()` or `page.mouse` drag, click "Highlight", assert a `.hl` div exists and the DB row has fractions in 0..1; zoom, assert highlight `width` scaled proportionally; reload and assert persistence; assert no network requests to non-localhost (`page.on("request")`). Pdf.js workers load same-origin, so no extra Playwright config.
- Static guard: add `viewer.js` to scanned files, exempt `vendor/`, assert vendored files + LICENSE exist and `pdf.min.mjs`/worker versions match (pdf.js throws on version mismatch).

## Recommendations
- Vendor pdfjs-dist 6.3.289 legacy build (`pdf.min.mjs`, `pdf.worker.min.mjs`, LICENSE, optionally `pdf_viewer.css`) under `static/vendor/pdfjs/`; build a thin canvas + TextLayer viewer in `viewer.js` (static ES import, same-origin worker). No iframe/embed; no pdf.js built-in annotation editor.
- Register `.mjs` MIME type at startup; extend the static guard to `viewer.js`, exempt `vendor/`.
- Highlights: store page + line rects as fractions of the page box + quote/prefix/suffix; redraw from fractions on zoom. Tables: `library`, `paper_files`, `paper_pages`, `annotations`.
- v3 viewer features, in order: zoom, page nav, annotation list with jump/edit/delete, colours, Markdown export, simple find-in-paper. Skip the rest.
- Store PDFs as files under a data dir (path in DB, sha256, size cap, atomic write); serve with `FileResponse` inline (Range works in starlette 1.7.0).
- Fetch via `export.arxiv.org`, shared 3 s throttle, explicit User-Agent, `%PDF-` check, only on user action; reuse bytes already downloaded in triage; on failure keep metadata, show retry.
- Keep pypdf; add per-page extraction; per-paper chat sends whole paper with `<page n>` tags, prompt-cached prefix, lazy first-message init, `[p.N]` citations validated server-side, existing sentinel refusal.
- Tests: multi-page sample.pdf with known words, extend net mock with failure ids, Playwright canvas/text-layer/highlight/zoom/persistence, no external-request assertion.

## Clarification questions
1. Should "library" mean explicit "Save" or every triaged paper auto-saved?
2. Are non-arXiv direct PDF URLs saved to the library too (no throttle contract)?
3. Max PDF size and total data-dir budget?
4. Is deleting a paper from the library also deleting its file and annotations?
5. Which browsers must be supported (decides legacy vs modern pdf.js)?
6. Should highlights/notes feed into per-paper chat context?

DONE
