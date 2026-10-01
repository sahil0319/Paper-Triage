#!/usr/bin/env bash
# SessionStart hook: inject checkpoint.md as additionalContext.
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
F="$ROOT/.claude/state/checkpoint.md"
[ -f "$F" ] || exit 0
python3 - "$F" <<'PY'
import json,sys
txt=open(sys.argv[1]).read()
print(json.dumps({"hookSpecificOutput":{"hookEventName":"SessionStart",
 "additionalContext":"Resume from here (read .claude/state/checkpoint.md rules in CLAUDE.md):\n"+txt}}))
PY
