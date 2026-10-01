#!/usr/bin/env bash
# PreCompact hook: snapshot progress.json + git status + tasks.md state. No commit (sentinel commits).
set -u
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ROOT" || exit 0
S=.claude/state
mkdir -p "$S/snapshots"
ts=$(date +%Y%m%d-%H%M%S)
{
  echo "# PreCompact snapshot $ts"
  echo "## progress.json"; cat "$S/progress.json" 2>/dev/null
  echo; echo "## git status"; git status --short 2>/dev/null
  echo; echo "## git log (10)"; git log --oneline -10 2>/dev/null
  echo; echo "## tasks.md"
  for f in specs/*/tasks.md; do [ -f "$f" ] && { echo "### $f"; grep -E '^\s*- \[[ xX]\]' "$f"; }; done
} > "$S/snapshots/precompact-$ts.md"
# keep last 5
ls -1t "$S"/snapshots/precompact-*.md 2>/dev/null | tail -n +6 | xargs -I{} rm -f {}
python3 - <<PY
import json,time
p=".claude/state/progress.json"
d=json.load(open(p)); d["last_precompact_ts"]=time.time()
json.dump(d,open(p,"w"),indent=2)
PY
exit 0
