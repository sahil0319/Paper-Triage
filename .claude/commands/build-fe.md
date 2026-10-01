---
description: Run frontend-builder only
argument-hint: [task-id...]
---
Spawn `frontend-builder` for: ${ARGUMENTS:-next unticked [FE] tasks in specs/001-paper-triage/tasks.md}. It must re-read DESIGN.md + PRODUCT.md first. Then tester, then sentinel. Report handoff line only.
