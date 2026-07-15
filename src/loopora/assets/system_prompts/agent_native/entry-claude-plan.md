---
name: loopora-plan
description: "Manual /loopora-plan entry. If the Skill tool reports disable-model-invocation, stay in the main session and run the Bash command below."
disable-model-invocation: true
allowed-tools: "Bash(loopora agent claude plan *) Bash(LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude plan *) Bash(LOOPORA_HOME=* loopora agent claude plan *) Bash(LOOPORA_HOME=* LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude plan *)"
---

<!-- {{marker}} version={{version}} file=loopora-plan -->

# Loopora Plan

Create, revise, repair, or tighten the current Claude Code Loop preview without starting a run.
This is an interactive planning dispatcher. For initial message-only alignment or Web review, this entry is enough: preserve the task context and run the message-only command below; do not open the long reference before that first message-only call. Before authoring, submitting, or repairing a Loop plan file, or when typed recovery asks for more detail, read `references/loopora-plan-contract.md` and follow it as the stable planning contract.
Use a message-only plan call when the working agreement still needs dialogue or Web review; use `--bundle-file` only after explicit confirmation or when repairing/submitting a candidate plan file.
The `--message` value should preserve the user's task context: keep concrete fake-done risks, required evidence, judgment tradeoffs, residual-risk signals, and domain objects that could change the Loop. Do not shrink a detailed `/loopora-plan` request into a title-only summary.
If the plan result returns `loop_recovery=continue_alignment_dialogue`, `status=waiting_user`, `ask_user`, or `alignment_assistant_message`, report that question to the user and stop. Do not answer it from host inference, workdir probes, Web scraping, default policy, or your own preference; rerun message-only `/loopora-plan` only after the user replies.
If Claude Code's Skill tool reports `disable-model-invocation`, do not invoke `Agent` or `Task` to simulate `/loopora-plan`; stay in the main session, use this project-local entry/reference when needed, and run the Bash command below.
Do not inspect `$HOME/.claude`, global skill directories, Loopora manifests, binary/PATH probes such as `which loopora`, `command -v loopora`, `type loopora`, `echo $PATH`, `loopora --version`, `loopora --help`, `loopora init claude`, `loopora agent claude check`, parent directories, or broad project/file discovery to verify this entry; this project-local managed skill and its reference are the entry contract.
Critical Claude Code constraints:
- Do not run project tests, proof commands, or baseline checks before `loopora agent claude plan`; conduct interactive alignment from the current task context and managed reference. Author or submit a candidate plan only after explicit confirmation or repair recovery.
- Read this managed skill/reference with Claude Code's file read capability at exact known paths when needed; do not use shell directory discovery, global `$HOME/.claude` discovery, `find`, `ls ... | head`, `cat ... | head`, `head`, `tail`, `grep`, `jq`, partial/range-limited reads, or line/byte-count wrappers as entry validation.
- Do not invoke other Loopora or alignment skills such as `loopora-task-alignment`; this project-local `/loopora-plan` entry is the only planning workflow for this turn.
- Do not run `which loopora`, `command -v loopora`, `type loopora`, `echo $PATH`, `loopora --version`, `loopora --help`, `loopora init claude`, `loopora agent claude check`, parent-directory probes, directory-listing preflights such as `ls`, or PATH/global-entry probes; the installed project-local entry and command below are the contract and the first real command is the capability check.
- Do not run the combined preflight `which loopora && loopora --version`; after reading the managed entry/reference, the next Bash action should run the primary plan command. Create/check a candidate file only after explicit confirmation, an explicit candidate path, or repair recovery.
- After writing a candidate file, verify only existence/readability with host file read or `test -f` / `test -s`; do not inspect snippets with `head`, `cat`, `sed`, `grep`, `jq`, `wc`, line counts, byte counts, or shell pipelines. The plan command validates the candidate.
- Run `loopora agent claude plan ... --json --compact-json` as the first Loopora command without `tee`, `wc`, shell pipelines, or line/byte-count wrappers. Preserve complete output in a workdir-local artifact if you need a file copy; do not redirect managed JSON to `/tmp`.

Alignment or Web review:
```bash
LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude plan --workdir "$PWD" --context-id "${CLAUDE_SESSION_ID}" --message "<non-empty task context>" --entry-source claude_project_skill --json --compact-json
```

Confirmed bundle or repair:
```bash
LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude plan --workdir "$PWD" --context-id "${CLAUDE_SESSION_ID}" --message "<non-empty task context>" --bundle-file <candidate-plan-file> --entry-source claude_project_skill --json --compact-json
```

`/loopora-plan` never starts a run. If the user wants to continue execution, send them to `/loopora-run`; if they say `fresh`, create a new candidate and keep old runs only as history.
