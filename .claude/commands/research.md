---
description: Run researcher on a topic
argument-hint: <topic>
---
Spawn the `researcher` agent (Agent tool, subagent_type=researcher) on: $ARGUMENTS
Output goes to docs/research/. After it returns, invoke `sentinel` to checkpoint. Report its last handoff line only.
