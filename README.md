# Paper Triage Assistant

Give it a topic or arXiv IDs / PDF URLs. It fetches papers, summarizes each, critiques it, and
ranks it 0-10 with a reason. Then ask questions in a chat grounded only in the current search
results: it cites paper ids and refuses anything outside them. Single user, no auth, SQLite
storage.

Pipeline: Fetcher -> Summarizer -> Critic -> Ranker -> grounded Chat.

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
(default `./paper_triage.db`). `GET /api/status` reports mock mode, provider, model and stored
paper count.

## Test

All tests run offline (no key, no network).

```sh
uv run pytest -q
uv run ruff check .
```

Real-browser tests (marker `e2e`, Playwright) drive the UI in Chromium against a local mock-LLM
server (`tests/e2e_harness.py`, temp SQLite file, optional delay before `POST /api/triage` to
observe the searching indicator). The server listens on `127.0.0.1:8766`; set `E2E_PORT` to use
another port. Any request to a non-local host fails the test. They skip when Chromium is missing.
Install it once (the browser download happens only here, see `SETUP_LOG.md`; tests themselves stay
offline):

```sh
uv run playwright install chromium
MOCK_LLM=1 uv run pytest -q -m e2e
```

## Notes

- arXiv rate limit: live mode waits at least 3 s between arXiv requests (`net.py` `Throttle`),
  so a 10-paper triage takes a while. Mock mode skips the wait.
- PDF text uses pypdf (`extract.py`, the one swap point). To use PyMuPDF instead, reimplement
  `extract_text` and `pdf_title` there with `fitz`, and swap the dependency in `pyproject.toml`.
  Scanned PDFs with too little text are reported as failures, not crashes.

## Layout

```
src/paper_triage/
  app.py          FastAPI: /api/status, /api/triage, /api/papers, /api/chat + static UI
  pipeline.py     orchestrates fetch -> summarize -> critique -> rank, persists results
  fetcher.py      arXiv search / ID / PDF URL fetch      (input_parse.py, net.py, extract.py)
  summarizer.py   runtime agent, prompt in prompts/summarizer.md
  critic.py       runtime agent, prompt in prompts/critic.md
  ranker.py       runtime agent, prompt in prompts/ranker.md
  chat.py         grounded chat agent, prompt in prompts/chat.md
  llm.py          the single LLM client wrapper (Anthropic or OpenAI; honors MOCK_LLM=1)
  db.py models.py config.py
  fixtures/       sample arXiv feed + PDF used in mock mode
  static/         the UI
tests/            pytest, offline; e2e_harness.py + e2e-marked tests need chromium
```

UI: one page of vanilla HTML/CSS/JS in `static/`, no framework or build step.
