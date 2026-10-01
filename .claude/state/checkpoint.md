# Checkpoint: Wave A/B Build

**Phase**: build (parallel FE/BE lanes)

**Active task**: T023 (FE polish, in flight)

**Done**: T001-T022, T024 (all ticked in tasks.md, all committed)

**Next phase**: tester (final pass on FE+README after T023 lands)

## Status by wave

### BE wave A (verified green, tester docs/qa/BE-wave-A.md)
- T014 pipeline: PASS (single retry, per-paper failure tracking)
- T015 app: PASS (status/triage/papers/static)
- T018 chat: PASS (empty refusal, citation validation)
- T019 chat API: PASS (persistence, 422 on blank)
- T021(api): PASS (stored results survive app restart)
- T022 e2e: PASS (6/6 offline smoke scenarios < 5s)

### FE wave A/B (committed, not yet tested)
- T016 UI structure: committed (406cfe7)
- T017 triage flow: committed (cb8e547), includes keyboard input, error states, critique details
- T020 chat UI: committed (9a4afc3), citations as links, refusal state distinct
- T021(ui): committed (0c025df), loads status and stored papers on page load
- T023 polish: in flight (a11y focus, contrast, reduced-motion, narrow layout)

### BE wave C
- T024 README: committed (e477903), not yet tested (depends on T023 merge)

## Decisions

- Builder split into backend-builder / frontend-builder lanes (b88da4c workflow commit)
- App does not load .env; README documents `source .env.example && export ...`
- No-mistakes init deferred (user decision pending on local bare origin)
- FE port 8765, tester port 8766
- T021 split: api landed first (ca2e161), ui then ticked the task (0c025df)

## Open failures

None. No entries in failures.md.

## Files touched (this checkpoint)

- .claude/state/checkpoint.md (this file)
- .claude/state/progress.json (task statuses + last_checkpoint_ts)
- .claude/state/agents/builder.md (appended wave A/B summary)
- .claude/state/agents/tester.md (no edit needed, BE wave A result already there)

## Verification

**Ticks vs git log match**: all 25 ticked tasks (T001-T022, T024) have commits; T023 unticked, no commit. ✓

**Context**: currently 67.8%; post-token-watch will update.

**DONE flag**: false (pending final tester pass on FE+README after T023).

## Exact next command

After T023 commits: `uv run pytest -q MOCK_LLM=1` (full suite) + ruff, then tester reports. If green → sentinel sets DONE=true and checkpoints final. If failure → looped builder up to 3 tries, then BLOCKED.

Current: await T023 commit, then invoke tester.
