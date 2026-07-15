---
description: Create, revise, repair, or tighten the current OpenCode Loop preview without starting a run.
---

<!-- {{marker}} version={{version}} file=loopora-plan -->

# Loopora Plan

This is an interactive planning dispatcher. For initial message-only alignment or Web review, this entry is enough: preserve the task context and run the message-only command below; do not open the long reference before that first message-only call. Before authoring, submitting, or repairing a Loop plan file, or when typed recovery asks for more detail, read `.opencode/loopora/references/loopora-plan-contract.md` and follow it as the stable planning contract.
Use a message-only plan call when the working agreement still needs dialogue or Web review; use `--bundle-file` only after explicit confirmation or when repairing/submitting a candidate plan file.
The `--message` value should preserve the user's task context: keep concrete fake-done risks, required evidence, judgment tradeoffs, residual-risk signals, and domain objects that could change the Loop. Do not shrink a detailed `/loopora-plan` request into a title-only summary.
If the plan result returns `loop_recovery=continue_alignment_dialogue`, `status=waiting_user`, `ask_user`, or `alignment_assistant_message`, report that question to the user and stop. Do not answer it from host inference, workdir probes, Web scraping, default policy, or your own preference; rerun message-only `/loopora-plan` only after the user replies.

## Arguments

`$ARGUMENTS` may contain `fresh` or an existing candidate plan file path. Use the reference contract to decide how to map it.

Alignment or Web review:
```bash
LOOPORA_AGENT_ENTRY_SOURCE=opencode_project_command loopora agent opencode plan --workdir "$PWD" --context-id "${OPENCODE_SESSION_ID:-}" --message "<non-empty task context>" --entry-source opencode_project_command --json --compact-json
```

Confirmed bundle or repair:
```bash
LOOPORA_AGENT_ENTRY_SOURCE=opencode_project_command loopora agent opencode plan --workdir "$PWD" --context-id "${OPENCODE_SESSION_ID:-}" --message "<non-empty task context>" --bundle-file <candidate-plan-file> --entry-source opencode_project_command --json --compact-json
```

`/loopora-plan` never starts a run. If the user wants to continue execution, send them to `/loopora-run`.
