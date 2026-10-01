---
description: Run tester on latest work
---
Spawn `tester` agent: pytest (MOCK_LLM=1), ruff, MOCK_LLM e2e smoke, local no-mistakes gate (never push). Failures -> docs/qa/failures.md and back to builder (max 3 loops per task, then BLOCKED). Report handoff line only.
