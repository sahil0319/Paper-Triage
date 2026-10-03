# Research: Paper Triage Assistant

Source notes: docs/research/paper-triage.md (arXiv, PDF, prompts, chat) + claude-api skill
(cached 2026-09-25). Each entry: Decision / Rationale / Alternatives.

## R1 arXiv access

- **Decision**: `httpx` GET `http://export.arxiv.org/api/query` (`search_query=all:<terms>` or
  `id_list=`), `sortBy=relevance`, `max_results<=20`; parse Atom with stdlib `xml.etree`.
  Process-wide throttle: min 3.0 s between arXiv requests (lock + last-call time; clock and
  sleep injectable). Raw responses cached in SQLite `arxiv_cache` keyed by normalized query.
  Ids normalized: strip `http(s)://arxiv.org/abs/` prefix and `vN` suffix; version kept in a
  column. PDF from Atom `<link title="pdf">`.
- **Rationale**: arXiv ToU (1 req/3 s); stdlib parser avoids a dep.
- **Alternatives**: `feedparser` (extra dep), `arxiv` pip package (hides throttle/cache).

## R2 PDF text extraction

- **Decision**: `pypdf` behind `extract_text(pdf_bytes) -> str` in `extract.py`. Truncate at a
  line matching `^references$` (case-insensitive) when found after 50% of text; cap 40,000 chars
  to LLM. Any exception or <500 chars extracted -> basis `abstract`.
- **Rationale**: BSD license, pure Python; one swap point for PyMuPDF (AGPL, not bundled).
- **Alternatives**: PyMuPDF (faster, AGPL), pdfminer.six (slow).

## R3 Non-arXiv PDF URLs

- **Decision**: any `http(s)` URL not on arxiv.org is a direct PDF. id = `pdf:` +
  `sha256(url).hexdigest()[:12]`. Title from PDF metadata `/Title`, else URL basename. Abstract
  = first 1,500 chars of extracted text. No throttle beyond one request at a time; 20 s timeout.
- **Rationale**: clarified in spec; stable deterministic id.

## R4 LLM client and structured output

- **Decision**: `llm.py` exposes `LLMClient` protocol with `parse(system, user, schema) -> BaseModel`
  and `text(system, user) -> str`. `AnthropicClient` uses `client.messages.parse(model=...,
  max_tokens=16000, system=..., messages=[...], output_format=Schema, output_config={"effort":
  "low"})` -> `.parsed_output`; chat uses `messages.create` text. No `temperature` (rejected by
  current models). `stop_reason == "refusal"` -> raises `LLMRefusal` -> item marked failed.
  Pydantic validation error -> one retry -> item failed. `MockClient` returns deterministic
  instances of the requested schema keyed by sha256 of the `<paper id=..>` in the prompt; chat
  mock cites the first stored id in context, or returns the refusal sentinel if the question
  contains "out of scope" or no ids are in context. `get_client()` picks mock when `MOCK_LLM=1`.
- **Model**: `ANTHROPIC_MODEL` env, documented default `claude-opus-5-5` in `config.py` only.
- **Rationale**: one wrapper = one mock point (constitution II); SDK helper validates schema.
- **Alternatives**: one combined call per paper (cheaper, but product requires separate
  Summarizer/Critic/Ranker modules + prompt files); server-side refusal `fallbacks` beta
  (deferred: adds beta surface; refusal handled as failed item).

## R5 Prompts

- **Decision**: `src/paper_triage/prompts/{summarizer,critic,ranker,chat}.md`, loaded at call
  time. Paper content wrapped `<paper id="..." basis="fulltext|abstract">..</paper>`. Critic:
  "only claims supported by supplied text; write 'not stated' rather than guess". Ranker gets the
  topic, summary and abstract, rubric 0-2/3-5/6-8/9-10; rank clamped 0-10 in code. With no topic
  (id-only input), ranker rates overall reading priority and says so in the reason.
- **Rationale**: research §3; honest-critique principle V.

## R6 Grounded chat

- **v2 note**: the context source is superseded by R10 (current result set via `paper_ids`);
  the citation format, sentinel and validation below still apply.
