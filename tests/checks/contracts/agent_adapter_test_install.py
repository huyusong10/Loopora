from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


from loopora import agent_adapters
from loopora.proof_command_prompt_guidance import (
    INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE,
    PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE,
)
from agent_adapter_expected import (
    AGENT_ENTRY_GEN_CONTRACT_SNIPPETS,
    AGENT_ENTRY_LOOP_CONTRACT_SNIPPETS,
    AGENT_ORCHESTRATOR_CONTRACT_SNIPPETS,
)


MAX_AGENT_ENTRY_LINES = 80
SHA256_HEX_LENGTH = 64


def _codex_skill_paths(workdir: Path) -> dict[str, Path]:
    return {
        "plan": workdir / ".agents" / "skills" / "loopora-plan" / "SKILL.md",
        "run": workdir / ".agents" / "skills" / "loopora-run" / "SKILL.md",
    }

def _claude_skill_paths(workdir: Path) -> dict[str, Path]:
    return {
        "plan": workdir / ".claude" / "skills" / "loopora-plan" / "SKILL.md",
        "run": workdir / ".claude" / "skills" / "loopora-run" / "SKILL.md",
    }

def _opencode_command_paths(workdir: Path) -> dict[str, Path]:
    return {
        "plan": workdir / ".opencode" / "commands" / "loopora-plan.md",
        "run": workdir / ".opencode" / "commands" / "loopora-run.md",
    }

def _manifest_managed_file_paths(manifest_payload: dict) -> set[str]:
    return {item["path"] for item in manifest_payload["managed_files"]}

def _assert_entry_line_budget(entry_text: str) -> None:
    assert len(entry_text.splitlines()) <= MAX_AGENT_ENTRY_LINES

def _assert_plan_entry_avoids_yaml_authoring(plan_entry: str) -> None:
    for forbidden in ("authoring YAML", "fix the YAML", "YAML"):
        assert forbidden not in plan_entry

def _assert_snippets(text: str, snippets: tuple[str, ...]) -> None:
    for snippet in snippets:
        assert snippet in text

def _assert_run_contract_compact_commands(
    run_contract: str, *, adapter: str, marker_source: str, context_arg: str = ""
) -> None:
    context_bits = f" {context_arg}" if context_arg else ""
    run_command = (
        f'loopora agent {adapter} run --workdir "$PWD"{context_bits} '
        f"--entry-source {marker_source} --json --compact-json"
    )
    submit_command = (
        f'loopora agent {adapter} submit --workdir "$PWD"{context_bits} --run-id <run-id> '
        f"--step-id <step-id> --result-file RESULT_JSON_PATH --entry-source {marker_source} "
        "--json --compact-json"
    )
    assert run_command in run_contract
    assert submit_command in run_contract

def _claude_settings_has_loopora_session_hook(settings: dict) -> bool:
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return False
    session_start = hooks.get("SessionStart")
    if not isinstance(session_start, list):
        return False
    for group in session_start:
        if not isinstance(group, dict):
            continue
        handlers = group.get("hooks")
        if not isinstance(handlers, list):
            continue
        if any(
            isinstance(handler, dict)
            and str(handler.get("command") or "").strip() == 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/loopora-session-context.py"'
            for handler in handlers
        ):
            return True
    return False

