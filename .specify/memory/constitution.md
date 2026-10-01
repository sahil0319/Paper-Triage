<!--
Sync Impact Report
- Version: 1.0.0 -> 1.1.0 (MINOR: materially expanded guidance)
- Modified principles: I. Small (dev deps + pytest-playwright/chromium for browser e2e);
  II. Offline-Testable (browser e2e offline rule); III. Grounded Answers (scope = current
  search's result set, not the whole store)
- Added sections: none
- Removed sections: none
- Templates: plan/spec/tasks templates read this file at runtime; no edits needed
- Deferred TODOs: none
-->
# Paper Triage Assistant Constitution

## Core Principles

### I. Small

- Every runtime agent (fetcher, summarizer, critic, ranker, chat) is one module in `src/`.
  Each LLM-using agent (summarizer, critic, ranker, chat) has exactly one prompt file; the
  fetcher makes no LLM calls. No agent framework, no orchestration library.
- New dependencies MUST be justified in plan.md; prefer stdlib. Allowed core deps: fastapi,
  uvicorn, httpx, pydantic, anthropic, pypdf. Dev: pytest, ruff, pytest-playwright (plus the
  Playwright chromium browser, installed once with `uv run playwright install chromium` and
  recorded in SETUP_LOG.md) for real-browser e2e tests only.
- Each task is one small commit that leaves the test suite green.
Rationale: a single user tool; size is the main source of bugs and cost.

### II. Offline-Testable (MOCK_LLM=1)

- All LLM access goes through one client wrapper with a mock twin behind the same interface;
  `MOCK_LLM=1` returns deterministic canned outputs valid against the same Pydantic schemas.
- All network (arXiv API, PDF download) goes through injectable fetch functions; tests use
  fixtures and MUST NOT touch the network or require `ANTHROPIC_API_KEY`.
- Browser e2e tests run against a local server on 127.0.0.1 with `MOCK_LLM=1`; the page
  MUST load no external assets (fonts, scripts, CDNs), so the browser needs no network.
- `pytest` and `ruff check` MUST pass offline before any task is marked done.
Rationale: reproducible, free, fast tests; the build loop runs without secrets.

### III. Grounded Answers (NON-NEGOTIABLE)

- Chat answers use only the papers of the current search's result set (the papers shown for
  the active search, including load-more pages), never other stored papers or general
  knowledge. Every factual claim cites a paper id from that set.
- The server MUST validate cited ids against that set and drop/flag any other id.
- When the set cannot answer, the reply is an explicit refusal (sentinel
  `NOT_IN_STORED_PAPERS`), rendered as a deliberate state, never a guess. This holds for the
  real model path and the mock client alike.
- With an empty result set (or zero stored papers), chat refuses without calling the LLM.
Rationale: the product's value is trust; an uncited claim is a defect.

### IV. One-Page Scope

- Feature scope fits a one-page spec: at most 3 user stories and 15 functional requirements.
- One single-page web UI (vanilla HTML/JS/CSS, no framework).
- No auth, no multi-user, no deployment, no background job queue.
- Features outside PRODUCT.md require a constitution amendment.
Rationale: keeps the build finishable and reviewable.

### V. Honest Critique

- Critique states the basis (`fulltext` or `abstract`); abstract-only results are flagged in UI.
- Prompts instruct "not stated" over guessing; ranks are clamped 0-10 with a 1-2 sentence reason.
- Tone calm and plain; no hype, no emoji (PRODUCT.md).
Rationale: skeptical triage is the purpose.

## Technical Constraints

Python 3.11+, uv, FastAPI, SQLite (stdlib `sqlite3`), Anthropic SDK. Model from
`ANTHROPIC_MODEL` env (documented default only in config), key from `ANTHROPIC_API_KEY`.
arXiv API: max 1 request per 3 s, results cached in SQLite. Secrets only in `.env` (git-ignored).
UI work MUST re-read DESIGN.md and PRODUCT.md first.

## Development Workflow

Spec-kit chain: constitution -> specify -> clarify -> plan -> tasks -> analyze -> implement.
Per task: builder implements (tests first where cheap) -> tester runs pytest + ruff -> commit.
Orchestrator owns git; agents end with `DONE` | `BLOCKED: <why>` | `NEXT:<agent>`.

## Governance

This constitution overrides other practice docs on conflict. Amendments: edit this file, bump
version (MAJOR: principle removed/redefined; MINOR: principle/section added; PATCH: wording),
record a Sync Impact Report. plan.md MUST include a Constitution Check; analyze treats
principle violations as CRITICAL. Runtime guidance lives in CLAUDE.md.

**Version**: 1.1.0 | **Ratified**: 2026-10-01 | **Last Amended**: 2026-10-01
