---
name: loopora-run
description: "Use when the user invokes /loopora-run to start or resume the reviewed Loop preview that preserves the current task judgment and evidence requirements."
---

<!-- {{marker}} version={{version}} file=loopora-run -->

# Loopora Run

This is a thin dispatcher. Read these managed references before starting role dispatch:

- `references/loopora-run-contract.md`
- `references/loopora-recovery-matrix.md`
- `references/loopora-role-dispatch-guide.md`
- `references/loopora-result-template-guide.md`

{{run_entry_contract}}

Start or resume with:

```bash
LOOPORA_AGENT_ENTRY_SOURCE=codex_project_skill {{loopora_cli_entry}} agent codex run --workdir "$PWD" --entry-source codex_project_skill --json --compact-json
```

If the user provides `option:<id>`, pass it as `--source-option-id <id>`. If the command returns `loop_recovery`, report the recovery path and stop before dispatching any role agent.