def _assert_claude_session_hook_executes(session_hook: Path, workdir: Path) -> None:
    env_file = workdir / ".claude" / "loopora-test-env.sh"
    completed = subprocess.run(
        [sys.executable, str(session_hook)],
        input=json.dumps({"session_id": "session_123", "transcript_path": str(workdir / "transcript.jsonl")}),
        text=True,
        capture_output=True,
        check=False,
        env={"CLAUDE_ENV_FILE": str(env_file)},
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    payload = json.loads(completed.stdout)
    hook_output = payload["hookSpecificOutput"]
    additional_context = hook_output["additionalContext"]
    assert hook_output["hookEventName"] == "SessionStart"
    assert ".claude/skills/loopora-plan/SKILL.md" in additional_context
    assert ".claude/skills/loopora-run/SKILL.md" in additional_context
    assert "do not inspect `$HOME/.claude`" in additional_context
    assert "run `find /`" in additional_context
    assert "Do not run the combined preflight `which loopora && loopora --version`" in additional_context
    assert "directory-listing preflights such as `ls`" in additional_context
    assert "write them under the workdir, not `/tmp`" in additional_context
    assert '--workdir "$PWD"' in additional_context
    assert '--context-id "$CLAUDE_SESSION_ID"' in additional_context
    assert "LOOPORA_AGENT_SESSION_ID=session_123" in env_file.read_text(encoding="utf-8")

def _assert_claude_gen_entry(gen_skill: str, plan_contract: str) -> None:
    assert "disable-model-invocation: true" in gen_skill
    assert "Manual /loopora-plan entry" in gen_skill
    assert "Skill tool reports disable-model-invocation" in gen_skill
    assert "do not invoke `Agent` or `Task` to simulate `/loopora-plan`" in gen_skill
    assert "stay in the main session" in gen_skill
    assert "allowed-tools:" in gen_skill
    assert "Bash(LOOPORA_HOME=* loopora agent claude plan *)" in gen_skill
    assert "Bash(LOOPORA_HOME=* LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude plan *)" in gen_skill
    assert "LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill" in gen_skill
    assert 'loopora agent claude plan --workdir "$PWD"' in gen_skill
    assert '--context-id "${CLAUDE_SESSION_ID}"' in gen_skill
    assert "--entry-source claude_project_skill" in gen_skill
    assert "--json --compact-json" in gen_skill
    assert "Create, revise, repair, or tighten the current Claude Code Loop preview" in gen_skill
    assert "thin dispatcher" in gen_skill
    assert "references/loopora-plan-contract.md" in gen_skill
    assert "Do not inspect `$HOME/.claude`, global skill directories, Loopora manifests" in gen_skill
    assert "binary/PATH probes such as `which loopora`, `command -v loopora`, `type loopora`, `echo $PATH`" in gen_skill
    assert "`loopora --version`, `loopora --help`, `loopora init claude`, `loopora agent claude check`" in gen_skill
    assert "project-local managed skill and its reference are the entry contract" in gen_skill
    assert "Critical Claude Code constraints" in gen_skill
    _assert_snippets(
        gen_skill,
        (
            "Do not run project tests, proof commands, or baseline checks before `loopora agent claude plan`",
            "Read this managed skill/reference with Claude Code's file read capability",
            "not shell directory discovery, `find`, `ls ... | head`, `cat ... | head`",
            "Do not invoke other Loopora or alignment skills such as `loopora-task-alignment`",
            "Do not run `which loopora`, `command -v loopora`, `type loopora`, `echo $PATH`",
            "`loopora init claude`, `loopora agent claude check`, parent-directory probes",
            "Do not run the combined preflight `which loopora && loopora --version`",
            "directory-listing preflights such as `ls`",
            "the next Bash action should create/check the candidate file or run the primary plan command",
            "After writing a candidate file, verify only existence/readability",
            "do not inspect snippets with `head`, `cat`, `sed`, `grep`, `jq`, `wc`",
            "without `tee`, `wc`, shell pipelines, or line/byte-count wrappers",
            "do not redirect managed JSON to `/tmp`",
        ),
    )
    assert "entry-visibility signal" in plan_contract
    assert "not permission to simulate `/loopora-plan` through a generic `Agent` or `Task` call" in plan_contract
    assert "project-local managed entry/reference file" in plan_contract
    assert "global skill directories" in plan_contract
    assert "parent directories, or broad project/file discovery to verify the entry" in plan_contract
    assert "`command -v loopora`, `type loopora`, `echo $PATH`" in plan_contract
    assert "read the project-local managed entry/reference file if needed with the host file-read capability" in plan_contract
    _assert_snippets(
        plan_contract,
        (
            "Do not invoke adjacent Loopora, alignment, bundle-generation, or marketplace skills such as `loopora-task-alignment`",
            "`loopora --version`, `loopora --help`, `loopora init claude`, `loopora agent claude check`",
            "Do not read managed references through shell directory discovery, `find`, `ls ... | head`, `cat ... | head`",
            "Do not run the combined preflight `which loopora && loopora --version`",
            "directory-listing preflights such as `ls`",
            "the next Bash action should create/check the candidate file or run the primary plan command",
            "After writing a candidate plan file, verify only existence/readability",
            "do not inspect candidate snippets with `head`, `head -1`, `cat`, `sed`, `grep`, `jq`, `wc`",
            "Do not run project tests, proof commands, smoke checks, or baseline checks before the primary `loopora agent claude plan` command",
            "planning should author the Loop contract from current task context and managed references",
            "Do not wrap it in `tee`, `wc`, `head`, `tail`, `sed`, `jq`, `grep`, `python -c`, line/byte-count commands, or shell pipelines",
            "do not redirect managed JSON to `/tmp`",
        ),
    )
    _assert_entry_line_budget(gen_skill)
    for snippet in AGENT_ENTRY_GEN_CONTRACT_SNIPPETS:
        assert snippet in plan_contract
    _assert_plan_entry_avoids_yaml_authoring(gen_skill)
    assert "Web alignment URL" not in gen_skill

def _assert_claude_loop_entry(loop_skill: str, run_contract: str) -> None:
    assert "Manual /loopora-run entry" in loop_skill
    assert "Skill tool reports disable-model-invocation" in loop_skill
    assert "do not invoke `Agent` or `Task` to simulate `/loopora-run`" in loop_skill
    assert "Use `Agent` or `Task` only after Loopora Core returns a role `next_step`" in loop_skill
    assert "reviewed Loop preview" in loop_skill
    assert "confirmed Loop preview" not in loop_skill
    assert "READY bundle" not in loop_skill
    assert "Bash(LOOPORA_HOME=* loopora agent claude *)" in loop_skill
    assert "Bash(LOOPORA_HOME=* LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude *)" in loop_skill
    assert "Bash(LOOPORA_HOME=* loopora init claude *)" in loop_skill
    assert "LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill" in loop_skill
    assert 'loopora agent claude run --workdir "$PWD"' in loop_skill
    assert "loopora agent claude submit" in run_contract
    for snippet in (
        "entry-visibility signal",
        "not permission to simulate `/loopora-run` through a generic `Agent` or `Task` call",
        "project-local managed references if needed",
        "global skill directories",
        "parent directories, or broad project/file discovery to verify the entry",
        "`command -v loopora`, `type loopora`, `echo $PATH`",
        "`loopora init claude`, `loopora agent claude check`",
        "use host-native role `Agent` / `Task` dispatch only after Loopora Core returns a role `next_step`",
        "Do not run the combined preflight `which loopora && loopora --version`",
        "directory-listing preflights such as `ls`",
        "the next Loopora Bash action should be the primary run/next/submit command returned by Loopora",
    ):
        assert snippet in run_contract
    _assert_run_contract_compact_commands(
        run_contract,
        adapter="claude",
        marker_source="claude_project_skill",
        context_arg='--context-id "${CLAUDE_SESSION_ID}"',
    )
    for snippet in (
        "Agent",
        "Task",
        "thin dispatcher",
        "references/loopora-run-contract.md",
        "references/loopora-recovery-matrix.md",
        "Do not inspect `$HOME/.claude`, global skill directories, Loopora manifests",
        "binary/PATH probes such as `which loopora`, `command -v loopora`, `type loopora`, `echo $PATH`",
        "`loopora --version`, `loopora --help`, `loopora init claude`, `loopora agent claude check`",
        "project-local managed references are the entry contract",
        "Critical Claude Code constraints",
        "Do not run the combined preflight `which loopora && loopora --version`",
        "directory-listing preflights such as `ls`",
        "the next Loopora Bash action should be the primary run/next/submit command returned by Loopora",
        "Copy `summary.next_role_dispatch_message` exactly as the Agent/Task prompt",
        "The Agent/Task `prompt` input itself must start with `Use this exact string as the whole Agent/Task prompt`",
        "Do not write a custom prompt beginning `You are running as the Loopora ... role agent`",
        "Do not prepend wrapper framing, `You are running as`, `Do the following:`, colon-style `target_agent:`",
        "Do not append task instructions, proof commands, artifact path examples",
        "Do not read `.claude/agents/loopora-*`, step context, step-contract, or result-template files",
        "If no Agent/Task start is observed, report native dispatch unavailable and stop before submit",
        "Do not append `| head`, `| tail`, `| sed`, `| python -c`, `| jq`, `| grep`, or `2>&1 | ...`",
        "not a `/tmp` file",
        "If upstream evidence already proves the required checks",
        "If you report runtime activity observation, cite an active `/api/runtime/activity` snapshot",
        "preserve any saved snapshot in a workdir-local artifact, not `/tmp`",
    ):
        assert snippet in loop_skill
    _assert_loop_entry_native_run_contract(loop_skill)
    assert "--source-option-id" in loop_skill
    _assert_entry_line_budget(loop_skill)
    for snippet in AGENT_ENTRY_LOOP_CONTRACT_SNIPPETS:
        assert snippet in run_contract
    for snippet in (
        "Claude Code native dispatch guidance",
        "Agent or Task tool",
        "main Claude Code session",
        "Do not read host role-agent config files, step context, step-contract, or result-template files",
        "only set `loopora_host_dispatch.actual_agent`, `native_tool_name`, `dispatch_mode=host_subagent`, or `inline=false`",
        "do not construct `result` from main-session file reads, reruns, role-agent config text, or observations",
        "final assistant answer must include the literal `agent_work_panel:` block",
        "role-agent call cannot be observed to start promptly",
        "agent_work_panel:",
        "If a task or probe asks for runtime activity observation",
        "use the returned local Web origin to read `/api/runtime/activity`",
        "Returned run URLs, timeline/evidence directories, ledgers, or post-exit file existence are diagnostics only",
        "nested provider CLI",
        "never cite todo completion, host status, or native trace as Loopora proof",
    ):
        assert snippet in run_contract
    for snippet in ('--context-id "${CLAUDE_SESSION_ID}"', "--entry-source claude_project_skill"):
        assert snippet in loop_skill

def _assert_claude_agent_prompts(builder_agent: Path, inspector_agent: Path, gatekeeper_agent: Path, orchestrator_agent: Path) -> None:
    builder_agent_text = builder_agent.read_text(encoding="utf-8")
    inspector_agent_text = inspector_agent.read_text(encoding="utf-8")
    gatekeeper_agent_text = gatekeeper_agent.read_text(encoding="utf-8")
    orchestrator_agent_text = orchestrator_agent.read_text(encoding="utf-8")
    assert "Loopora Builder" in builder_agent_text
    assert "tools: Read, Glob, Grep, Bash, Write, Edit, MultiEdit" in builder_agent_text
    assert "tools: Read, Glob, Grep, Bash" in inspector_agent_text
    assert "tools: Read, Glob, Grep, Bash" in gatekeeper_agent_text
    assert "Do not save, overwrite, or submit Loopora result template/outbox files from inside this role." in inspector_agent_text
    assert "Do not save, overwrite, or submit Loopora result template/outbox files from inside this role." in gatekeeper_agent_text
    assert "Bash heredocs" in inspector_agent_text
    assert "Bash heredocs" in gatekeeper_agent_text
    assert PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE in inspector_agent_text
    assert PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE in gatekeeper_agent_text
    assert "discovery, directory-listing, context-check" in inspector_agent_text
    assert "discovery, directory-listing, context-check" in gatekeeper_agent_text
    assert "do not replace it with `ls ... | head`" in gatekeeper_agent_text
    assert INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE in inspector_agent_text
    assert INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE not in gatekeeper_agent_text
    assert "Run each primary proof command once" in inspector_agent_text
    assert "Run each primary proof command once" in gatekeeper_agent_text
    assert "Return exactly one raw wrapper JSON object" in inspector_agent_text
    assert "Do not wrap it in Markdown fences, prose, a code block, or a trailing explanation." in inspector_agent_text
    assert "Do not include `loopora_result_contract` in the returned wrapper" in inspector_agent_text
    assert "result_file_to_write" in inspector_agent_text
    assert "result_file_to_write" in gatekeeper_agent_text
    assert "GateKeeper fail-closed dynamic-check rule" in gatekeeper_agent_text
    assert "If a proof file is empty, unexpectedly short, or created by a misordered shell redirection" in gatekeeper_agent_text
    assert "do not write them under `.loopora/agent_outbox`" in gatekeeper_agent_text
    assert "Do not validate proof artifacts with `wc`, line counts, byte counts" in gatekeeper_agent_text
    assert "write it directly to a task-owned path" in builder_agent_text
    assert "do not stage it in `/tmp`" in builder_agent_text
    assert "fresh upstream task-owned proof artifacts" in inspector_agent_text
    assert "without rerunning the identical command" in inspector_agent_text
    assert ".loopora/agent_artifacts/<run_id>/<step_id>/" in gatekeeper_agent_text
    assert "NOT-OK" in gatekeeper_agent_text
    assert "`passed` false" in gatekeeper_agent_text
    assert "GateKeeper fail-closed dynamic-check rule" not in inspector_agent_text
    assert "Loopora Orchestrator" in orchestrator_agent_text
    assert PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE in orchestrator_agent_text
    assert "discovery, directory-listing, context-check" in orchestrator_agent_text
    assert "do not replace it with `ls ... | head`" in orchestrator_agent_text
    assert "do not stage it in `/tmp`" in orchestrator_agent_text
    assert "remove it from the filled wrapper before submit" in orchestrator_agent_text
    assert "Role agents return raw wrapper JSON" in orchestrator_agent_text
    assert "tools: Agent, Task, Read, Write, Bash" in orchestrator_agent_text
    for snippet in AGENT_ORCHESTRATOR_CONTRACT_SNIPPETS:
        assert snippet in orchestrator_agent_text

def _assert_claude_manifest(manifest_path: Path) -> str:
    assert manifest_path.exists()
    first_manifest = manifest_path.read_text(encoding="utf-8")
    manifest_payload = json.loads(first_manifest)
    assert manifest_payload["managed_schema_version"] == agent_adapters.ADAPTER_MANAGED_SCHEMA_VERSION
    assert _manifest_managed_file_paths(manifest_payload) == {
        ".claude/skills/loopora-plan/SKILL.md",
        ".claude/skills/loopora-plan/references/loopora-plan-contract.md",
        ".claude/skills/loopora-run/SKILL.md",
        ".claude/skills/loopora-run/references/loopora-run-contract.md",
        ".claude/skills/loopora-run/references/loopora-recovery-matrix.md",
        ".claude/skills/loopora-run/references/loopora-result-template-guide.md",
        ".claude/skills/loopora-run/references/loopora-role-dispatch-guide.md",
        ".claude/hooks/loopora-session-context.py",
        ".claude/agents/loopora-builder.md",
        ".claude/agents/loopora-inspector.md",
        ".claude/agents/loopora-gatekeeper.md",
        ".claude/agents/loopora-guide.md",
        ".claude/agents/loopora-orchestrator.md",
    }
    return first_manifest

def _assert_claude_managed_install(workdir: Path, skill_paths: dict[str, Path]) -> tuple[Path, str]:
    gen_skill = skill_paths["plan"].read_text(encoding="utf-8")
    loop_skill = skill_paths["run"].read_text(encoding="utf-8")
    plan_contract = (workdir / ".claude" / "skills" / "loopora-plan" / "references" / "loopora-plan-contract.md").read_text(encoding="utf-8")
    run_contract = (workdir / ".claude" / "skills" / "loopora-run" / "references" / "loopora-run-contract.md").read_text(encoding="utf-8")
    recovery_matrix = (workdir / ".claude" / "skills" / "loopora-run" / "references" / "loopora-recovery-matrix.md").read_text(encoding="utf-8")
    settings = json.loads((workdir / ".claude" / "settings.json").read_text(encoding="utf-8"))
    gen_command = workdir / ".claude" / "commands" / "loopora-plan.md"
    loop_command = workdir / ".claude" / "commands" / "loopora-run.md"
    old_gen_skill = workdir / ".claude" / "skills" / "loopora-gen" / "SKILL.md"
    old_loop_skill = workdir / ".claude" / "skills" / "loopora-loop" / "SKILL.md"
    session_hook = workdir / ".claude" / "hooks" / "loopora-session-context.py"
    builder_agent = workdir / ".claude" / "agents" / "loopora-builder.md"
    inspector_agent = workdir / ".claude" / "agents" / "loopora-inspector.md"
    gatekeeper_agent = workdir / ".claude" / "agents" / "loopora-gatekeeper.md"
    orchestrator_agent = workdir / ".claude" / "agents" / "loopora-orchestrator.md"
    assert "LOOPORA-MANAGED: claude-code-adapter" in gen_skill
    assert not gen_command.exists()
    assert not loop_command.exists()
    assert not old_gen_skill.exists()
    assert not old_loop_skill.exists()
    for path in (session_hook, builder_agent, inspector_agent, gatekeeper_agent, orchestrator_agent):
        assert path.exists()
    session_hook_text = session_hook.read_text(encoding="utf-8")
    assert "CLAUDE_SESSION_ID" in session_hook_text
    assert "Loopora managed Agent entries are already project-local" in session_hook_text
    assert "`which loopora`" in session_hook_text
    assert "`command -v loopora`" in session_hook_text
    assert "`type loopora`" in session_hook_text
    assert "`echo $PATH`" in session_hook_text
    assert "`loopora --version`" in session_hook_text
    assert "`loopora --help`" in session_hook_text
    assert "`loopora init claude`" in session_hook_text
    assert "`loopora agent claude check`" in session_hook_text
    assert "Do not run the combined preflight `which loopora && loopora --version`" in session_hook_text
    assert "directory-listing preflights such " in session_hook_text
    assert "as `ls`" in session_hook_text
    assert "write them under the workdir, not `/tmp`" in session_hook_text
    assert "parent-directory inspection" in session_hook_text
    assert "directory walks" in session_hook_text
    assert ".claude/skills/loopora-plan/SKILL.md" in session_hook_text
    assert "do not inspect `$HOME/.claude`" in session_hook_text
    assert "run `find /`" in session_hook_text
    assert "author the candidate file under .loopora/agent_inbox/claude/ first" in session_hook_text
    assert "--bundle-file <candidate>" in session_hook_text
    _assert_claude_session_hook_executes(session_hook, workdir)
    assert _claude_settings_has_loopora_session_hook(settings)
    _assert_claude_gen_entry(gen_skill, plan_contract)
    assert "READY bundle" not in gen_skill
    _assert_claude_loop_entry(loop_skill, run_contract + recovery_matrix)
    _assert_claude_agent_prompts(builder_agent, inspector_agent, gatekeeper_agent, orchestrator_agent)
    manifest_path = workdir / ".loopora" / "adapters" / "claude" / "manifest.json"
    return manifest_path, _assert_claude_manifest(manifest_path)

def _assert_opencode_plan_entry(gen_command: str, plan_contract: str) -> None:
    assert "description:" in gen_command
    assert "agent: build" not in gen_command
    assert "$ARGUMENTS" in gen_command
    assert "LOOPORA_AGENT_ENTRY_SOURCE=opencode_project_command" in gen_command
    assert 'loopora agent opencode plan --workdir "$PWD"' in gen_command
    assert '--context-id "${OPENCODE_SESSION_ID:-}"' in gen_command
    assert "--entry-source opencode_project_command" in gen_command
    assert "--json --compact-json" in gen_command
    assert "Create, revise, repair, or tighten the current OpenCode Loop preview" in gen_command
    assert "thin dispatcher" in gen_command
    assert ".opencode/loopora/references/loopora-plan-contract.md" in gen_command
    _assert_entry_line_budget(gen_command)
    for snippet in AGENT_ENTRY_GEN_CONTRACT_SNIPPETS:
        assert snippet in plan_contract
    _assert_plan_entry_avoids_yaml_authoring(gen_command)
    assert "READY bundle" not in gen_command

def _assert_opencode_loop_entry(loop_command: str, run_contract: str, recovery_matrix: str) -> None:
    assert "reviewed Loop preview" in loop_command
    assert "preserves this OpenCode task judgment and evidence requirements" in loop_command
    assert "confirmed Loop preview" not in loop_command
    assert "READY bundle" not in loop_command
    assert "LOOPORA_AGENT_ENTRY_SOURCE=opencode_project_command" in loop_command
    assert "agent: loopora-orchestrator" in loop_command
    assert "subtask: true" in loop_command
    assert 'loopora agent opencode run --workdir "$PWD"' in loop_command
    assert "loopora agent opencode submit" in run_contract
    _assert_run_contract_compact_commands(
        run_contract,
        adapter="opencode",
        marker_source="opencode_project_command",
        context_arg='--context-id "${OPENCODE_SESSION_ID:-}"',
    )
    assert "thin dispatcher" in loop_command
    assert ".opencode/loopora/references/loopora-run-contract.md" in loop_command
    assert ".opencode/loopora/references/loopora-recovery-matrix.md" in loop_command
    _assert_loop_entry_native_run_contract(loop_command)
    assert "--source-option-id" in loop_command
    _assert_entry_line_budget(loop_command)
    for snippet in AGENT_ENTRY_LOOP_CONTRACT_SNIPPETS:
        assert snippet in run_contract + recovery_matrix
    assert "OpenCode native dispatch guidance" in run_contract
    assert "agent: loopora-orchestrator" in run_contract
    assert "native task/agent capability" in run_contract
    assert "native `task` mechanism" in run_contract
    assert "native trace are not Loopora proof" in run_contract
    assert '--context-id "${OPENCODE_SESSION_ID:-}"' in loop_command
    assert "--entry-source opencode_project_command" in loop_command

def _assert_opencode_agent_prompts(builder_agent: Path, orchestrator_agent: Path) -> None:
    builder_agent_text = builder_agent.read_text(encoding="utf-8")
    orchestrator_agent_text = orchestrator_agent.read_text(encoding="utf-8")
    assert "Loopora Builder" in builder_agent_text
    assert "mode: subagent" in builder_agent_text
    assert "task: deny" in builder_agent_text
    assert "Loopora Orchestrator" in orchestrator_agent_text
    assert "mode: subagent" in orchestrator_agent_text
    assert "loopora-builder: allow" in orchestrator_agent_text
    for snippet in AGENT_ORCHESTRATOR_CONTRACT_SNIPPETS:
        assert snippet in orchestrator_agent_text

def _assert_opencode_manifest(manifest_path: Path) -> tuple[Path, str]:
    assert manifest_path.exists()
    first_manifest = manifest_path.read_text(encoding="utf-8")
    manifest_payload = json.loads(first_manifest)
    assert manifest_payload["managed_schema_version"] == agent_adapters.ADAPTER_MANAGED_SCHEMA_VERSION
    assert _manifest_managed_file_paths(manifest_payload) == {
        ".opencode/commands/loopora-plan.md",
        ".opencode/loopora/references/loopora-plan-contract.md",
        ".opencode/commands/loopora-run.md",
        ".opencode/loopora/references/loopora-run-contract.md",
        ".opencode/loopora/references/loopora-recovery-matrix.md",
        ".opencode/loopora/references/loopora-result-template-guide.md",
        ".opencode/loopora/references/loopora-role-dispatch-guide.md",
        ".opencode/agents/loopora-builder.md",
        ".opencode/agents/loopora-inspector.md",
        ".opencode/agents/loopora-gatekeeper.md",
        ".opencode/agents/loopora-guide.md",
        ".opencode/agents/loopora-orchestrator.md",
    }
    return manifest_path, first_manifest

def _assert_opencode_managed_install(workdir: Path, command_paths: dict[str, Path]) -> tuple[Path, str]:
    gen_command = command_paths["plan"].read_text(encoding="utf-8")
    loop_command = command_paths["run"].read_text(encoding="utf-8")
    plan_contract = (workdir / ".opencode" / "loopora" / "references" / "loopora-plan-contract.md").read_text(encoding="utf-8")
    run_contract = (workdir / ".opencode" / "loopora" / "references" / "loopora-run-contract.md").read_text(encoding="utf-8")
    recovery_matrix = (workdir / ".opencode" / "loopora" / "references" / "loopora-recovery-matrix.md").read_text(encoding="utf-8")
    builder_agent = workdir / ".opencode" / "agents" / "loopora-builder.md"
    orchestrator_agent = workdir / ".opencode" / "agents" / "loopora-orchestrator.md"
    old_gen_command = workdir / ".opencode" / "commands" / "loopora-gen.md"
    old_loop_command = workdir / ".opencode" / "commands" / "loopora-loop.md"
    assert "LOOPORA-MANAGED: opencode-adapter" in gen_command
    assert builder_agent.exists()
    assert orchestrator_agent.exists()
    assert not old_gen_command.exists()
    assert not old_loop_command.exists()
    _assert_opencode_plan_entry(gen_command, plan_contract)
    _assert_opencode_loop_entry(loop_command, run_contract, recovery_matrix)
    _assert_opencode_agent_prompts(builder_agent, orchestrator_agent)
    manifest_path = workdir / ".loopora" / "adapters" / "opencode" / "manifest.json"
    return _assert_opencode_manifest(manifest_path)

def _assert_codex_managed_install(workdir: Path, skill_paths: dict[str, Path]) -> tuple[Path, str]:
    codex_builder_agent = workdir / ".codex" / "agents" / "loopora-builder.toml"
    codex_orchestrator_agent = workdir / ".codex" / "agents" / "loopora-orchestrator.toml"
    old_gen_skill = workdir / ".agents" / "skills" / "loopora-gen" / "SKILL.md"
    old_loop_skill = workdir / ".agents" / "skills" / "loopora-loop" / "SKILL.md"
    assert codex_builder_agent.exists()
    assert codex_orchestrator_agent.exists()
    assert not old_gen_skill.exists()
    assert not old_loop_skill.exists()
    gen_skill = skill_paths["plan"].read_text(encoding="utf-8")
    loop_skill = skill_paths["run"].read_text(encoding="utf-8")
    plan_contract = (workdir / ".agents" / "skills" / "loopora-plan" / "references" / "loopora-plan-contract.md").read_text(encoding="utf-8")
    run_contract = (workdir / ".agents" / "skills" / "loopora-run" / "references" / "loopora-run-contract.md").read_text(encoding="utf-8")
    recovery_matrix = (workdir / ".agents" / "skills" / "loopora-run" / "references" / "loopora-recovery-matrix.md").read_text(encoding="utf-8")
    assert "LOOPORA-MANAGED: codex-adapter" in gen_skill
    assert "name: loopora-plan" in gen_skill
    assert "LOOPORA_AGENT_ENTRY_SOURCE=codex_project_skill" in gen_skill
    assert 'loopora agent codex plan --workdir "$PWD"' in gen_skill
    assert "--bundle-file" in gen_skill
    assert "--entry-source codex_project_skill" in gen_skill
    assert "--json --compact-json" in gen_skill
    assert "create, revise, repair, or tighten the reviewed Loop preview" in gen_skill
    assert "thin dispatcher" in gen_skill
    assert "references/loopora-plan-contract.md" in gen_skill
    _assert_entry_line_budget(gen_skill)
    for snippet in AGENT_ENTRY_GEN_CONTRACT_SNIPPETS:
        assert snippet in plan_contract
    _assert_plan_entry_avoids_yaml_authoring(gen_skill)
    assert "reviewed Loop preview" in loop_skill
    assert "preserves the current task judgment and evidence requirements" in loop_skill
    assert "confirmed Loop preview" not in loop_skill
    assert "READY bundle" not in gen_skill
    assert "READY bundle" not in loop_skill
    assert "name: loopora-run" in loop_skill
    assert "LOOPORA_AGENT_ENTRY_SOURCE=codex_project_skill" in loop_skill
    assert 'loopora agent codex run --workdir "$PWD"' in loop_skill
    assert "loopora agent codex submit" in run_contract
    _assert_run_contract_compact_commands(
        run_contract,
        adapter="codex",
        marker_source="codex_project_skill",
    )
    assert "loopora-builder" in run_contract
    assert "thin dispatcher" in loop_skill
    assert "references/loopora-run-contract.md" in loop_skill
    assert "references/loopora-recovery-matrix.md" in loop_skill
    _assert_loop_entry_native_run_contract(loop_skill)
    assert "--source-option-id" in loop_skill
    _assert_entry_line_budget(loop_skill)
    for snippet in AGENT_ENTRY_LOOP_CONTRACT_SNIPPETS:
        assert snippet in run_contract + recovery_matrix
    assert "Codex native dispatch guidance" in run_contract
    assert "omit `fork_context`" in run_contract
    assert "bounded timeout" in run_contract
    assert "experience projection only; Loopora proof still comes only" in run_contract
    assert "--entry-source codex_project_skill" in loop_skill
    _assert_codex_role_agent_files(codex_builder_agent, codex_orchestrator_agent)
    return _assert_codex_manifest(workdir)

def _assert_codex_role_agent_files(codex_builder_agent: Path, codex_orchestrator_agent: Path) -> None:
    codex_builder_agent_text = codex_builder_agent.read_text(encoding="utf-8")
    assert "loopora-builder" in codex_builder_agent_text
    assert 'developer_instructions = """' in codex_builder_agent_text
    assert '\ninstructions = """' not in codex_builder_agent_text
    codex_orchestrator_agent_text = codex_orchestrator_agent.read_text(encoding="utf-8")
    assert "Loopora Orchestrator" in codex_orchestrator_agent_text
    for snippet in AGENT_ORCHESTRATOR_CONTRACT_SNIPPETS:
        assert snippet in codex_orchestrator_agent_text

def _assert_loop_entry_native_run_contract(loop_entry: str) -> None:
    assert agent_adapters.NATIVE_RUN_ENTRY_CONTRACT_TITLE in loop_entry
    for snippet in agent_adapters.NATIVE_RUN_ENTRY_CONTRACT_BULLETS:
        assert snippet in loop_entry

def _assert_codex_manifest(workdir: Path) -> tuple[Path, str]:
    manifest_path = workdir / ".loopora" / "adapters" / "codex" / "manifest.json"
    assert manifest_path.exists()
    first_manifest = manifest_path.read_text(encoding="utf-8")
    manifest_payload = json.loads(first_manifest)
    assert manifest_payload["managed_schema_version"] == agent_adapters.ADAPTER_MANAGED_SCHEMA_VERSION
    assert manifest_payload["version"] == agent_adapters.ADAPTER_VERSION
    assert _manifest_managed_file_paths(manifest_payload) == {
        ".agents/skills/loopora-plan/SKILL.md",
        ".agents/skills/loopora-plan/references/loopora-plan-contract.md",
        ".agents/skills/loopora-run/SKILL.md",
        ".agents/skills/loopora-run/references/loopora-run-contract.md",
        ".agents/skills/loopora-run/references/loopora-recovery-matrix.md",
        ".agents/skills/loopora-run/references/loopora-result-template-guide.md",
        ".agents/skills/loopora-run/references/loopora-role-dispatch-guide.md",
        ".codex/agents/loopora-builder.toml",
        ".codex/agents/loopora-inspector.toml",
        ".codex/agents/loopora-gatekeeper.toml",
        ".codex/agents/loopora-guide.toml",
        ".codex/agents/loopora-orchestrator.toml",
    }
    assert all(len(item["sha256"]) == SHA256_HEX_LENGTH for item in manifest_payload["managed_files"])
    return manifest_path, first_manifest
