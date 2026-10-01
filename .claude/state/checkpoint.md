# Checkpoint
- phase: build (parallel lanes)
- done: T001-T016 (T014,T015 BE; T016 FE committed 406cfe7)
- in flight: T017 FE: partial uncommitted src/paper_triage/static/app.js from the stopped builder; frontend-builder continues it
- next wave A: BE T018 -> T019 -> T021(api) -> T022 || FE T017 -> T021(ui). Wave B: FE T020 (needs T019), T023. Wave C: BE T024
- decisions: builder split into backend-builder/frontend-builder; tester single, tags failures [BE]/[FE]; no-mistakes init still deferred (user decision on local origin pending); FE port 8765, tester 8766
- open failures: none
- exact next command: /build  (wave A)
