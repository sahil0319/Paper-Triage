<!--
Sync Impact Report
- Version: 1.1.0 -> 2.0.0 (MAJOR: principle III scope redefined with a second chat scope;
  principle IV scope cap redefined)
- Modified principles: I. Small (vendored same-origin static JS libraries allowed, no
  framework, no build step); II. Offline-Testable (PDF downloads injectable, fixture PDF in mock
  mode); III. Grounded Answers (adds per-paper chat scope with page citations); IV. One-Page
  Scope (cap 9 user stories / 32 FRs; views via hash routes on one page; in-process background
  download allowed; locally stored PDFs for saved papers)
- Added sections: none
- Removed sections: none
- Templates: plan/spec/tasks templates read this file at runtime; no edits needed
- Deferred TODOs: PRODUCT.md Library section (designer drafting; orchestrator owns)
-->
# Paper Triage Assistant Constitution

## Core Principles

### I. Small

- Every runtime agent (fetcher, summarizer, critic, ranker, chat, paper chat) is one module in
  `src/`. Each LLM-using agent (summarizer, critic, ranker, chat, paper chat) has exactly one
  prompt file; the fetcher makes no LLM calls. No agent framework, no orchestration library.
- New dependencies MUST be justified in plan.md; prefer stdlib. Allowed core deps: fastapi,
  uvicorn, httpx, pydantic, anthropic, pypdf. Dev: pytest, ruff, pytest-playwright (plus the
  Playwright chromium browser, installed once with `uv run playwright install chromium` and
  recorded in SETUP_LOG.md) for real-browser e2e tests only.
- Front end: vanilla HTML/JS/CSS, no framework, no bundler, no build step. Third-party browser
  libraries are allowed only when vendored as files under `static/vendor/<lib>/` with their
  license and pinned version, served same-origin, and justified in plan.md (v3: pdf.js modern
  build). No CDN, no runtime package fetch.
- Each task is one small commit that leaves the test suite green.
Rationale: a single user tool; size is the main source of bugs and cost.

### II. Offline-Testable (MOCK_LLM=1)

- All LLM access goes through one client wrapper with a mock twin behind the same interface;
  `MOCK_LLM=1` returns deterministic canned outputs valid against the same Pydantic schemas.
- All network (arXiv API, PDF download for triage and for saved papers) goes through injectable
  fetch functions; tests use fixtures (mock mode serves a fixture PDF) and MUST NOT touch the
  network or require `ANTHROPIC_API_KEY`.
- Browser e2e tests run against a local server on 127.0.0.1 with `MOCK_LLM=1`; the page
  MUST load no external assets (fonts, scripts, CDNs), so the browser needs no network.
- `pytest` and `ruff check` MUST pass offline before any task is marked done.
Rationale: reproducible, free, fast tests; the build loop runs without secrets.

### III. Grounded Answers (NON-NEGOTIABLE)

Two chat scopes exist; each answers only from its own scope, never from general knowledge.

- Results chat: uses only the papers of the current search's result set (the papers shown for
  the active search, including load-more pages), never other stored papers. Every factual claim
  cites a paper id from that set; the server validates cited ids against the set and
  drops/flags any other id. With an empty set (or zero stored papers) it refuses without
  calling the LLM.
- Paper chat (v3): uses only the extracted text of one saved paper. Every factual claim cites a
  page number (`[p.N]`); the server validates N against that paper's page count and drops/flags
  any other page. It is lazy: no text extraction and no LLM call before the user's first
  question for that paper. With no ready PDF or no extractable text it refuses without calling
  the LLM. User highlights and notes are not part of its context.
- When the scope cannot answer, the reply is an explicit refusal (sentinel
  `NOT_IN_STORED_PAPERS`), rendered as a deliberate state, never a guess. This holds for the
  real model path and the mock client alike.
Rationale: the product's value is trust; an uncited claim is a defect.

### IV. One-Page Scope

- Feature scope fits a bounded spec: at most 9 user stories and 32 functional requirements.
- One single-page web UI; Triage, Library and Preview are views of that page (hash routes),
  not separate pages.
- No auth, no multi-user, no deployment, no background job queue. In-process background work
  (for example a saved paper's PDF download) is allowed when its state is persisted and visible.
- PDFs are stored locally only for saved papers, for personal use; never redistributed or
  served beyond the local app.
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
arXiv API and arXiv PDF downloads: max 1 request per 3 s, results cached in SQLite. Saved PDFs
live as files in a git-ignored local data directory, capped at 50 MB each. Secrets only in
`.env` (git-ignored). UI work MUST re-read DESIGN.md and PRODUCT.md first.

## Development Workflow

Spec-kit chain: constitution -> specify -> clarify -> plan -> tasks -> analyze -> implement.
Per task: builder implements (tests first where cheap) -> tester runs pytest + ruff -> commit.
Orchestrator owns git; agents end with `DONE` | `BLOCKED: <why>` | `NEXT:<agent>`.

## Governance

This constitution overrides other practice docs on conflict. Amendments: edit this file, bump
version (MAJOR: principle removed/redefined; MINOR: principle/section added; PATCH: wording),
record a Sync Impact Report. plan.md MUST include a Constitution Check; analyze treats
principle violations as CRITICAL. Runtime guidance lives in CLAUDE.md.

**Version**: 2.0.0 | **Ratified**: 2026-10-01 | **Last Amended**: 2026-10-03
