# Data Model: Paper Triage Assistant

SQLite file at `PAPER_TRIAGE_DB` (default `./paper_triage.db`, git-ignored via `*.db`).
Schema created idempotently on startup (`CREATE TABLE IF NOT EXISTS`). JSON columns are TEXT.

## papers

| column | type | rule |
|---|---|---|
| id | TEXT PK | arXiv id w/o version (`2401.01234`, `math.GT/0107001`) or `pdf:<12 hex>` |
| source | TEXT | `arxiv` \| `pdf` |
| version | TEXT NULL | e.g. `v2` (arXiv only) |
| title | TEXT | non-empty |
| authors | TEXT (JSON list[str]) | may be empty |
| abstract | TEXT | arXiv summary, or first 1,500 chars of text for `pdf` |
| published | TEXT NULL | ISO date |
| pdf_url | TEXT NULL | |
| full_text | TEXT NULL | extracted text (capped 200,000 chars); PDF bytes never stored |
| basis | TEXT | `fulltext` \| `abstract` |
| fetched_at | TEXT | ISO timestamp |

## arxiv_cache

| column | type | rule |
|---|---|---|
| key | TEXT PK | normalized query string (v2: `q:<terms>:<n>:<offset>` or `ids:<sorted ids>`; old `q:<terms>:<n>` rows are simply never hit again) |
| body | TEXT | raw Atom XML |
| fetched_at | TEXT | ISO; no expiry in v1 |

## results

| column | type | rule |
|---|---|---|
| paper_id | TEXT FK papers.id | |
| topic | TEXT | may be `""` (id-only input) |
| summary | TEXT (JSON Summary) NULL | |
| critique | TEXT (JSON Critique) NULL | |
| rank | INTEGER NULL | 0..10 (clamped) |
| rank_reason | TEXT NULL | |
| status | TEXT | `ok` \| `failed` |
| error | TEXT NULL | reason when failed |
| created_at | TEXT | ISO |
| PK | (paper_id, topic) | same paper + topic -> reused, not recomputed |

## chat_turns

| column | type | rule |
|---|---|---|
| id | INTEGER PK | autoincrement |
| question | TEXT | |
| answer | TEXT | citations already validated |
| citations | TEXT (JSON list[str]) | all exist in papers |
| refused | INTEGER | 0/1 |
| created_at | TEXT | ISO |

## Pydantic schemas (`models.py`) = LLM output contracts

- **Summary**: `summary: str` (<=120 words, validator trims), `contributions: list[str]` (1-5).
- **Critique**: `weak_claims: list[{claim, why}]`, `overclaims: list[{claim, evidence_gap}]`,
  `missing_baselines: list[str]`, `basis: Literal["fulltext","abstract"]` (set by code, not LLM).
- **Rank**: `rank: int` (clamped 0-10 in validator), `rank_reason: str` (1-2 sentences).
- **ChatAnswer** (API, not LLM): `answer: str`, `citations: list[str]`, `refused: bool`,
  `dropped_citations: list[str]`.

- **PaperOut** (API, v2): adds `abs_url: str | None`, `pdf_url: str | None`, derived per
  contracts/api.md (arXiv: from the id; `pdf` source: `papers.pdf_url`). No schema migration:
  `papers.pdf_url` already exists; `abs_url` is never stored.

## Result set (v2, client-held, not persisted)

Page state in `app.js`: `query` (string sent to `/api/triage`), `topic`, `ids` (ordered, unique,
max 50), `nextOffset` (int | null), `hasMore` (bool). A new search replaces it; load-more
appends to `ids` and updates `nextOffset`/`hasMore`; a reload rebuilds it from
`GET /api/papers` (`nextOffset` = number of shown results, `hasMore` = topic non-empty).
Sent as `paper_ids` on every `POST /api/chat`.

## v3 tables (Library)

All created idempotently in `db.SCHEMA`; `PRAGMA foreign_keys = ON` already set. Saved PDFs
live on disk under `PAPER_TRIAGE_DATA_DIR` (default `./paper_triage_data`, git-ignored).

### directories

| column | type | rule |
|---|---|---|
| id | INTEGER PK | autoincrement |
| name | TEXT | trimmed, 1..40 chars, shown as typed |
| name_key | TEXT UNIQUE | `name.casefold()`; `unsorted` and `all saved` reserved (409) |
| created_at | TEXT | ISO |

