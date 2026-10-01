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

## State

Paper: fetched -> (extract ok: basis=fulltext | fail: basis=abstract).
Result: created -> ok (all three agents succeeded) | failed (any agent failed after 1 retry;
partial fields kept).
