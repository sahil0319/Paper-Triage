---
description: Run tester on latest work
---
Spawn `tester` agent: pytest (MOCK_LLM=1), ruff, MOCK_LLM e2e smoke, local no-mistakes gate (never push). Failures -> docs/qa/failures.md and back to the owning lane, backend-builder [BE] or frontend-builder [FE] (max 3 loops per task, then BLOCKED). Report handoff line only.