- **Decision**: context stuffing: top 20 stored papers by latest rank, each as `<paper id=..>`
  with title, abstract, summary, critique. Instruction: cite as `[<id>]` using the exact id;
  if unanswerable reply exactly `NOT_IN_STORED_PAPERS` + one sentence. Server: regex
  `\[([^\[\]\s]+)\]`, keep ids in store, list unknown in `dropped_citations` and strip them
  from the answer text. Answer with zero valid citations and no sentinel -> treated as refusal.
  Empty store -> refusal without LLM call.
- **Rationale**: research §4; Citations API is not needed for a small corpus and keeps the
  mock simple.
- **Alternatives**: Citations API document blocks (richer spans, harder to mock); FTS5 retrieval
  (not needed at <=20 papers).

## R7 Mock network

- **Decision**: fetcher takes an `httpx.Client` + `Throttle` from `net.make_http()`; under
  `MOCK_LLM=1` it is an `httpx.MockTransport` client with a 0 s throttle serving bundled fixtures (`src/paper_triage/fixtures/`: one Atom feed of
  5 papers, one tiny PDF). Tests use the same transport.
- **Rationale**: FR-011 requires full flow offline with no key.

## R8 Web layer

- **Decision**: FastAPI, synchronous triage request (<=20 papers; sequential), static files
  served from `src/paper_triage/static/`. Run: `uv run uvicorn paper_triage.app:app`.
- **Rationale**: no job queue (constitution IV).

## R9 v2: load-more paging

- **Decision**: `offset` on `POST /api/triage` maps to arXiv API `start`; `has_more` from the
  feed's `opensearch:totalResults` (fallback: full page). Cache key gains `:<offset>`. Mock feed
  grows to 15 entries and honours `start`, so 10 + 5 exhausts it deterministically.
- **Rationale**: arXiv API supports `start`/`max_results` natively; no server-side session.
- **Alternatives**: server-side search sessions with stored cursors (state, more code);
  "exclude ids" parameter (arXiv cannot filter by id list).

## R10 v2: chat scope

- **Decision**: client sends `paper_ids` (current result set, max 50) with each question; the
  server builds context only from those stored papers and validates citations against them.
  MockClient answers only on id or content-word overlap with the context papers.
- **Rationale**: the result set already lives in the page; no session table needed. The cap of
  50 bounds the prompt (about 50 papers x short summary/critique/abstract).
- **Alternatives**: `search_id` persisted per run (new table, more API); topic-based scope
  (fails for ID/URL searches and repeated topics).

## R11 v2: searching indicator

- **Decision**: client-only working card (brief D14-D18): rotating verbs + elapsed time, no
  progress claims, shown 300 ms after submit, gone on response/error.
- **Rationale**: triage is one synchronous request; a progress endpoint would need background
  jobs (constitution IV). Honest activity beats fake progress.

## R12 v2: browser e2e

- **Decision**: pytest-playwright (dev only) + chromium. A test harness in `tests/` runs uvicorn
  in a thread on `127.0.0.1:${E2E_PORT:-8766}` with `MOCK_LLM=1` and a temp DB, wraps the app
  in a test-only ASGI middleware that can delay `POST /api/triage` (so the indicator is
  observable), and aborts and records any non-local browser request. Tests marked `e2e`; skipped
  with a clear reason only if chromium is not installed.
- **Rationale**: real browser proves indicator, links, load-more and chat scope; mock transport
  already makes the fetcher deterministic offline (`net.make_http(mock=True)`).
- **Alternatives**: Selenium (heavier), JS test runner (adds Node toolchain), product-side
  latency env var (test concern leaking into product code).

## v3 (2026-10-03): Library, PDF preview, paper chat

Source research: `docs/research/v3-library-preview.md` (sections 1-7). Design: brief
`docs/design/v3-library-brief.md` Rev 2. Decisions below override the research doc where they
differ (user decisions relayed 2026-10-03).

## R13 v3: PDF rendering

- **Decision**: vendor `pdfjs-dist` 6.3.289 **modern** build (`build/pdf.min.mjs`,
  `build/pdf.worker.min.mjs`, `LICENSE`, plus a `VERSION` file with source URLs and sha256)
  under `src/paper_triage/static/vendor/pdfjs/`. Thin own viewer `static/viewer.js` (ES module,
  static `import` of the vendored lib): one canvas + `TextLayer` per page, pages rendered lazily
  near the viewport, worker same-origin (`/vendor/pdfjs/pdf.worker.min.mjs`; static files are
  mounted at `/`). No `pdf_viewer.css` (about 25 lines of own `.textLayer` CSS instead), no
  cmaps/standard_fonts/wasm in v3. The server registers `.mjs` as `text/javascript`.
