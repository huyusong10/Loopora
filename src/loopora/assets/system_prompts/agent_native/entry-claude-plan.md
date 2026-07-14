---
name: loopora-plan
description: "Manual host-native /loopora-plan entry. Stay in the main session for alignment; run the candidate Bash command only after explicit confirmation."
disable-model-invocation: true
allowed-tools: "Bash({{loopora_cli_entry}} agent claude plan *) Bash(LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill {{loopora_cli_entry}} agent claude plan *) Bash(LOOPORA_HOME=* {{loopora_cli_entry}} agent claude plan *) Bash(LOOPORA_HOME=* LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill {{loopora_cli_entry}} agent claude plan *)"
---

<!-- {{marker}} version={{version}} file=loopora-plan -->

# Loopora Plan

Create, revise, repair, or tighten the current Claude Code Loop preview without starting a run.
This is a host-native interactive planning dispatcher. Keep planning in the current main session; do not invoke `Agent` or `Task`, start a nested provider CLI, or make the message-only CLI call as the first planning action.
Preserve the user's complete task judgment. If Loopora fit or a Loop-shaping decision is missing, use the main-session question capability to ask one focused question with a recommended answer and wait. Otherwise present a draft working agreement covering fit, outcome, fake-done risks, evidence, execution strategy, tradeoffs, residual-risk policy, and local governance, then wait for explicit confirmation.
Only after explicit confirmation, read `references/loopora-plan-contract.md`, author a complete candidate under `.loopora/agent_inbox/claude/`, and submit it with `--bundle-file`. Repair and resubmit the same candidate when validation asks.
Use the message-only command only when Claude Code cannot continue the main-session dialogue or the user explicitly chooses Web review. That fallback may start a separate alignment executor and does not prove a candidate is ready.
Do not inspect `$HOME/.claude`, global skill directories, Loopora manifests, binary/PATH probes such as `which loopora`, `command -v loopora`, `type loopora`, `echo $PATH`, `loopora --version`, `loopora --help`, `loopora init claude`, `loopora agent claude check`, parent directories, or broad project/file discovery to verify this entry; this project-local managed skill and its reference are the entry contract.
Critical Claude Code constraints:
- Do not run project tests, proof commands, baseline checks, or Loopora CLI commands before main-session alignment and explicit confirmation. Author or submit a candidate plan only after that confirmation or repair recovery.
- Read this managed skill/reference with Claude Code's file read capability at exact known paths when needed; do not use shell directory discovery, global `$HOME/.claude` discovery, `find`, `ls ... | head`, `cat ... | head`, `head`, `tail`, `grep`, `jq`, partial/range-limited reads, or line/byte-count wrappers as entry validation.
- Do not invoke other Loopora or alignment skills such as `loopora-task-alignment`; this project-local `/loopora-plan` entry is the only planning workflow for this turn.
- Do not run `which loopora`, `command -v loopora`, `type loopora`, `echo $PATH`, `loopora --version`, `loopora --help`, `loopora init claude`, `loopora agent claude check`, parent-directory probes, directory-listing preflights such as `ls`, or PATH/global-entry probes; the installed project-local entry and command below are the contract and the first real command is the capability check.
- Do not run the combined preflight `which loopora && loopora --version`; after explicit confirmation and candidate authoring, the next Bash action should run the candidate plan command. Create/check a candidate file only after explicit confirmation, an explicit candidate path, or repair recovery.
- After writing a candidate file, verify only existence/readability with host file read or `test -f` / `test -s`; do not inspect snippets with `head`, `cat`, `sed`, `grep`, `jq`, `wc`, line counts, byte counts, or shell pipelines. The plan command validates the candidate.
- After explicit confirmation, run the candidate `{{loopora_cli_entry}} agent claude plan ... --bundle-file ... --json --compact-json` as the first Loopora command without `tee`, `wc`, shell pipelines, or line/byte-count wrappers. Preserve complete output in a workdir-local artifact if needed; do not redirect managed JSON to `/tmp`.

Confirmed candidate or repair:
```bash
LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill {{loopora_cli_entry}} agent claude plan --workdir "$PWD" --context-id "${CLAUDE_SESSION_ID}" --message "<confirmed task context>" --bundle-file <candidate-plan-file> --entry-source claude_project_skill --json --compact-json
```

Non-interactive or Web fallback:
```bash
LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill {{loopora_cli_entry}} agent claude plan --workdir "$PWD" --context-id "${CLAUDE_SESSION_ID}" --message "<non-empty task context>" --entry-source claude_project_skill --json --compact-json
```

`/loopora-plan` never starts a run. If the user wants to continue execution, send them to `/loopora-run`; if they say `fresh`, create a new candidate and keep old runs only as history.
