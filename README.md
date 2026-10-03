# Paper Triage Assistant

Give it a topic or arXiv IDs / PDF URLs. It fetches papers, summarizes each, critiques it, and
ranks it 0-10 with a reason. Then ask questions in a chat grounded only in the current search
results: it cites paper ids and refuses anything outside them. Single user, no auth, SQLite
storage.

Pipeline: Fetcher -> Summarizer -> Critic -> Ranker -> grounded Chat.

You can also save papers to a local Library: each saved paper keeps its summary, critique and
score, gets its PDF stored on disk, and can be read in the page, highlighted, annotated, tagged,
filed into directories and questioned in a chat that answers from that paper alone.

## Using the page

- **Search.** Enter a topic (keywords) or arXiv IDs / PDF URLs, or a mix. Results are listed by
  rank (0-10) with the reason, summary and critique.
- **Searching indicator.** A triage can take a while in live mode (roughly 1 to 3 minutes for up
  to 10 papers). While it runs the page shows a working card with activity and elapsed time, never
  a progress percentage.
- **Paper links.** Each result links to its source: arXiv papers get an abstract page and a PDF
  link (`https://arxiv.org/abs/<id>`, `https://arxiv.org/pdf/<id>`); a direct PDF URL gets the PDF
  link only (`abs_url` is `null`).
- **Load more.** A topic search returns 10 papers first; "Load 5 more" fetches the next page
  (`offset` / `next_offset` / `has_more` in `POST /api/triage`). Paging applies to topic searches
  only: a query with arXiv IDs or URLs is one page, and sending `offset` above 0 with such a query
  is a 422.
- **Chat scope.** The chat answers only from the papers in the current results (the first page
  plus any loaded pages, at most 50). The page sends those ids as `paper_ids` with every
  `POST /api/chat`. A paper stored by an earlier search but not shown now is out of scope: the
  answer is a refusal and nothing outside the set is cited. An empty result set is refused without
  a model call.

## Library, PDF viewer and paper chat

Everything below is local. There is no account and nothing is shared.

- **Save.** Every completed result card has a Save button. Saving freezes a snapshot of the card
  (title, authors, date, abstract, summary, critique, score and reason, links, the query it was
  ranked against) in SQLite. Later searches never change it. Saving a paper twice keeps the first
  snapshot and save time and only merges tags. Cards of saved papers show "Saved" in every search
  and after a reload. Unsave always asks first; it deletes the entry, its PDF file, its highlights
  and notes, and its prepared paper text. Search results are kept.
- **PDF download.** After you save, the app downloads the PDF in the background (the save is not
  delayed). A saved paper's PDF is `pending`, `ready` or `failed` (with a plain reason, and a
  Retry action). The limit is 50 MB, content must start with `%PDF-`, and arXiv downloads wait at
  least 3 s between requests (`export.arxiv.org` first, then `arxiv.org`). A direct PDF URL is
  fetched from its own URL without the wait. Downloads cut short by a restart become `failed`
  ("Download interrupted. Try again.") when the app starts.
- **Library view.** A Library section lists saved papers, newest first, with title, authors, date,
  score, tags, directory and PDF status. It has an empty state and a "no match" state.
- **Tags.** Tags come from the topic query, not from manual editing: lowercase words, English stop
  words and 1-character tokens dropped, duplicates removed (`Diffusion models, for VIDEO
  generation` gives `diffusion`, `models`, `video`, `generation`). Queries made of arXiv IDs or
  URLs add no tags. The Library lists every tag with its paper count and lets you select several
  (a paper must carry all of them), narrow the tag list by typing, clear the selection and filter
  by title. Tag, title and directory filters combine.
- **Directories.** Create, rename and delete flat directories (1-40 characters, unique ignoring
  case; "Unsorted" and "All saved" are reserved). Each paper is in exactly one directory (default
  Unsorted) and can be moved. Deleting a directory moves its papers to Unsorted.
- **Viewer.** Open a ready PDF in the page: previous and next page, go to page, "page n of m",
  zoom in and out, fit width, and open the PDF in a new tab. Pages are drawn by a vendored copy of
  pdf.js (below), served by this app; the viewer loads nothing from other hosts. Closing the
  viewer keeps your Library filters and scroll position.
- **Highlights and notes.** Select text to highlight it in one of 3 colors (yellow, mint, peach).
  Add a note of up to 500 characters to a highlight or to a page. Edit, recolor or delete them
  (deleting offers Undo for 8 seconds). Highlight positions are stored as fractions of the page, so
  they stay on the same text at every zoom level. An annotation list shows them by page; picking
  one jumps to it. Annotations persist across restarts.
