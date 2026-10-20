# Checkpoint: v4 + T077 Complete

**Phase**: done (v4 + T077)

**Status**: COMPLETE. T001-T077 ticked (77/77). T077 [BE] LLM env rename committed 2c0ec7a. Tester PASS: pytest 659 x2, ruff clean, e2e 67 on 8766. Report docs/qa/T077.md.

## Summary

### Completed
- **T001-T076**: all committed (v1-v4), see previous checkpoint history in agents/tester.md
- **T077** [BE]: `LLM_PROVIDER` / `AGENT_API_KEY` / `AGENT_MODEL` replace `ANTHROPIC_*` / `OPENAI_*` (FR-011, R22). Commit 2c0ec7a.
- **README**: repo link at top. Commit ed130db.

### Git Verification
- 77 unique T-ids in commits == 77 ticked in tasks.md. 0 unticked. No mismatches.
- Tester nit: tasks.md T077 says app.py unchanged, but 2c0ec7a edits app.py (LazyClient). Doc-only mismatch.

### Test Results (latest)
- Pytest: 659 pass x2
- E2E: 67 pass (8766)
- Ruff: clean
- Report: docs/qa/T077.md

## Open Items for User

1. **.env.example**: not updated (agents permission-blocked). User edits by hand. User also renames keys in `.env`.
2. **Uncommitted spec/config edits** (planner + orchestrator): `.specify/memory/constitution.md` (2.1.0), `specs/001-paper-triage/{spec,plan,research,quickstart,tasks}.md`, `checklists/requirements.md`, `contracts/api.md`, `CLAUDE.md` defaults edit. User commits.
3. **specs/001-paper-triage/analysis.md**: not written (harness-blocked). Analyze summary in `.claude/state/agents/planner.md`: 0 CRITICAL, 0 HIGH.
4. **Not pushed**: ed130db, 2c0ec7a (push permission-blocked).
5. **tasks.md T077 nit**: says app.py unchanged; commit edits it (LazyClient). Fix text or accept.
6. **./paper_triage.db**: mutated by designer audit run (4 papers re-saved, 1 mock triage, 2401.00002 moved to "network"). User decides state.
7. **Stale worktree**: `.claude/worktrees/agent-a4628e381b8ec6bcc`, branch `worktree-agent-a4628e381b8ec6bcc`. User removes.
8. **Uncommitted docs/qa/***: tester outputs incl. docs/qa/T077.md, docs/design/v4-audit.md, docs/screenshots/ (17 PNG). User decides.
9. **Cosmetic FE**: preview load-error branch does not reset h1 title attribute. Not blocking.
10. **Proposed feature (not started)**: page transitions (View Transitions crossfade). Awaiting user approval. If approved: designer DESIGN.md §6 row -> planner T078 + analyze -> FE -> tester.
11. **No-mistakes gate**: deferred (no bare repo in `.local/`).

## Files Touched (T077 + README)
- `src/paper_triage/config.py`, `src/paper_triage/app.py` (LazyClient), LLM client modules, `tests/test_config_llm.py` (commit 2c0ec7a)
- `README.md` (ed130db)
- `docs/qa/T077.md` (uncommitted)

## Exact Next Command

None; await user. All phases complete. Await user decision on open items 1-11.

---

**DONE**: true
**Blocker**: None
**Context**: Complete
