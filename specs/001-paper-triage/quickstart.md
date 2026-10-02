# Quickstart / Validation

Prereqs: Python 3.11+, uv.

```sh
uv sync
uv run ruff check .
MOCK_LLM=1 uv run pytest -q          # offline, no key
MOCK_LLM=1 uv run uvicorn paper_triage.app:app --port 8000
```

Mock-mode checks (browser at http://127.0.0.1:8000):

1. Header shows "Offline mock mode" label.
2. Enter `diffusion distillation`, submit: 5 fixture papers ranked desc, each rank + reason
   visible; one paper flagged "abstract only".
3. Open a critique: weak claims / overclaims / missing baselines (or "not stated").
4. Chat a question that contains a word from a shown paper's title: answer with citation links
   to shown ids (v2 mock rule: content-word or id overlap with the current result set).
5. Chat "What is the capital of France?": refusal state.
6. Restart server, reload: same list (US3).

v2 checks (mock mode, fresh DB, default 10 papers):

7. Submit `diffusion distillation`: a cream working card with rotating verbs and a timer shows
   while the request runs, then disappears; 10 papers listed.
8. Each arXiv row shows "arXiv page" (`https://arxiv.org/abs/<id>`) and "PDF"
   (`https://arxiv.org/pdf/<id>`) links opening in a new tab.
9. "Load 5 more papers": 5 rows appended under "Papers 11–15", no duplicate ids; the button is
   then gone ("No more papers").
10. Chat "What is the capital of France?": refusal. Chat naming a word from a shown title:
    answer citing a shown id.
11. Submit one id `2401.00001`, then ask about another fixture paper's title word: refusal
    (that paper is stored but not in the current set).

Browser e2e (offline, after one-time `uv run playwright install chromium`):

```sh
MOCK_LLM=1 uv run pytest -q -m e2e          # port 8766; override with E2E_PORT
```

v3 Library (mock mode, offline; PDFs land in `PAPER_TRIAGE_DATA_DIR`, default
`./paper_triage_data`):

12. Search "diffusion models", activate Save on one card: the button reads "Saved"; the nav
    shows "Library 1".
13. Open Library: the row shows tags "diffusion" and "models", "Unsorted", and the PDF status
    moves from "Downloading PDF…" to "PDF ready" without a reload.
14. Search "video generation", Save another card. In Library select tags "diffusion" and
    "models": only the first paper shows. Type part of its title: still shown; a random string:
    "No saved papers match."
15. Create directory "thesis", move the first paper into it, select "thesis": one row. Delete
    "thesis" and confirm: the paper is back in Unsorted.
16. Open preview: page 1 renders in the page (no new tab); next page, zoom in/out, fit width work.
    Select text, pick Mint: the highlight shows, survives zoom and an app restart; add a note;
    the Highlights list "Go to" jumps to the page.
17. Ask this paper a question using a word from page 2 of the fixture: the answer cites "p. 2";
    activating it jumps the viewer. Ask "What is the capital of France?": refusal. Reload: the
    transcript is gone.
18. Save `2401.00005` (fixture with a non-PDF body): status "PDF unavailable" with "Try again";
    the chat input is disabled with its reason.
19. Unsave from the card: a confirmation appears; confirm: the Library entry, its PDF file and
    its highlights are gone.

Live mode: copy `.env.example` to `.env`, set `ANTHROPIC_API_KEY` (optional
`ANTHROPIC_MODEL`), run without `MOCK_LLM`. Expect ~3 s per arXiv request (rate limit).

Details: [contracts/api.md](contracts/api.md), [data-model.md](data-model.md).