- **Rationale**: highlights need page JS access to the text layer; native `<embed>` cannot.
  User targets current evergreen browsers, so the legacy build is not needed. Constitution
  2.0.0 I allows vendored libraries (no CDN, no framework, no build step).
- **Alternatives**: native iframe/embed (no highlight access); full pdf.js viewer app (heavy,
  own toolbar clashes with DESIGN.md); pdf.js annotation editor (persists into PDF bytes only).

## R14 v3: PDF storage, download and serving

- **Decision**: files under `PAPER_TRIAGE_DATA_DIR` (default `./paper_triage_data`, git-ignored)
  in `pdfs/<sha256(paper_id)>.pdf`; the path is read only from the DB row (no request path
  traversal). Written to a temp file, then `os.replace`. Download starts on save as a FastAPI
  `BackgroundTask` (in-process, no queue; TestClient runs it synchronously, which keeps tests
  deterministic), streaming with a 50 MB cap, connect 10 s / read 60 s timeouts, `%PDF-` magic
  check. arXiv: `https://export.arxiv.org/pdf/<id>` with fallback to `https://arxiv.org/pdf/<id>`
  on 404/5xx, through the shared 3 s `Throttle`; direct PDF URLs: same path, no throttle.
  Network happens outside the DB lock; status writes take the lock. On startup, rows still
  `pending` become `failed` ("Download interrupted. Try again."). Retry only by user action.
  Served by `FileResponse` (inline, `application/pdf`, Range supported by starlette 1.7.0).
  Page count read with pypdf at download time (no text extraction).
- **Rationale**: SQLite guidance prefers external files for blobs over 100 KB; BackgroundTasks
  needs no new dependency; arXiv ToS allows personal storage, not redistribution.
- **Alternatives**: BLOBs in SQLite (slower, bigger DB); thread pool or queue (constitution IV);
  reuse triage bytes (would require keeping PDFs for unsaved papers; skipped).

## R15 v3: annotations

- **Decision**: geometry-first anchors: 1-based page + rects as fractions (0..1) of the rendered
  page box + quote (<= 500 chars) + optional prefix/suffix (<= 64 chars). Stored in SQLite
  `annotations`; redraw from fractions at any zoom. Three colors: yellow, mint, peach. Kinds:
  `highlight` (rects + quote) and `note` (page note, no rects). Ordering by page, then `top`
  (smallest rect y), then id.
- **Rationale**: stored PDFs are immutable, so geometry is stable; fractions make zoom free.
- **Alternatives**: Hypothesis-style fuzzy text anchoring (built for changing HTML).

## R16 v3: per-paper chat

- **Decision**: new runtime agent `paper_chat.py` + `prompts/paper_chat.md`. Lazy: on the first
  question for a paper with no stored page text, extract per-page text with pypdf
  (`extract.extract_pages`) into `paper_pages`; nothing happens on open. Context = whole paper
  as `<page n="N">` blocks, capped at 300,000 characters (later pages dropped, prompt told).
  The page sends the in-page transcript (last 6 turns) as `history`; the server stores no
  turns. Citations `[p.N]` validated against the page count; invalid go to `dropped_pages`.
  Sentinel `NOT_IN_STORED_PAPERS` or zero valid page citations -> refusal. PDF not ready or no
  extractable text -> refusal without an LLM call. Highlights and notes are not context.
  `MockClient.text` gains a page mode (prompt contains `<page n=`): content-word rule against
  page text, cites the first matching page.
- **Rationale**: a typical paper fits the context window; whole text avoids retrieval misses and
  new deps. Page-only transcript per user decision. Same refusal machinery as results chat.
- **Alternatives**: native citations API with document blocks (incompatible with mock path);
  FTS5 page retrieval (only needed for huge papers); eager extraction on save (violates lazy
  rule). Prompt caching deferred (optional live-mode cost tweak).

## R17 v3: tags, library filtering, directories

