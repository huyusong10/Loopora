Loopora managed Agent entries are already project-local for this workspace.

If the user asks for `/loopora-plan`, `/loopora-run`, or both phases, do not perform entry-discovery or availability preflight probes. Forbidden probes include binary/PATH checks (`which loopora`, `command -v loopora`, `type loopora`, `echo $PATH`), help/version/init/check probes (`loopora --version`, `loopora --help`, `loopora init claude`, `loopora agent claude check`), parent-directory inspection, broad project/file discovery, directory walks, and shell-filtered listings such as `find`, `ls ... | head`, `head`, `tail`, `jq`, `grep`, or `wc`.

Use exact known project paths (`.claude/skills/loopora-plan/SKILL.md`, `.claude/skills/loopora-plan/references/loopora-plan-contract.md`, `.claude/skills/loopora-run/SKILL.md`, and `.claude/skills/loopora-run/references/loopora-run-contract.md`) plus the host Read tool when managed references are needed; do not inspect `$HOME/.claude` or run `find /` to locate entries. The explicit `loopora agent claude plan/run ... --json --compact-json` command is the capability check.

Do not run the combined preflight `which loopora && loopora --version`, directory-listing preflights such as `ls`, or any PATH/help/init/check probe after reading the managed entries.

For `/loopora-plan`, use a message-only plan call while Loopora fit, judgment sufficiency, working-agreement confirmation, or Web review is pending:

`LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude plan --workdir "$PWD" --context-id "$CLAUDE_SESSION_ID" --message "<non-empty task context>" --entry-source claude_project_skill --json --compact-json`

Preserve concrete fake-done risks, required evidence, judgment tradeoffs, residual-risk signals, and domain objects in `--message`; do not shrink a detailed `/loopora-plan` request into a title-only summary.

Create/check a candidate file only after explicit confirmation, an explicit candidate path, or repair recovery. Do not treat a detailed first prompt as confirmation. After that point, submit or repair the candidate with:

`LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude plan --workdir "$PWD" --context-id "$CLAUDE_SESSION_ID" --message "<non-empty task context>" --bundle-file <candidate-plan-file> --entry-source claude_project_skill --json --compact-json`

For `/loopora-run`, run the managed run command and dispatch roles only after Loopora Core returns `next_step`.

If preserving managed JSON or runtime snapshots, write them under the workdir, not `/tmp`.
