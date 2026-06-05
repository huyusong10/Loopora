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
LOOPORA_AGENT_ENTRY_SOURCE=codex_project_skill loopora agent codex plan --workdir "$PWD" --message "<non-empty short task summary>" --bundle-file <candidate-plan-file> --entry-source codex_project_skill --json --compact-json
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
LOOPORA_AGENT_ENTRY_SOURCE=codex_project_skill loopora agent codex run --workdir "$PWD" --entry-source codex_project_skill --json --compact-json
```

If the user provides `option:<id>`, pass it as `--source-option-id <id>`. If the command returns `loop_recovery`, report the recovery path and stop before dispatching any role agent.
"""


def claude_loopora_gen_skill(*, marker: str, version: int) -> str:
    return f"""---
name: loopora-plan
description: "Manual /loopora-plan entry. If the Skill tool reports disable-model-invocation, stay in the main session and run the Bash command below."
disable-model-invocation: true
allowed-tools: "Bash(loopora agent claude plan *) Bash(LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude plan *) Bash(LOOPORA_HOME=* loopora agent claude plan *) Bash(LOOPORA_HOME=* LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude plan *)"
---

<!-- {marker} version={version} file=loopora-plan -->

# Loopora Plan

Create, revise, repair, or tighten the current Claude Code Loop preview without starting a run.
This is a thin dispatcher. Before authoring or repairing a Loop plan, read `references/loopora-plan-contract.md` and follow it as the stable planning contract.
If Claude Code's Skill tool reports `disable-model-invocation`, do not invoke `Agent` or `Task` to simulate `/loopora-plan`; stay in the main session, read this file/reference, and run the Bash command below.
Do not inspect `$HOME/.claude`, global skill directories, Loopora manifests, binary/PATH probes such as `which loopora`, `command -v loopora`, `type loopora`, `echo $PATH`, `loopora --version`, `loopora --help`, `loopora init claude`, `loopora agent claude check`, parent directories, or broad project/file discovery to verify this entry; this project-local managed skill and its reference are the entry contract.
Critical Claude Code constraints:
- Do not run project tests, proof commands, or baseline checks before `loopora agent claude plan`; author the candidate plan from the current task context and managed reference.
- Read this managed skill/reference with Claude Code's file read capability at exact known paths, not shell directory discovery, `find`, `ls ... | head`, `cat ... | head`, `sed`, `tail`, `grep`, `jq`, or global `$HOME/.claude` discovery.
- Do not invoke other Loopora or alignment skills such as `loopora-task-alignment`; this project-local `/loopora-plan` entry is the only planning workflow for this turn.
- Do not run `which loopora`, `command -v loopora`, `type loopora`, `echo $PATH`, `loopora --version`, `loopora --help`, `loopora init claude`, `loopora agent claude check`, parent-directory probes, directory-listing preflights such as `ls`, or PATH/global-entry probes; the installed project-local entry and command below are the contract and the first real command is the capability check.
- Do not run the combined preflight `which loopora && loopora --version`; after reading the managed entry/reference, the next Bash action should create/check the candidate file or run the primary plan command.
- After writing a candidate file, verify only existence/readability with host file read or `test -f` / `test -s`; do not inspect snippets with `head`, `cat`, `sed`, `grep`, `jq`, `wc`, line counts, byte counts, or shell pipelines. The plan command validates the candidate.
- Run `loopora agent claude plan ... --json --compact-json` as the first Loopora command without `tee`, `wc`, shell pipelines, or line/byte-count wrappers. Preserve complete output in a workdir-local artifact if you need a file copy; do not redirect managed JSON to `/tmp`.

```bash
LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude plan --workdir "$PWD" --context-id "${{CLAUDE_SESSION_ID}}" --message "<non-empty short task summary>" --bundle-file <candidate-plan-file> --entry-source claude_project_skill --json --compact-json
```

`/loopora-plan` never starts a run. If the user wants to continue execution, send them to `/loopora-run`; if they say `fresh`, create a new candidate and keep old runs only as history.
"""


def claude_loopora_loop_skill(*, marker: str, version: int) -> str:
    return f"""---
name: loopora-run
description: "Manual /loopora-run entry. If the Skill tool reports disable-model-invocation, stay in the main session and run the Bash command below."
disable-model-invocation: true
allowed-tools: "Bash(loopora agent claude run *) Bash(loopora agent claude next *) Bash(loopora agent claude submit *) Bash(loopora agent claude check *) Bash(LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude *) Bash(LOOPORA_HOME=* loopora agent claude *) Bash(LOOPORA_HOME=* LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude *) Bash(loopora init claude *) Bash(LOOPORA_HOME=* loopora init claude *) Agent Task"
---

<!-- {marker} version={version} file=loopora-run -->

# Loopora Run

Start or reuse the reviewed Loop preview that preserves this Claude Code task judgment and evidence requirements.
This is a thin dispatcher. Read these managed references before starting role dispatch:

- `references/loopora-run-contract.md`
- `references/loopora-recovery-matrix.md`
- `references/loopora-role-dispatch-guide.md`
- `references/loopora-result-template-guide.md`

If Claude Code's Skill tool reports `disable-model-invocation`, do not invoke `Agent` or `Task` to simulate `/loopora-run`; stay in the main session, read these references, and run the Bash command below. Use `Agent` or `Task` only after Loopora Core returns a role `next_step`.
Do not inspect `$HOME/.claude`, global skill directories, Loopora manifests, binary/PATH probes such as `which loopora`, `command -v loopora`, `type loopora`, `echo $PATH`, `loopora --version`, `loopora --help`, `loopora init claude`, `loopora agent claude check`, parent directories, or broad project/file discovery to verify this entry; these project-local managed references are the entry contract.
Critical Claude Code constraints:
- Do not run the combined preflight `which loopora && loopora --version`, directory-listing preflights such as `ls`, or any PATH/help/init/check probe before `/loopora-run`; after reading the managed references, the next Loopora Bash action should be the primary run/next/submit command returned by Loopora.
- Copy `summary.next_role_dispatch_message` exactly as the Agent/Task prompt when present. Do not write a custom prompt beginning `You are running as the Loopora ... role agent`.
- The Agent/Task `prompt` input itself must start with `Use this exact string as the whole Agent/Task prompt`; put role selection in the tool's agent/subagent field, not in a wrapper prompt.
- Do not append task instructions, proof commands, artifact path examples, schema reminders, or extra paragraphs after the copied dispatch message; the role agent must open local paths for the full step contract.
- Do not prepend wrapper framing, `You are running as`, `Do the following:`, colon-style `target_agent:`, or examples before the copied dispatch message.
- Do not read `.claude/agents/loopora-*`, step context, step-contract, or result-template files in the main session as a substitute for Agent/Task dispatch. Invoke Agent/Task first; only after a real Agent/Task call returns structured output may the main session open the result template, fill `result`, and submit.
- Do not set `actual_agent`, `native_tool_name`, `dispatch_mode=host_subagent`, or `inline=false` from main-session work. If no Agent/Task start is observed, report native dispatch unavailable and stop before submit.
- Run `loopora agent claude submit ... --json --compact-json` exactly and read the complete JSON. Do not append `| head`, `| tail`, `| sed`, `| python -c`, `| jq`, `| grep`, or `2>&1 | ...`; if you need selected fields, save the full JSON first to a workdir-local artifact and parse that saved copy, not a `/tmp` file.
- Before GateKeeper runs a proof command, inspect upstream evidence refs and coverage. If upstream evidence already proves the required checks, GateKeeper should decide from those exact refs instead of rerunning the same command.
- If you report runtime activity observation, cite an active `/api/runtime/activity` snapshot for the target run while it is `queued`, `running`, or `awaiting_agent`; preserve any saved snapshot in a workdir-local artifact, not `/tmp`; do not substitute returned run URLs, timeline/evidence directories, ledgers, or post-exit file existence.

{agent_native_run_entry_contract().rstrip()}

Start or resume with:

```bash
LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude run --workdir "$PWD" --context-id "${{CLAUDE_SESSION_ID}}" --entry-source claude_project_skill --json --compact-json
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
LOOPORA_AGENT_ENTRY_SOURCE=opencode_project_command loopora agent opencode plan --workdir "$PWD" --context-id "${{OPENCODE_SESSION_ID:-}}" --message "<non-empty short task summary>" --bundle-file <candidate-plan-file> --entry-source opencode_project_command --json --compact-json
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
LOOPORA_AGENT_ENTRY_SOURCE=opencode_project_command loopora agent opencode run --workdir "$PWD" --context-id "${{OPENCODE_SESSION_ID:-}}" --entry-source opencode_project_command --json --compact-json
```

If `$ARGUMENTS` or the user provides `option:<id>`, pass it as `--source-option-id <id>`. If the command returns `loop_recovery`, report the recovery path and stop before dispatching any role agent.
"""