### saved_papers

| column | type | rule |
|---|---|---|
| paper_id | TEXT PK FK papers.id | one entry per paper (idempotent save) |
| snapshot | TEXT (JSON) | frozen at first save: `PaperOut` fields (title, authors, source, basis, rank, rank_reason, summary, critique, abs_url, pdf_url) + `abstract`, `published` |
| topic | TEXT | topic the card was ranked against (`""` for item runs) |
| directory_id | INTEGER NULL FK directories.id ON DELETE SET NULL | `NULL` = Unsorted |
| saved_at | TEXT | ISO, first save only |

### saved_tags

| column | type | rule |
|---|---|---|
| paper_id | TEXT FK saved_papers.paper_id ON DELETE CASCADE | |
| tag | TEXT | output of `tags.keywords(topic)` |
| added_at | TEXT | ISO; list order = added_at, then tag |
| PK | (paper_id, tag) | merge = `INSERT OR IGNORE` |

### paper_files

| column | type | rule |
|---|---|---|
| paper_id | TEXT PK FK saved_papers.paper_id ON DELETE CASCADE | |
| source_url | TEXT | URL downloaded (arXiv export URL or direct PDF URL) |
| status | TEXT | `pending` \| `ready` \| `failed` |
| error | TEXT NULL | plain reason when failed |
| path | TEXT NULL | absolute file path; set only when ready |
| bytes | INTEGER NULL | <= 52,428,800 (50 MB) |
| sha256 | TEXT NULL | of the file |
| pages | INTEGER NULL | page count (pypdf, no text extraction) |
| updated_at | TEXT | ISO |

### paper_pages (lazy, written on the first paper-chat question)

| column | type | rule |
|---|---|---|
| paper_id | TEXT FK saved_papers.paper_id ON DELETE CASCADE | |
| page | INTEGER | 1-based |
| text | TEXT | pypdf `extract_text()` of that page (may be empty) |
| PK | (paper_id, page) | absent rows = not prepared yet |

### annotations

| column | type | rule |
|---|---|---|
| id | INTEGER PK | autoincrement |
| paper_id | TEXT FK saved_papers.paper_id ON DELETE CASCADE | |
| page | INTEGER | 1..`paper_files.pages` |
| kind | TEXT | `highlight` \| `note` |
| color | TEXT | `yellow` (default) \| `mint` \| `peach` |
| rects | TEXT (JSON list[[x,y,w,h]]) | highlight: 1..50 rects, every value 0..1; note: `[]` |
| top | REAL | min y of rects (0 for page notes); ordering key |
| quote | TEXT | highlight: 1..500 chars; note: `""` |
| prefix / suffix | TEXT | 0..64 chars each |
| note | TEXT | 0..500 chars; kind `note` requires 1..500 |
| created_at / updated_at | TEXT | ISO |

Unsave = `DELETE FROM saved_papers` (cascades tags, files row, pages, annotations) + unlink the
PDF file. `papers`, `results` and `chat_turns` are never touched by Library actions.

### Pydantic (API, `models.py`)

- **LibraryItem**: snapshot fields + `paper_id`, `topic`, `tags: list[str]`,
  `directory_id: int | None`, `saved_at`, `pdf: {status, error, pages}`, `highlight_count: int`.
- **Directory**: `id`, `name`, `count`.
- **Annotation**: table columns, `rects: list[list[float]]`.
- **PaperChatAnswer**: `answer: str`, `pages: list[int]`, `refused: bool`,
  `dropped_pages: list[int]`.
- **PaperOut** (v3): adds `saved: bool`.

### Paper chat transcript (v3, client-held, not persisted)

Per open preview in the page: list of `{question, answer, pages, refused}`. Reset on reload or
when the preview closes. The last 6 turns are sent as `history`.

### State (v3)

PDF file: (save) -> pending -> ready | failed; failed -> (retry) -> pending; pending at startup
-> failed ("Download interrupted. Try again."). Paper text: absent -> prepared (first paper-chat
question with a ready PDF). Saved paper: saved -> (unsave) -> gone with all dependents.

## State

Paper: fetched -> (extract ok: basis=fulltext | fail: basis=abstract).
Result: created -> ok (all three agents succeeded) | failed (any agent failed after 1 retry;
partial fields kept).
