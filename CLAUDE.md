# CLAUDE.md — orchestrator rules

**FIRST on every session start: read `.claude/state/checkpoint.md`, then continue from "exact next command".**
(SessionStart hook injects it too.) Keep all messages terse. Use `/caveman lite` for agent-to-agent notes/handoffs only.

## Product
Paper Triage Assistant. Input: topic/keywords or arXiv IDs / PDF URLs.
Pipeline: Fetcher -> Summarizer -> Critic -> Ranker (0-10 + reason). Then grounded chat over stored papers (cites paper ids, refuses outside stored data).
Scope: one page of spec. No auth, no multi-user, no deployment.

## Defaults (decided; do not re-ask)
Python 3.11+, FastAPI, SQLite, Anthropic SDK (model via `ANTHROPIC_MODEL` env, key via `ANTHROPIC_API_KEY`), single-page web UI (vanilla HTML/JS, no framework), pytest + ruff, uv for env.
`MOCK_LLM=1` -> canned responses; all tests must run offline. Product code in `src/`, tests in `tests/`, one module + prompt file per runtime agent.
Design: DESIGN.md (user-supplied Apple style; real spec in place since 2026-10-01) + PRODUCT.md. Re-read both before UI work.

## DEV vs RUNTIME (do not confuse)
- RUNTIME agents = the product's code: fetcher, summarizer, critic, ranker, chat. Live in `src/`.
- DEV agents = build crew in `.claude/agents/`: researcher, planner, backend-builder, frontend-builder, tester, sentinel. (impeccable-* agents are tool-provided; ignore unless doing UI polish.)

## Roster
| agent | model | writes | owns |
|---|---|---|---|
| researcher | sonnet | docs/research/ | research notes |
| planner | opus | specs/, .specify/ | speckit-constitution/specify/clarify/plan/tasks/analyze |
| backend-builder [BE] | sonnet | src/paper_triage/** except static/, tests/ except tests/frontend/, pyproject, README | speckit-implement (BE tasks) |
| frontend-builder [FE] | sonnet | src/paper_triage/static/**, tests/frontend/** | speckit-implement (FE tasks); re-reads DESIGN.md + PRODUCT.md every task |
| tester | sonnet | docs/qa/ | speckit-checklist, pytest, ruff, e2e, no-mistakes gate |
| sentinel | haiku | .claude/state/ | checkpoints |
Subagents can't spawn subagents: the main session is the only router.

## Pipeline
research -> plan -> build (BE and FE lanes IN PARALLEL) <-> test loop -> checkpoint -> README + final test pass.
Slash: /research /plan /build (both lanes) /build-be /build-fe /test /checkpoint /resume /status.
Tasks in tasks.md carry a lane tag [BE]/[FE] (T021 is [BE+FE], API half first). Waves: see "Lanes" in tasks.md.
Per wave: spawn backend-builder AND frontend-builder in the same message (background) -> when both report, tester (failures tagged [BE]/[FE], back to the owning lane, max 3 loops per task, then BLOCKED) -> sentinel.
Parallel safety: disjoint file ownership; each lane commits only its own paths (`git commit -m ... -- <paths> tasks.md`), never `git add -A`/stash/reset; FE uses port 8765, tester 8766. API handoff FE<-BE via specs/001-paper-triage/contracts/api.md + "API facts" in .claude/state/agents/backend-builder.md. FE gaps are reported as `NEEDS-BE:` and routed by the orchestrator.

## Handoff format
Every agent ends with exactly one line: `DONE` | `BLOCKED: <why>` | `NEXT:<agent>`.
Each agent appends to `.claude/state/agents/<name>.md` after every task: goal, status, findings, next step.

## Checkpoint rules
- `.claude/state/checkpoint.md` (human) + `progress.json` (machine: phase, tasks, last_checkpoint_ts, context_pct, DONE).
- PostToolUse hook runs `scripts/token_watch.py` (estimates context vs `CONTEXT_WINDOW`, default 200000). >=70%: invoke sentinel, finish current task only. >=85%: checkpoint immediately and stop.
- PreCompact -> `scripts/save_checkpoint.sh`. SessionStart injects checkpoint.md.
- `scripts/run_loop.sh` restarts on usage limit/crash (max 20 iters, stops on DONE). No `--dangerously-skip-permissions`.

## Hard rules
- One task = one small commit (per lane). Never push; no real remotes. no-mistakes gate is local only (bare repo in `.local/`).
- `.env` ignored; no secrets in commits. Stay inside project dir.
- Don't install ECC or extra tooling beyond SETUP_LOG.md.
