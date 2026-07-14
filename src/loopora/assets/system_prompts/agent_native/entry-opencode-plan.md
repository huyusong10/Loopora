---
description: Create, revise, repair, or tighten the current OpenCode Loop preview without starting a run.
---

<!-- {{marker}} version={{version}} file=loopora-plan -->

# Loopora Plan

This is a host-native interactive planning dispatcher. Keep planning in the current main session; do not start a nested provider CLI or make the message-only CLI call as the first planning action.
Preserve the user's complete task judgment. If Loopora fit or a Loop-shaping decision is missing, ask one focused question with a recommended answer and wait. Otherwise present a draft working agreement covering fit, outcome, fake-done risks, evidence, execution strategy, tradeoffs, residual-risk policy, and local governance, then wait for explicit confirmation.
Only after explicit confirmation, read `.opencode/loopora/references/loopora-plan-contract.md`, author a complete candidate under `.loopora/agent_inbox/opencode/`, and submit it with `--bundle-file`. Repair and resubmit the same candidate when validation asks.
Use the message-only command only when this host cannot continue the main-session dialogue or the user explicitly chooses Web review. That fallback may start a separate alignment executor and does not prove a candidate is ready.

## Arguments

`$ARGUMENTS` may contain `fresh` or an existing candidate plan file path. Use the reference contract to decide how to map it.

Confirmed candidate or repair:
```bash
LOOPORA_AGENT_ENTRY_SOURCE=opencode_project_command {{loopora_cli_entry}} agent opencode plan --workdir "$PWD" --context-id "${OPENCODE_SESSION_ID:-}" --message "<confirmed task context>" --bundle-file <candidate-plan-file> --entry-source opencode_project_command --json --compact-json
```

Non-interactive or Web fallback:
```bash
LOOPORA_AGENT_ENTRY_SOURCE=opencode_project_command {{loopora_cli_entry}} agent opencode plan --workdir "$PWD" --context-id "${OPENCODE_SESSION_ID:-}" --message "<non-empty task context>" --entry-source opencode_project_command --json --compact-json
```

`/loopora-plan` never starts a run. If the user wants to continue execution, send them to `/loopora-run`.
