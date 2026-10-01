---
description: Print progress.json and remaining tasks
---
!`python3 scripts/token_watch.py >/dev/null; cat .claude/state/progress.json; echo; echo "--- remaining tasks"; grep -hE '^\s*- \[ \]' specs/*/tasks.md 2>/dev/null || echo "(no tasks yet)"`

Summarize in 3 lines max.
