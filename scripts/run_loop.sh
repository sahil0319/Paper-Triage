#!/usr/bin/env bash
# Restart loop for usage-limit / crash. Stops when progress.json DONE=true or after MAX_ITER.
# No --dangerously-skip-permissions; allowed tools come from .claude/settings.local.json.
set -u
cd "$(cd "$(dirname "$0")/.." && pwd)"
MAX_ITER="${MAX_ITER:-20}"
SLEEP_DEFAULT="${SLEEP_DEFAULT:-1800}"
PROMPT="Resume from .claude/state/checkpoint.md and continue until all tasks in tasks.md are done, then set DONE in progress.json"
mkdir -p .claude/state/loop

is_done() { python3 -c "import json,sys; sys.exit(0 if json.load(open('.claude/state/progress.json')).get('DONE') else 1)" 2>/dev/null; }

# seconds until reset if message has "resets at 3pm" / "reset at 15:00"; else default
parse_wait() {
  python3 - "$1" "$SLEEP_DEFAULT" <<'PY'
import re,sys,datetime as dt
txt,default=sys.argv[1],int(sys.argv[2])
m=re.search(r'reset[s]?(?: at)?\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?',txt,re.I)
if not m: print(default); sys.exit()
h,mi,ap=int(m.group(1)),int(m.group(2) or 0),(m.group(3) or '').lower()
if ap=='pm' and h<12: h+=12
if ap=='am' and h==12: h=0
if h>23: print(default); sys.exit()
now=dt.datetime.now(); t=now.replace(hour=h,minute=mi,second=0,microsecond=0)
if t<=now: t+=dt.timedelta(days=1)
print(int((t-now).total_seconds())+60)
PY
}

for i in $(seq 1 "$MAX_ITER"); do
  is_done && { echo "DONE flag set. Stopping."; exit 0; }
  log=".claude/state/loop/iter-$i.log"
  echo "[$(date)] iteration $i/$MAX_ITER"
  claude -p "$PROMPT" --continue --permission-mode acceptEdits >"$log" 2>&1
  rc=$?
  cat "$log" | tail -20
  is_done && { echo "DONE flag set. Stopping."; exit 0; }
  if grep -qiE 'usage limit|rate limit|limit reached|resets? at|429|overloaded' "$log"; then
    w=$(parse_wait "$(tail -40 "$log")")
    echo "Limit hit (rc=$rc). Sleeping ${w}s."
    sleep "$w"
  elif [ "$rc" -ne 0 ]; then
    echo "Crash rc=$rc. Retry in 30s."
    sleep 30
  fi
done
echo "Reached $MAX_ITER iterations without DONE."
exit 1
