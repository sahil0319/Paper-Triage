---
description: Run backend-builder and frontend-builder IN PARALLEL on the next wave
argument-hint: [wave A|B|C | task-ids]
---
Read "Lanes" in specs/001-paper-triage/tasks.md. Pick the next unticked tasks per lane (or those in $ARGUMENTS). In ONE message spawn `backend-builder` and `frontend-builder` (Agent tool, run_in_background) with their lane's task ids; skip a lane with nothing unblocked. Tell each the other lane is running in parallel. FE tasks that need an unlanded BE endpoint (e.g. T020 needs T019) wait for the next wave.
When both report: `tester` on both lanes, route tagged failures back to the owning lane, then `sentinel`. Report handoff lines only.
