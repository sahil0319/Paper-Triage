# Checkpoint: Wave D complete, Wave E in progress

**Phase**: v2 build (amendment: redesign, searching indicator, paper links, chat scope, load-more, e2e browser tests)

**Active tasks**: T038-T041 (FE wave E) in progress

**Done**: T001-T037, T042 (16 tasks in v1, 16 tasks in v2 wave D)

## Wave D: PASS

Commit 63fc73e (last T033 in wave). Tester green: docs/qa/wave-d.md, 219 pytest pass, e2e 1, ruff clean.

### BE (T027-T033, T042)
- T027: abs_url/pdf_url source links on result items
- T028: 15-entry mock feed, net._feed honours start/totalResults
- T029: offset paging for topic searches (fetcher, pipeline, API)
- T030: MockClient chat answers only when question matches a context paper
- T031: chat scoped to required paper_ids (max 50)
- T032: Playwright harness (`tests/e2e_harness.py`, E2E_PORT=8766)
- T033: API-level v2 smoke, offline (links, paging, scoped chat)
- T042: README v2 (links, load-more, scoped chat, searching indicator, e2e setup)

### FE (T034-T037)
- T034: Static asset guard test (no external URLs, required hooks)
- T035: Redesign shell (tokens, nav, query band, results header, chat panel, empty state, alert)
- T036: Redesigned rendering (paper rows, rank, disclosure, turns, citations, refusal, states)
- T037: Searching indicator (cream card, verb rotation, timer, aria-live, busy state, reduced motion)

## Wave E: In progress

FE T038-T041 (BE done). Dependencies met by wave D. A2 fix (hide #empty during run) included.

### FE tasks queued
- T038: Paper links (arXiv + PDF hrefs from abs_url/pdf_url)
- T039: Load 5 more (offset paging in UI, dedupe, nextOffset, exhaustion, batch sep, flash, announcement)
- T040: Chat scope wiring (paper_ids from shown rows, scope copy, refusals, disabled empty)
- T041: Browser e2e specs (indicator, links, load-more, id search, chat out-of-scope, in-scope cite)

## Decisions

1. BE T042 (README) placed in wave D (tester deferred, not blocking FE E).
2. T038 dependencies: T027 (landed). T039 deps: T029, T037, T038 (all landed/active). T040 deps: T031, T039 (landed/queued). T041 deps: T032, T037-T040 (landed/queued).
3. A2 fix (hide #empty during working) considered "small FE polish" per advisory, not separate task.

## Open items

1. **A1 [FE]**: impeccable detect reports false positives (cramped-padding, flat-type-hierarchy). Previous run returned []. Likely CSS shorthand detector issue. Optional: expand to longhand.
2. **A3 [BE]**: mock chat cites first paper sharing a content word (per contract CHK005). Expected behavior; advisory only.
3. **analysis.md**: specs/001-paper-triage/analysis.md not persisted (planner harness blocked write). Retry when planner resumes.
4. **checklist**: specs/001-paper-triage/checklists/v2-requirements.md (28 items) left unchecked for review.
5. **no-mistakes gate**: Deferred. Needs `.local/bare.git` init + remote config. User decision.

## Files touched (this checkpoint)

- `.claude/state/checkpoint.md` (this file)
- `.claude/state/progress.json` (phase, tasks T027-T042 added, T038-T041→in-progress, DONE=false)
- `.claude/state/agents/sentinel.md` (appended)

## Exact next command

When FE wave E reports → spawn tester on T038-T041 full suite (includes e2e browser specs T041) → sentinel checkpoint → final pass (README review, no-mistakes gate optional, fresh clone feasible).

