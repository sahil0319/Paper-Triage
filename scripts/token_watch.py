#!/usr/bin/env python3
"""Estimate context-window use from the active session transcript.

Usage:
  token_watch.py            print JSON (finds latest transcript under ~/.claude/projects/)
  token_watch.py --hook     PostToolUse hook: reads hook JSON on stdin, may emit additionalContext
Writes context_pct into .claude/state/progress.json.
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parent.parent)
PROGRESS = ROOT / ".claude/state/progress.json"
WINDOW = int(os.environ.get("CONTEXT_WINDOW", "200000"))
WARN, STOP = 70, 85


def find_transcript(hint=None):
    if hint and Path(hint).is_file():
        return Path(hint)
    slug = str(ROOT).replace("/", "-").replace(".", "-")
    base = Path.home() / ".claude/projects"
    files = list((base / slug).glob("*.jsonl")) or list(base.glob("*/*.jsonl"))
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def last_usage(path):
    """Usage of the most recent main-chain assistant message."""
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - 2_000_000))
        lines = f.read().decode("utf-8", "ignore").splitlines()
    for line in reversed(lines):
        if '"usage"' not in line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") != "assistant" or d.get("isSidechain"):
            continue
        u = (d.get("message") or {}).get("usage")
        if u:
            return u
    return None


def read_progress():
    try:
        return json.loads(PROGRESS.read_text())
    except (OSError, ValueError):
        return {}


def write_progress(p):
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    tmp = PROGRESS.with_suffix(".tmp")
    tmp.write_text(json.dumps(p, indent=2) + "\n")
    os.replace(tmp, PROGRESS)


def measure(hint=None):
    path = find_transcript(hint)
    u = last_usage(path) if path else None
    used = 0
    if u:
        used = (u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
                + u.get("cache_read_input_tokens", 0))
    return {"context_used": used, "context_window": WINDOW,
            "context_pct": round(100 * used / WINDOW, 1), "transcript": str(path) if path else None}


def main():
    hook = "--hook" in sys.argv
    hint = None
    if hook:
        try:
            hint = json.loads(sys.stdin.read() or "{}").get("transcript_path")
        except ValueError:
            pass
    m = measure(hint)
    p = read_progress()
    p["context_pct"] = m["context_pct"]
    pct = m["context_pct"]
    level = 2 if pct >= STOP else 1 if pct >= WARN else 0
    msg = None
    if hook and level:
        # re-warn only when level rises, or after a checkpoint made since last warning
        stale = (p.get("last_checkpoint_ts") or 0) > (p.get("last_warn_ts") or 0)
        if level > p.get("last_warn_level", 0) or stale:
            msg = ("Context ~%.0f%%. Checkpoint immediately and stop: invoke sentinel, then end the session."
                   if level == 2 else
                   "Context ~%.0f%%. Invoke sentinel to checkpoint now, finish current task only.") % pct
            p["last_warn_level"], p["last_warn_ts"] = level, time.time()
    elif level == 0:
        p["last_warn_level"] = 0
    write_progress(p)
    if hook:
        if msg:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}}))
    else:
        print(json.dumps(m))


if __name__ == "__main__":
    main()