- **Paper chat.** A chat beside the viewer answers only from that paper's own text and cites page
  numbers as `[p.N]`; picking a citation jumps the viewer to that page. It is lazy: page text is
  extracted and a model is called only when you ask the first question about a paper. It refuses
  when the paper does not cover the question, and refuses without a model call when the PDF is not
  ready or has no extractable text. Cited pages that do not exist are removed (`dropped_pages`).
  Highlights and notes are not part of the chat context. The transcript lives in the page only and
  resets on reload or when the preview closes.

The page follows `DESIGN.md`, `PRODUCT.md` and the v3 brief `docs/design/v3-library-brief.md`.

### Storage

- `PAPER_TRIAGE_DATA_DIR` sets where PDFs are stored (default `./paper_triage_data`, git-ignored).
  Files are `<data dir>/pdfs/<sha256 of the paper id>.pdf`; the app creates the directory at start.
  Metadata, tags, directories and annotations stay in the SQLite file (`PAPER_TRIAGE_DB`).
- Keep the DB file and the data directory together when you move or back them up.
- The stored PDFs are for your own personal and research use. arXiv's terms allow storing
  e-prints for personal use but not redistributing them, so do not deploy this app publicly or
  share the data directory.

### Design and fonts

The page follows `DESIGN.md` (v4), which is built on IBM Carbon: a light theme only (white canvas,
`#f4f4f4` layers, one IBM Blue accent, 1px rules, square corners, no shadows except overlays).
There is no dark mode.

The UI uses IBM Plex Sans (weights 400 and 600) and IBM Plex Mono (400), vendored as 8 woff2
files (about 125 KB, SIL Open Font License 1.1) under `src/paper_triage/static/vendor/fonts/`,
with `plex.css` holding the `@font-face` rules and `LICENSE-IBM-Plex.txt` the licence text. The
exact npm packages and versions (`@fontsource/ibm-plex-sans@5.3.0`,
`@fontsource/ibm-plex-mono@5.3.0`, `@ibm/plex-sans@1.1.0`), the file mapping and the sha256
checksums are listed in `static/vendor/fonts/README`. The files were fetched once at build time
with `npm pack`; the app makes no font request to the network at run time, and there is no CDN,
npm install or build step. To update a font, replace the files and update that README. The app
registers `.woff2` as `font/woff2` at startup so the type is correct on every OS.

### Vendored pdf.js

The viewer uses pdf.js (`pdfjs-dist` 6.3.289, modern build, Apache-2.0) committed under
`src/paper_triage/static/vendor/pdfjs/` (`pdf.min.mjs`, `pdf.worker.min.mjs`, `LICENSE`,
`VERSION`). Source: https://registry.npmjs.org/pdfjs-dist/-/pdfjs-dist-6.3.289.tgz. There is no
CDN, no npm install and no build step. The library and worker versions must match exactly, so
update both files together and edit `VERSION`. The app registers `.mjs` as `text/javascript` at
startup so module scripts load on every OS.

### Library API

Paper ids can contain `/`, so they travel in the JSON body or the `paper_id` query parameter.
Shapes are in `specs/001-paper-triage/contracts/api.md`.

| Endpoint | Purpose |
|---|---|
| `GET /api/library` | saved papers, directories with counts, `unsorted_count`, `total` |
| `POST /api/library` | save `{paper_id, topic}` (201, or 200 if already saved) |
| `DELETE /api/library?paper_id=` | unsave |
| `POST /api/library/retry` | retry a failed PDF download (202) |
| `GET /api/library/pdf?paper_id=` | the stored PDF, inline, Range requests honored |
| `POST /api/library/move` | move a paper to a directory (`null` = Unsorted) |
| `POST /api/directories`, `PATCH`/`DELETE /api/directories/{id}` | directory CRUD |
| `GET`/`POST /api/annotations`, `PATCH`/`DELETE /api/annotations/{id}` | highlights and page notes |
| `POST /api/paper-chat` | ask about one saved paper (`pages`, `refused`, `dropped_pages`) |

Triage and `GET /api/papers` items also carry `saved: true | false`.

### Mock mode and the Library

With `MOCK_LLM=1` no network is used. The mock arXiv feed holds 15 papers (`2401.00001` to
`2401.00015`); `PAPER_TRIAGE_DATA_DIR` still applies, so point it at a scratch directory when you
try things out. Saving serves `src/paper_triage/fixtures/sample.pdf`, a 3-page PDF made by
`fixtures/make_sample_pdf.py`:

- `2401.00005` returns bytes that are not a PDF, so its download ends `failed` ("Not a PDF.") and
  you can try Retry.
- Direct PDF URLs on hosts ending `.invalid` return 404, so they also end `failed`.
- Paper chat in mock mode answers only when your question shares a content word (4 or more
  letters) with a page, and cites the first such page: ask about "Quartzite" for page 2 or
  "Obsidian" for page 3; "What is the capital of France?" is refused.

## Setup

Needs Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```sh
uv sync
cp .env.example .env      # live mode only; .env is git-ignored
```

