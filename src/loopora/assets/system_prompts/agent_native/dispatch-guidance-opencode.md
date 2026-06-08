OpenCode native dispatch guidance:
- `/loopora-run` is an OpenCode project command assigned to `agent: loopora-orchestrator` with `subtask: true`; keep role work inside that host-native OpenCode subtask flow.
- From `loopora-orchestrator`, use OpenCode's native task/agent capability for the exact `role_dispatch.target_agent`; do not run `opencode`, `codex`, or `claude` as a nested provider CLI.
- Pass only the step/context/template paths plus compact anchors such as coverage target IDs, action policy, required coverage status, known evidence IDs, and relevant artifact paths to the role agent. Tell it to open local paths for the full prompt, output schema, judgment contract, evidence rules, and known evidence details. Do not pass full CLI JSON, full run payloads, large file contents, full schemas, full evidence ledger rows, or unrelated transcript history.
- Ask the role agent to return the required raw JSON wrapper directly, with no Markdown fence or prose.
- Use OpenCode's native `task` mechanism and project command orchestrator status only as user-visible progress; todo, host status, and native trace are not Loopora proof.
- If OpenCode exposes a task trace or tool-call id, copy it into `loopora_host_dispatch.native_trace` or `native_trace_ref`; otherwise leave optional trace fields empty.
- If OpenCode cannot invoke the named role agent, or the role task returns no wrapper / no structured output, report native dispatch unavailable and stop before submit.
