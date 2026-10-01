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

Live mode: copy `.env.example` to `.env`, set `ANTHROPIC_API_KEY` (optional
`ANTHROPIC_MODEL`), run without `MOCK_LLM`. Expect ~3 s per arXiv request (rate limit).

Details: [contracts/api.md](contracts/api.md), [data-model.md](data-model.md).
