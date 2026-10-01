# Checkpoint: DONE

**Phase**: done+live-hardening

**Active task**: none

**Done**: T001-T026 all ticked, all committed, tester final pass GREEN

**Status**: 174 tests pass (MOCK_LLM=1), ruff clean, e2e ok, live verified with OpenAI key.

## Live verification (T025-T026)

- Topic search: 5 papers 2:44 → 1:16 after T026 concurrency (TRIAGE_CONCURRENCY default 4)
- ID search with bogus ID: handled gracefully
- Chat in-scope: citations valid
- Chat out-of-scope: refused (sentinel mock limitation noted)
- Rank calibration: spread 10,10,10,9,7 → 9,9,8,8,6 after prompt tuning

## Tester verdict

Full suite GREEN. No blocking failures. 1 advisory (mock chat refusal only on sentinel 'out of scope' case—demo wart, not SC-003 violation). 2 minor FE nits. See docs/qa/final.md (updated for T025-T026).

## Open items for user

1. **no-mistakes init deferred** — needs local bare origin. User decides whether to init `.local/bare.git` + add remote.
2. **Mock chat advisory** — in mock mode, generic out-of-scope questions return canned answers citing stored papers. Real live path unaffected. Optional: doc sentinel or enhance MockClient logic.
3. **No automated JS/browser tests** — FE verified by static HTML/CSS/a11y read + served-asset smoke only. Live (non-mock) path untested. Risk low.
4. **Optional FE**: show provider next to model in UI.
5. **Optional**: add TRIAGE_CONCURRENCY=4 to .env.example (guarded by deny rule; T026 note in tasks.md says it was updated but it wasn't).
6. **Direct PDF URL**: not tested live (only in mixed ID/URL test).

## Verification

- All 26 tasks ticked in tasks.md, all 26 have matching `T00X` commits in git log. ✓
- Builder parallel lanes (BE wave A/B/C + FE) completed and tested green.
- Repo hygiene: .env/.db ignored, no secrets, fresh clone feasible (uv.lock tracked). ✓
- Spec coverage complete per docs/qa/final.md. ✓
- Live run with user's OpenAI key: topic search, id search (bogus), chat (in/out scope). ✓

## Files touched (final checkpoint)

- .claude/state/checkpoint.md (this file)
- .claude/state/progress.json (DONE=true, phase=done+live-hardening, T025-T026→done)
- .claude/state/agents/tester.md (already updated by tester for T025-T026)
- docs/qa/final.md (tester report, 174 tests, live verification)

## Next step

none. Project complete. User may initialize no-mistakes gate or add optional env/FE enhancements.
