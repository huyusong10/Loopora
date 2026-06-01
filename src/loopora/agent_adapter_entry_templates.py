from __future__ import annotations

from loopora.agent_adapter_run_contract import (
    agent_native_run_entry_contract,
)


def codex_loopora_gen_skill(*, marker: str, version: int) -> str:
    return f"""---
name: loopora-plan
description: "Use when the user invokes /loopora-plan to create, revise, repair, or tighten the reviewed Loop preview without starting a run."
---

<!-- {marker} version={version} file=loopora-plan -->

# Loopora Plan

This is a thin dispatcher. Before authoring or repairing a Loop plan, read `references/loopora-plan-contract.md` and follow it as the stable planning contract.

```bash
LOOPORA_AGENT_ENTRY_SOURCE=codex_project_skill loopora agent codex plan --workdir "$PWD" --message "<non-empty short task summary>" --bundle-file <candidate-plan-file> --entry-source codex_project_skill
```

`/loopora-plan` never starts a run. If the user wants to continue execution, send them to `/loopora-run`; if they say `fresh`, create a new candidate and keep old runs only as history.
"""


def codex_loopora_loop_skill(*, marker: str, version: int) -> str:
    return f"""---
name: loopora-run
description: "Use when the user invokes /loopora-run to start or resume the reviewed Loop preview that preserves the current task judgment and evidence requirements."
---

<!-- {marker} version={version} file=loopora-run -->

# Loopora Run

This is a thin dispatcher. Read these managed references before starting role dispatch:

- `references/loopora-run-contract.md`
- `references/loopora-recovery-matrix.md`
- `references/loopora-role-dispatch-guide.md`
- `references/loopora-result-template-guide.md`

{agent_native_run_entry_contract().rstrip()}

Start or resume with:

```bash
LOOPORA_AGENT_ENTRY_SOURCE=codex_project_skill loopora agent codex run --workdir "$PWD" --entry-source codex_project_skill --json
```

If the user provides `option:<id>`, pass it as `--source-option-id <id>`. If the command returns `loop_recovery`, report the recovery path and stop before dispatching any role agent.
"""


def claude_loopora_gen_skill(*, marker: str, version: int) -> str:
    return f"""---
name: loopora-plan
description: "Create, revise, repair, or tighten the current Claude Code Loop preview without starting a run. Invoke manually as /loopora-plan."
disable-model-invocation: true
allowed-tools: "Bash(loopora agent claude plan *) Bash(LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude plan *) Bash(LOOPORA_HOME=* loopora agent claude plan *) Bash(LOOPORA_HOME=* LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude plan *)"
---

<!-- {marker} version={version} file=loopora-plan -->

# Loopora Plan

This is a thin dispatcher. Before authoring or repairing a Loop plan, read `references/loopora-plan-contract.md` and follow it as the stable planning contract.

```bash
LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude plan --workdir "$PWD" --context-id "${{CLAUDE_SESSION_ID}}" --message "<non-empty short task summary>" --bundle-file <candidate-plan-file> --entry-source claude_project_skill
```

`/loopora-plan` never starts a run. If the user wants to continue execution, send them to `/loopora-run`; if they say `fresh`, create a new candidate and keep old runs only as history.
"""


def claude_loopora_loop_skill(*, marker: str, version: int) -> str:
    return f"""---
name: loopora-run
description: "Start or reuse the reviewed Loop preview that preserves this Claude Code task judgment and evidence requirements. Invoke manually after /loopora-plan."
disable-model-invocation: true
allowed-tools: "Bash(loopora agent claude run *) Bash(loopora agent claude next *) Bash(loopora agent claude submit *) Bash(loopora agent claude check *) Bash(LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude *) Bash(LOOPORA_HOME=* loopora agent claude *) Bash(LOOPORA_HOME=* LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude *) Bash(loopora init claude *) Bash(LOOPORA_HOME=* loopora init claude *) Agent Task"
---

<!-- {marker} version={version} file=loopora-run -->

# Loopora Run

This is a thin dispatcher. Read these managed references before starting role dispatch:

- `references/loopora-run-contract.md`
- `references/loopora-recovery-matrix.md`
- `references/loopora-role-dispatch-guide.md`
- `references/loopora-result-template-guide.md`

{agent_native_run_entry_contract().rstrip()}

Start or resume with:

```bash
LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude run --workdir "$PWD" --context-id "${{CLAUDE_SESSION_ID}}" --entry-source claude_project_skill --json
```

If the user provides `option:<id>`, pass it as `--source-option-id <id>`. If the command returns `loop_recovery`, report the recovery path and stop before dispatching any role agent.
"""


def opencode_loopora_gen_command(*, marker: str, version: int) -> str:
    return f"""---
description: Create, revise, repair, or tighten the current OpenCode Loop preview without starting a run.
---

<!-- {marker} version={version} file=loopora-plan -->

# Loopora Plan

This is a thin dispatcher. Before authoring or repairing a Loop plan, read `.opencode/loopora/references/loopora-plan-contract.md` and follow it as the stable planning contract.

## Arguments

`$ARGUMENTS` may contain `fresh` or an existing candidate plan file path. Use the reference contract to decide how to map it.

```bash
LOOPORA_AGENT_ENTRY_SOURCE=opencode_project_command loopora agent opencode plan --workdir "$PWD" --context-id "${{OPENCODE_SESSION_ID:-}}" --message "<non-empty short task summary>" --bundle-file <candidate-plan-file> --entry-source opencode_project_command
```

`/loopora-plan` never starts a run. If the user wants to continue execution, send them to `/loopora-run`.
"""


def opencode_loopora_loop_command(*, marker: str, version: int) -> str:
    return f"""---
description: Start or reuse the reviewed Loop preview that preserves this OpenCode task judgment and evidence requirements.
agent: loopora-orchestrator
subtask: true
---

<!-- {marker} version={version} file=loopora-run -->

# Loopora Run

This is a thin dispatcher. Read these managed references before starting role dispatch:

- `.opencode/loopora/references/loopora-run-contract.md`
- `.opencode/loopora/references/loopora-recovery-matrix.md`
- `.opencode/loopora/references/loopora-role-dispatch-guide.md`
- `.opencode/loopora/references/loopora-result-template-guide.md`

{agent_native_run_entry_contract().rstrip()}

Start or resume with:

```bash
LOOPORA_AGENT_ENTRY_SOURCE=opencode_project_command loopora agent opencode run --workdir "$PWD" --context-id "${{OPENCODE_SESSION_ID:-}}" --entry-source opencode_project_command --json
```

If `$ARGUMENTS` or the user provides `option:<id>`, pass it as `--source-option-id <id>`. If the command returns `loop_recovery`, report the recovery path and stop before dispatching any role agent.
"""
