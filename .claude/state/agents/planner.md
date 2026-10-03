# planner state

## 2026-10-01 plan chain
- goal: constitution -> specify -> clarify -> plan -> tasks -> analyze for paper triage.
- status: done. speckit skills not registered as Skill tools; followed .claude/skills/speckit-*/SKILL.md by hand. No git branch/commit made.
- files: .specify/memory/constitution.md (v1.0.0), .specify/feature.json, specs/001-paper-triage/{spec,plan,research,data-model,quickstart,tasks}.md, contracts/api.md, checklists/requirements.md.
- decisions: 5 clarify Qs self-answered in spec (abstract fallback flagged; full text stored locally; ANTHROPIC_MODEL default claude-opus-5-5; non-arXiv PDF id pdf:<sha12>; chat context-stuff top 20). Separate summarizer/critic/ranker calls (3 per paper). Opus 5.5: no temperature, effort low. Mock mode also mocks HTTP (MockTransport, 0 s throttle).
- analyze: 0 CRITICAL, 0 HIGH after fixes (mock throttle vs SC-001; one-page rule made testable; http.py->net.py; T021 DESIGN re-read; plan test tree sync). LOW left: SC-001 "renders" only API-timed; md lint table spacing.
- tasks: 24 (T001-T024), MVP = T001-T017.
- next: builder T001.
NEXT:builder

## 2026-10-01 v2 amendment (wave 1 planning)
- goal: amend spec/plan/contracts/data-model/tasks for redesign, searching indicator, links, load-more, chat scope, Playwright e2e.
- status: done via Skill speckit-constitution/specify/clarify/plan/tasks/analyze + .specify/scripts/bash helpers. Constitution 1.0.0 -> 1.1.0 (pytest-playwright dev dep; offline browser e2e; chat scope = current result set).
- tasks: T027-T042. Wave D: BE T027-T033 || FE T034-T037. Wave E: FE T038-T041 || BE T042.
- decisions: chat `paper_ids` required (max 50); paging `offset`/`next_offset`/`has_more`; mock feed 15 entries with unique title marker words; FE T036 sends paper_ids early; harness triage-delay middleware in tests/ only.
- analyze: 0 CRITICAL, 0 HIGH open (2 HIGH + 5 MEDIUM fixed), 5 LOW. analysis.md write denied by harness ("subagents return findings as text"); full report in handoff for orchestrator to persist.
- next: router spawns Wave D (backend-builder || frontend-builder).
- retry: analysis.md Write rejected again (same harness message). No workaround, no commit. R1 marked noted (FE T039 follows contract) in the report text only.
BLOCKED: analysis.md write denied by harness

## 2026-10-03 v3 amendment phase 1 (specify + clarify)
- goal: amend specs/001-paper-triage/spec.md for v3 Library (save, PDF preview, tags, directories, annotations, paper chat).
- status: done via Skill speckit-specify + speckit-clarify (non-interactive); commit 753d0a5 (spec.md, checklists/requirements.md).
- added: US4-US9, FR-008a (F-006 chat clear/re-scope), FR-015..FR-029, SC-009..SC-016, 7 v3 entities, 9 edge cases, assumptions, Clarifications Session 2026-10-03 (v3): 6 router defaults + 5 planner defaults.
- planner defaults: re-save keeps first snapshot (tags merge only); paper chat transcript page-only, prepared page text persisted; mock paper chat = content-word rule, cites first matching page; 4 colors yellow/green/blue/pink, zoom-stable; load-more also clears results chat.
- blocker for plan: constitution IV cap (3 stories/15 FRs) and III scope exceeded; run speckit-constitution (2.0.0) first. PRODUCT.md lacks Library (orchestrator).
- next: wait for docs/research/v3-library-preview.md + docs/design/v3-library-brief.md, then constitution -> plan -> tasks -> analyze.

## 2026-10-03 v3 amendment phase 2 (constitution, plan, tasks, analyze)
- status: done via Skill speckit-constitution/plan/tasks/analyze + .specify helpers. Commit 7739a42.
- constitution 1.1.0 -> 2.0.0 (cap 9 stories/32 FRs; paper chat scope in III; vendored libs, no framework/build; local PDFs for saved papers).
- decisions: tags per token; 3 colors yellow/mint/peach; dir name 40; unsave always confirm (card + Library); tags auto-merge when topic search returns saved paper; pending at startup -> failed; BackgroundTasks; paper ids in body/query; find + export client-only (B8 dropped); paper chat page-only, history <=6.
- tasks T043-T065: BE 13, FE 10. Waves F (BE T043-T051 || FE T052-T056), G (BE T057-T059 || FE T060-T063), H (FE T064 || BE T065).
- analyze: 0 CRITICAL; 3 HIGH + 4 MEDIUM fixed; open: S1 (T060/T062 size), LOW T1, T2, E1. analysis.md Write denied by harness again; report in handoff.
- next: router spawns Wave F.
