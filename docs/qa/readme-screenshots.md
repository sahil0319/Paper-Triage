# README screenshots check (commit 071d354)

Result: GREEN with 2 cosmetic caption nits (tagged [BE]). No edits made.

## 1. Image paths
- README references 17 distinct `docs/screenshots/*.png`; all 17 exist; all 17 files in the directory are referenced (01, 02, 03, 03b, 04, 05, 06, 07, 07b, 08, 09, 10, 11, 12a, 12b, 12c, 13a). PASS.

## 2. Captions vs images
- Match: 01 (search box + example queries), 02 (working card, elapsed time), 04 (paper id + cited papers list), 05 ("Not in these papers"), 06 (Saved), 07 (directory rail + tag pills with counts), 07b (Rename / Delete directory), 08 (two tags selected), 09 (page nav, zoom, find, Highlight, Ask this paper), 10 (yellow/mint/peach + note + annotation list), 11 (page citation chips), 12a-c (390 px), 13a (Load 5 more papers).
- [BE] README.md:13 alt text says "a one-line reason": reasons in the live run are 4-7 line paragraphs. Suggest "a short reason".
- [BE] README.md:39 alt text says the card is expanded "to its summary, contributions and critique": 03b is cropped at the viewport, so only Summary and Contributions are visible (critique sections are below the fold). Suggest "to its summary and contributions, with the critique below".

## 3. Quick start vs reality
- `MOCK_LLM=1 uv run uvicorn paper_triage.app:app`, port 8000 (uvicorn default), `GET /api/status` fields (mock, provider, model, paper_count): confirmed against the live run (`{"mock":false,"model":"gpt-5-mini","provider":"openai","paper_count":N}`).
- Env vars in README match `src/paper_triage/config.py`/`llm.py`: LLM_PROVIDER (default anthropic), OPENAI_MODEL default `gpt-5-mini`, TRIAGE_CONCURRENCY default 4 min 1, PAPER_TRIAGE_DB `./paper_triage.db`, PAPER_TRIAGE_DATA_DIR `./paper_triage_data`, OpenAI-without-key startup error. `E2E_PORT` default 8766 matches `tests/e2e_harness.py`.
- `.env.example` is in a permission-denied directory for this agent, so "blank values in .env.example" not re-read (unchanged from previous README).

## 4. Dropped facts vs `071d354~1:README.md`
- Line-by-line normalized comparison: every old line from "## Using the page" on is present in the new README (heading renamed to "Usage"; "Reference"/"Features" wrappers added). Only the old intro (lines 3-12) was rewritten; its facts (pipeline, grounded chat citing ids and refusing, no auth, SQLite, Library with PDF on disk, viewer, highlights, notes, tags, directories, per-paper chat) are all in the new intro and Features. Minor: the explicit "Pipeline: ... -> grounded Chat." line became "(Fetcher -> Summarizer -> Critic -> Ranker)" plus a chat sentence. No loss. PASS.

## 5. Gates
- `uv run ruff check .`: All checks passed.
- `MOCK_LLM=1 uv run pytest -q`: 646 passed in 133 s (offline).
