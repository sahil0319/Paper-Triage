---
description: Run designer on a UI topic (brief or critique)
argument-hint: <screen/component> [brief|critique]
---
Spawn `designer` agent on $ARGUMENTS (default: brief). Inputs: PRODUCT.md, DESIGN.md, specs/001-paper-triage/{spec,contracts/api.md}, current static/ (read only). Output goes to docs/design/.
On `NEXT:frontend-builder` spawn `frontend-builder` with the brief/critique path; on `NEXT:planner` spawn `planner`. Then `tester`, then `sentinel`. Report handoff line only.
