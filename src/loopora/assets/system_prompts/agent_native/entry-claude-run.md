---
name: loopora-run
description: "Manual /loopora-run entry. If the Skill tool reports disable-model-invocation, stay in the main session and run the Bash command below."
disable-model-invocation: true
allowed-tools: "Bash({{loopora_cli_entry}} agent claude run *) Bash({{loopora_cli_entry}} agent claude next *) Bash({{loopora_cli_entry}} agent claude submit *) Bash({{loopora_cli_entry}} agent claude check *) Bash(LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill {{loopora_cli_entry}} agent claude *) Bash(LOOPORA_HOME=* {{loopora_cli_entry}} agent claude *) Bash(LOOPORA_HOME=* LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill {{loopora_cli_entry}} agent claude *) Bash({{loopora_cli_entry}} init claude *) Bash(LOOPORA_HOME=* {{loopora_cli_entry}} init claude *) Agent Task"
---

<!-- {{marker}} version={{version}} file=loopora-run -->

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
- Run `{{loopora_cli_entry}} agent claude submit ... --json --compact-json` exactly and read the complete JSON. Do not append `| head`, `| tail`, `| sed`, `| python -c`, `| jq`, `| grep`, or `2>&1 | ...`; if you need selected fields, save the full JSON first to a workdir-local artifact and parse that saved copy, not a `/tmp` file.
- Before GateKeeper runs a proof command, inspect upstream evidence refs and coverage. If upstream evidence already proves the required checks, GateKeeper should decide from those exact refs instead of rerunning the same command.
- If you report runtime activity observation, cite an active `/api/runtime/activity` snapshot for the target run while it is `queued`, `running`, or `awaiting_agent`; preserve any saved snapshot in a workdir-local artifact, not `/tmp`; do not substitute returned run URLs, timeline/evidence directories, ledgers, or post-exit file existence.

{{run_entry_contract}}

Start or resume with:

```bash
LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill {{loopora_cli_entry}} agent claude run --workdir "$PWD" --context-id "${CLAUDE_SESSION_ID}" --entry-source claude_project_skill --json --compact-json
```

If the user provides `option:<id>`, pass it as `--source-option-id <id>`. If the command returns `loop_recovery`, report the recovery path and stop before dispatching any role agent.
