# Checkpoint: v3 Amendment in Progress

**Phase**: v3 planning (v2 complete, v3 research + design + spec phase 1 done; planner phase 2 queued)

**Status**: Fixes F-006/F-007/F-008 shipped and verified GREEN. v3 user request research, design brief, and spec amendment committed. Planner ready for phase 2.

## Summary

v2 project (T001-T042) complete and tested (236 pytest pass, 15 e2e stable, ruff clean).

v3 user request live: save papers to local library; in-app PDF preview (pdfjs-dist vendored, Range-served); keyword tags with AND multi-select; user directories; PDF annotations (highlights 3 colors, notes); per-paper chat (transcript page-only); chat disabled when no PDF.

Research + design + spec amendment (phase 1) complete:
- docs/research/v3-library-preview.md: pdfjs-dist 6.3.289 vendor option, pypdf per-page text, FileResponse Range support, arXiv throttle.
- docs/design/v3-library-brief.md (Rev 2): L1-L24 FE items (Library sidebar, save/unsave, tags, directories, PDF viewer, chat), B1-B8 BE needs (save paper, PDF serve, tags CRUD, etc).
- PRODUCT.md Library draft: docs/design/product-md-library-draft.md (user to paste when ready).
- specs/001-paper-triage/spec.md commit 753d0a5: US4-US9 (save/unsave/tagging stories), FR-008a (F-006 chat clear/rescope), FR-015..029 (Library features), SC-009..016 (PDF viewer, annotations, per-paper chat scenarios), 7 new entities, 9 edge cases, assumptions.

## Fixes shipped (v2 tail)

**F-006** (c205d59): load-more and new search clear chat transcript and rescope to new paper set.
- Root: transcript never cleared.
- Fix: resetChat() appends scope sentence to #status (once per result-set change).
- Verify: docs/qa/F-006.md (tester e2e 12 x3 stable, pytest 233 pass).

**F-007/F-008** (c911fa1): chat reset announced once in #status; #ask re-enabled after stale reply settles.
- Root: reset announced per row; Ask disabled during in-flight reply.
- Fix: resetChat appends scope once via observer pattern; stale replies dropped via chatGen.
- Verify: tester e2e 15 x3 stable, pytest 236 pass; docs/qa/failures.md + F-006.md.

## v2 test results (final)

- Pytest: 236 pass (MOCK_LLM=1 offline)
- E2E: 15 pass (x3 stable, Playwright chromium, E2E_PORT 8766)
- Ruff: clean
- Repo: .db/.env ignored, no secrets, uv.lock tracked

## User decisions (v3 all approved)

- Constitution 2.0.0 scope bump (added Library stories/features).
- Paper chat page-only (not full-text).
- PDF cap 50 MB.
- Re-save keeps first snapshot; tags merge.
- Direct PDF URLs savable (pdf:<sha12> ids).
- Evergreen browsers, modern pdf.js.
- Notes don't feed chat.
- Vendored pdf.js approved.
- 3 highlight colors: yellow, green, blue.
- Chat disabled when no PDF.
- Unsave confirms and deletes PDF + annotations.

## In progress

**Planner phase 2**: Constitution 2.0.0 → specify/clarify/plan/tasks/analyze for v3 features.
- Input: v3 user request + research + design.
- Output: constitution.md 2.0.0, amended spec.md, data-model.md, contracts (api.md v3), tasks T043+ with Lanes/waves, analysis.md.
- Blocker resolved: phase 1 complete (spec.md amended); ready to start.

## Open items

1. **analysis.md**: planner phase 2 will write specs/001-paper-triage/analysis.md (speckit-analyze output).
2. **PRODUCT.md**: user to paste Library section from docs/design/product-md-library-draft.md (orchestrator action).
3. **Checklist**: specs/001-paper-triage/checklists/v2-requirements.md 11/28 ticked; v3 checklists TBD after phase 2.
4. **No-mistakes gate**: deferred (needs .local/bare.git).

## Files touched

- `.claude/state/checkpoint.md` (this file)
- `.claude/state/progress.json` (phase, tasks, DONE=false, context_pct)
- `.claude/state/agents/sentinel.md` (appended)

## Next

When planner reports phase 2 done → spawn backend-builder + frontend-builder in parallel on v3 wave 1 per Lanes section in tasks.md → tester → sentinel.
