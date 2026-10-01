# Checkpoint: Phase Build

## State
- phase: build
- active task: T014 (next)
- done: T001-T013 all ticked + 13 commits verified in git log; tester green (docs/qa/T001-T005, T006-T010, T011-T013)
- next: builder T014-T017 (pipeline, API, UI structure, UI triage flow)
- decisions:
  - Groups of tasks per builder/tester cycle
  - Native dev agents now registered
  - DESIGN.md is the real Apple-style spec (committed 4cc32b0) -> UI tasks T016,T017,T020,T021,T023 must re-read it
  - No-mistakes init deferred (needs origin, user decision pending)
  - Agents propagate LLMError/LLMRefusal/ValidationError so T014 pipeline owns single retry
  - Use `unset VIRTUAL_ENV` for uv
  - Ruff format not part of gate
- open failures: none (F-001 resolved in e52a67a)
- files touched: T001-T013 commits verified in git log; .claude/state/agents/{builder,tester}.md created (untracked); DESIGN.md modified (4cc32b0); docs/qa/ created with tester results; progress.json modified
- exact next command: /build T014

## Tick Verification
- T001-T013: 13 commits match git log
  - T001: d5449e1 project scaffold
  - T002: d0a7a4d env-driven Settings
  - T003: f3c519b pydantic models
  - T004: e87fc36 LLM wrapper with mock twin
  - T005: 427767d sqlite db layer
  - T006: 37956f3 net throttle, mock http transport, fixtures
  - T007: be9a0b5 pypdf text extraction and LLM text prep
  - T008: 540fa7f parse query into topic and items
  - T009: bd4bb10 fetcher arXiv search and by_ids with cache and throttle
  - T010: 10c9a7b fetcher PDF download, full text, direct URLs, reuse
  - T011: b307041 summarizer agent, prompt, shared prompting helpers
  - T012: 78d714f critic agent and prompt
  - T013: 55df157 ranker agent and prompt
- F-001: e52a67a fix host-less URL gives fetch error entry, not crash
- T014-T024: pending, no commits yet

## Key Notes
- AnthropicClient wraps only APIError; T014 pipeline must handle ValidationError retry
- Use `unset VIRTUAL_ENV` for uv
- MockClient reads basis from `<paper id basis>` tag; MockTransport fixtures used for net.py testing
- UI tasks must re-read DESIGN.md and PRODUCT.md for Apple-style design patterns
