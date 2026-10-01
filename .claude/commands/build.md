---
description: Run builder on next (or given) task
argument-hint: [task-id]
---
Spawn `builder` agent for task: ${ARGUMENTS:-next unticked task in specs/*/tasks.md}. It uses speckit-implement, one task, one commit. UI task -> it must re-read DESIGN.md + PRODUCT.md first.
After DONE: run /test flow (tester), then `sentinel`. Report handoff line only.
