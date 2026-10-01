# Checkpoint: Phase Build

## State
- phase: build
- active task: T006 (next)
- done: T001-T005 ticked + 5 commits; tester green
- next: builder T006-T010 (net, extract, input_parse, fetcher)
- decisions: tasks run in groups (builder -> tester -> sentinel); general-purpose agents for now; SDK accepts effort with messages.parse
- open failures: none
- files touched: T001-T005 commits verified in git log; untracked .claude/state/agents/{builder,tester}.md; DESIGN.md modified
- exact next command: /build T006

## Tick Verification
- T001-T005: 5 commits match git log (d5449e1 T005, e87fc36 T004, f3c519b T003, d0a7a4d T002, d5449e1 T001)
- T006-T024: pending, no commits yet

## Key Notes
- AnthropicClient wraps only APIError; T014 pipeline must handle ValidationError retry
- Use `unset VIRTUAL_ENV` for uv
- MockClient reads basis from `<paper id basis>` tag; MockTransport fixtures used for net.py testing
