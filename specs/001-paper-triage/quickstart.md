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
4. Chat "what does the top paper claim?": answer with citation links to stored ids.
5. Chat "out of scope question about cooking": refusal state.
6. Restart server, reload: same list (US3).

Live mode: copy `.env.example` to `.env`, set `ANTHROPIC_API_KEY` (optional
`ANTHROPIC_MODEL`), run without `MOCK_LLM`. Expect ~3 s per arXiv request (rate limit).

Details: [contracts/api.md](contracts/api.md), [data-model.md](data-model.md).