- **Decision**: `tags.py` `keywords(topic) -> list[str]`: lowercase, split on whitespace and
  commas, strip surrounding punctuation (inner `-` kept), drop English stop words (fixed list in
  the module) and 1-character tokens, dedupe keeping order. Item-only queries have topic `""`
  -> no tags. Tags merge on save and when a topic search returns an already saved paper.
  Filtering (tags AND, title substring, directory) runs client-side over `GET /api/library`
  (tens to hundreds of papers). Directories: flat table, Unsorted = `NULL`, names 1-40 chars,
  unique by `casefold()`, "Unsorted" and "All saved" reserved; delete sets members to `NULL`.
- **Rationale**: one list request keeps the API small; client filtering is instant at this scale.
- **Alternatives**: whole topic string as one tag (brief 10.1; router default chose tokens);
  server-side filter endpoints (more API, no benefit at this scale).

## R18 v3: find in paper and export notes

- **Decision**: both client-only. Find uses `page.getTextContent()` per page (no server
  endpoint; brief B8 dropped); export builds Markdown from the loaded annotation list.
- **Rationale**: no new API; the viewer already loads the document.

## R19 v4: vendored IBM Plex fonts

- **Decision**: 8 woff2 files, renamed per DESIGN.md section 3.1: Plex Sans 400/600 Latin and
  Latin-ext from `@fontsource/ibm-plex-sans@5.3.0` (`files/ibm-plex-sans-{latin,latin-ext}-
  {400,600}-normal.woff2`), Plex Sans Greek Regular/SemiBold from `@ibm/plex-sans@1.1.0`
  (`fonts/split/woff2/`, list the tarball for exact names), Plex Mono 400 Latin and Latin-ext
  from `@fontsource/ibm-plex-mono@5.3.0`. Total 125,228 bytes (cap 250 KB). `plex.css` holds
  the `@font-face` rules (`font-display: swap`, `unicode-range` copied verbatim from Fontsource
  `latin.css`/`latin-ext.css`, Greek `U+0370-03FF`) and the metric-matched "IBM Plex Sans
  Fallback" face; linked before `app.css` so `app.css` stays free of `@font-face`. One
  build-time fetch (`npm pack` of the three pinned packages into a scratch dir, or `curl` of the
  same registry tarballs if npm is absent); nothing is installed in the project. OFL text as
  `LICENSE-IBM-Plex.txt`; `README` records packages, versions and file mapping.
- **Rationale**: Fontsource ships no Greek (verified in ibm-verify.md); the official split
  package does. `unicode-range` keeps a typical page at the ~62 KB Latin set. Weights 300/500/
  700 are not used (D3.1), and `font-synthesis: none` stops faked weights.
- **Alternatives**: system stack (v2; loses the Carbon voice); Google Fonts CDN (breaks
  principle II and the static guard); Plex Mono Greek (not checked; system mono fallback is
  acceptable for rare Greek in ids).

## R20 v4: visual verification without pixel diffs

- **Decision**: `tests/frontend/test_e2e_design.py` asserts rendered values (font family and
  `document.fonts.check`, radius 0 on controls, key token colours, focus ring, highlight fill
  alpha 1 + multiply, `.is-stale` opacity 1) and computed WCAG contrast for a fixed selector
  list at 390, 820 and 1440 px, emulates `reduced_motion="reduce"` and `forced_colors="active"`,
  and saves screenshots of Triage, Library and Preview at each width to `$V4_SHOTS_DIR`.
  Screenshots feed the designer re-audit (brief item 34); they are not compared pixel by pixel.
- **Rationale**: pytest-playwright (Python) has no built-in screenshot assertion; an image-diff
  library is a new dependency (principle I); font rasterising differs across machines, so
  baselines would flake. Style and contrast assertions are deterministic and offline.
- **Alternatives**: stored PNG baselines + Pillow diff (new dep, flaky); Node Playwright test
  runner (second toolchain).

## R21 v4: token migration order

- **Decision**: one FE task swaps the whole `:root` block to DESIGN.md tokens and remaps every
  `var()` use with the brief item 3 table in the same commit, so the page stays coherent; the
  per-view tasks then refine components; the final sweep adds the "no literal hex outside
  `:root`" test. All v4 FE tasks edit `app.css`, so they run sequentially in the FE lane; only
  the BE MIME task and the BE docs task run in parallel.
- **Rationale**: keeps every commit green and reviewable; avoids a half-migrated stylesheet with
  undefined variables.
- **Alternatives**: alias old tokens to new values during the migration (leaves dead names,
  which D9 forbids); one big restyle commit (violates one-small-commit rule).
