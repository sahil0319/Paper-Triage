---
description: Run planner chain (constitution, specify, clarify, plan, tasks, analyze)
---
Spawn `planner` agent. Order: speckit-constitution -> speckit-specify -> speckit-clarify (resolve with defaults) -> speckit-plan -> speckit-tasks -> speckit-analyze. Loop until analyze has zero CRITICAL. Inputs: PRODUCT.md, DESIGN.md, docs/research/*.
Then invoke `sentinel`. Report handoff line only.