The app does not load `.env` itself. Export it into your shell before a live run:
`set -a; source .env; set +a`.

## Run

Mock (offline, canned LLM output and bundled arXiv fixtures, no key needed):

```sh
MOCK_LLM=1 uv run uvicorn paper_triage.app:app
```

Live (real arXiv and Claude):

```sh
export ANTHROPIC_API_KEY=...        # your key
export ANTHROPIC_MODEL=...          # model id to use
uv run uvicorn paper_triage.app:app
```

Live with OpenAI instead of Claude (`LLM_PROVIDER` is `anthropic` by default; `MOCK_LLM=1` wins over both):

```sh
# in .env (blank values in .env.example): LLM_PROVIDER=openai, OPENAI_API_KEY=..., OPENAI_MODEL=...
set -a; source .env; set +a
uv run uvicorn paper_triage.app:app
```

`OPENAI_MODEL` defaults to `gpt-5-mini`; confirm that id is available to your key, or set your own.
Startup fails with a clear error if `LLM_PROVIDER=openai` and `OPENAI_API_KEY` is unset.

`TRIAGE_CONCURRENCY` (default 4, min 1) sets how many papers are summarized/critiqued/ranked in
parallel (summarizer and critic also overlap within a paper). `1` = fully sequential. Fetching and
arXiv throttling stay sequential; lower it if your key hits rate limits.

Open http://127.0.0.1:8000. Optional: `PAPER_TRIAGE_DB` sets the SQLite path
(default `./paper_triage.db`); `PAPER_TRIAGE_DATA_DIR` sets where saved PDFs go (default
`./paper_triage_data`). `GET /api/status` reports mock mode, provider, model and stored
paper count.

## Test

All tests run offline (no key, no network).

```sh
uv run pytest -q
uv run ruff check .
```

Real-browser tests (marker `e2e`, Playwright) drive the UI in Chromium against a local mock-LLM
server (`tests/e2e_harness.py`, temp SQLite file and temp PDF data directory removed on stop,
optional delay before `POST /api/triage` to observe the searching indicator). The server listens on `127.0.0.1:8766`; set `E2E_PORT` to use
another port. Any request to a non-local host fails the test. They skip when Chromium is missing.
Install it once (the browser download happens only here, see `SETUP_LOG.md`; tests themselves stay
offline):

```sh
uv run playwright install chromium
MOCK_LLM=1 uv run pytest -q -m e2e
```

The v4 design checks (zero non-local requests, `font/woff2` responses, contrast, focus ring,
reduced motion, forced colors, and screenshots of Triage, Library and Preview at widths 390, 820
and 1440) live in `tests/frontend/test_e2e_design.py`. To run them and keep the screenshots:

```sh
MOCK_LLM=1 V4_SHOTS_DIR=docs/qa/screenshots/v4 uv run pytest -q -m e2e tests/frontend/test_e2e_design.py
```

Screenshots are written as `<view>-<width>.png`. When `V4_SHOTS_DIR` is not set they go to a
pytest temp directory.

## Notes

- arXiv rate limit: live mode waits at least 3 s between arXiv requests (`net.py` `Throttle`),
  so a 10-paper triage takes a while. Mock mode skips the wait.
- PDF text uses pypdf (`extract.py`, the one swap point). To use PyMuPDF instead, reimplement
  `extract_text`, `extract_pages`, `page_count` and `pdf_title` there with `fitz`, and swap the dependency in `pyproject.toml`.
  Scanned PDFs with too little text are reported as failures, not crashes.

## Layout

```
src/paper_triage/
  app.py          FastAPI: /api/status, /api/triage, /api/papers, /api/chat, Library routes + UI
  pipeline.py     orchestrates fetch -> summarize -> critique -> rank, persists results
  fetcher.py      arXiv search / ID / PDF URL fetch      (input_parse.py, net.py, extract.py)
  summarizer.py   runtime agent, prompt in prompts/summarizer.md
  critic.py       runtime agent, prompt in prompts/critic.md
  ranker.py       runtime agent, prompt in prompts/ranker.md
  chat.py         grounded chat agent, prompt in prompts/chat.md
  paper_chat.py   per-paper chat agent (page-cited), prompt in prompts/paper_chat.md
  tags.py         topic -> keyword tags
  pdfstore.py     background PDF download to the data directory (cap, atomic write, sweep)
  llm.py          the single LLM client wrapper (Anthropic or OpenAI; honors MOCK_LLM=1)
  db.py models.py config.py
  fixtures/       sample arXiv feed + PDF used in mock mode
  static/         the UI (static/vendor/pdfjs/ is the vendored pdf.js, static/vendor/fonts/ the IBM Plex fonts)
tests/            pytest, offline; e2e_harness.py + e2e-marked tests need chromium
```

UI: one page of vanilla HTML/CSS/JS in `static/`, no framework or build step.
