# Specification Analysis Report: v3 Amendment

**Feature**: 001-paper-triage
**Date**: 2026-10-03
**Source**: `speckit-analyze` run by the planner agent at commit 7739a42. The harness blocks subagents from writing report files, so the main session persisted this report verbatim from the planner's handoff (one-time exception approved by the user).

## Scope

- spec.md: FR-008a, FR-015..FR-029, SC-009..SC-016, user stories US4-US9
- plan.md (v3 section), contracts/api.md (v3 endpoints), data-model.md (v3 entities)
- tasks.md: T043-T065
- Constitution 2.0.0 (`.specify/memory/constitution.md`)
- Design brief Rev 2 (`docs/design/v3-library-brief.md`)

## Findings

| ID | Severity | Summary | Status |
|----|----------|---------|--------|
| I1 | HIGH | US4 scenario 3 depended on re-saving from the card; now uses the automatic tag merge when a topic search returns an already saved paper. | Fixed |
| I2 | HIGH | Downloads still pending at restart: the spec said "resumed or retried". They are now marked failed everywhere, with Retry. | Fixed |
| I3 | HIGH | FR-029 now requires confirmation for unsave and directory delete, and Undo for highlight delete. | Fixed |
| I4 | MEDIUM | US9 scenario 4 now states the chat input is disabled when the paper has no PDF. | Fixed |
| C1 | MEDIUM | Library scroll position restored on return from preview (T053). | Fixed |
| C2 | MEDIUM | T064 now asserts the 5 s PDF-ready and 2 s first-page budgets. | Fixed |
| C3 | MEDIUM | T062 now shows a message for scanned pages with no selectable text. | Fixed |
| S1 | MEDIUM | T060 and T062 are large; builders may split each into two commits under the same task id. | Open |
| U1 | LOW | `.mjs` MIME test wording. | Fixed |
| A1 | LOW | "Stored PDF" wording. | Fixed |
| P1 | LOW | Plan wording. | Fixed |
| T1 | LOW | Terminology: spec says "score", API says "rank". | Open |
| T2 | LOW | API status names differ from the brief's UI labels; contracts/api.md maps them. | Open |
| E1 | LOW | Edge case "unsave while preview is open" is nearly moot. | Open |

## Metrics

- CRITICAL: 0
- HIGH: 3 (3 fixed)
- MEDIUM: 5 (4 fixed, 1 open: S1)
- LOW: 6 (3 fixed: U1, A1, P1; 3 open: T1, T2, E1)

## Coverage

24 of 24 v3 requirements (100%) map to at least one task. FR-008a (chat reset on result-set change) is covered by the already-shipped fixes F-006 (c205d59) and F-007/F-008 (c911fa1).

## Constitution Check (2.0.0)

- Scope cap raised to 9 user stories and 32 FRs; the spec has 9 stories and 31 FRs. Pass.
- Principle III (grounded chat) now includes the per-paper chat scope. Pass.
- Vendored front-end libraries allowed (no CDN, no framework, no build step); pdf.js is vendored under `static/vendor/pdfjs/`. Pass.

## Next Actions

No CRITICAL or HIGH issues remain; implementation can proceed (Waves F-H). Open MEDIUM/LOW items are advisory.
