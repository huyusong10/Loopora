Loopora managed Agent entries are already project-local for this workspace.

If the user asks for `/loopora-plan`, `/loopora-run`, or both phases, do not perform entry-discovery or availability preflight probes. Forbidden probes include binary/PATH checks (`which loopora`, `command -v loopora`, `type loopora`, `echo $PATH`), help/version/init/check probes (`loopora --version`, `loopora --help`, `loopora init claude`, `loopora agent claude check`), parent-directory inspection, broad project/file discovery, directory walks, and shell-filtered listings such as `find`, `ls ... | head`, `head`, `tail`, `jq`, `grep`, or `wc`.

Use exact known project paths (`.claude/skills/loopora-plan/SKILL.md`, `.claude/skills/loopora-plan/references/loopora-plan-contract.md`, `.claude/skills/loopora-run/SKILL.md`, and `.claude/skills/loopora-run/references/loopora-run-contract.md`) plus the host Read tool when managed references are needed; do not inspect `$HOME/.claude` or run `find /` to locate entries. Confirmed-candidate plan validation and the managed run command are the capability checks after their prerequisites are met.

Do not run the combined preflight `which loopora && loopora --version`, directory-listing preflights such as `ls`, or any PATH/help/init/check probe after reading the managed entries.

For `/loopora-plan`, keep fit review, missing-judgment questions, the draft working agreement, and explicit confirmation in the current Claude Code main session. Do not invoke `Agent`/`Task`, a nested provider CLI, or Loopora CLI before confirmation.

After explicit confirmation, create the candidate under `.loopora/agent_inbox/claude/` and submit it with:

`LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill {{loopora_cli_entry}} agent claude plan --workdir "$PWD" --context-id "$CLAUDE_SESSION_ID" --message "<confirmed task context>" --bundle-file <candidate-plan-file> --entry-source claude_project_skill --json --compact-json`

Preserve concrete fake-done risks, required evidence, judgment tradeoffs, residual-risk signals, and domain objects in `--message`; do not shrink a detailed `/loopora-plan` request into a title-only summary.

Use message-only planning only when Claude Code cannot continue the main-session dialogue or the user explicitly chooses Web review:

`LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill {{loopora_cli_entry}} agent claude plan --workdir "$PWD" --context-id "$CLAUDE_SESSION_ID" --message "<non-empty task context>" --entry-source claude_project_skill --json --compact-json`

For `/loopora-run`, run the managed run command and dispatch roles only after Loopora Core returns `next_step`.

If preserving managed JSON or runtime snapshots, write them under the workdir, not `/tmp`.
