from __future__ import annotations

import json
from pathlib import Path


import loopora.agent_adapters as agent_adapters
from agent_adapter_expected import (
    AGENT_ENTRY_GEN_CONTRACT_SNIPPETS,
    AGENT_ENTRY_LOOP_CONTRACT_SNIPPETS,
    AGENT_ORCHESTRATOR_CONTRACT_SNIPPETS,
)


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

def _assert_claude_gen_entry(gen_skill: str, plan_contract: str) -> None:
    assert "disable-model-invocation: true" in gen_skill
    assert "allowed-tools:" in gen_skill
    assert "Bash(LOOPORA_HOME=* loopora agent claude plan *)" in gen_skill
    assert "Bash(LOOPORA_HOME=* LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude plan *)" in gen_skill
    assert "LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill" in gen_skill
    assert 'loopora agent claude plan --workdir "$PWD"' in gen_skill
    assert '--context-id "${CLAUDE_SESSION_ID}"' in gen_skill
    assert "--entry-source claude_project_skill" in gen_skill
    assert "Create, revise, repair, or tighten the current Claude Code Loop preview" in gen_skill
    assert "thin dispatcher" in gen_skill
    assert "references/loopora-plan-contract.md" in gen_skill
    assert len(gen_skill.splitlines()) <= 80
    for snippet in AGENT_ENTRY_GEN_CONTRACT_SNIPPETS:
        assert snippet in plan_contract
    assert "authoring YAML" not in gen_skill
    assert "fix the YAML" not in gen_skill
    assert "YAML" not in gen_skill
    assert "Web alignment URL" not in gen_skill

def _assert_claude_loop_entry(loop_skill: str, run_contract: str) -> None:
    assert "reviewed Loop preview" in loop_skill
    assert "preserves this Claude Code task judgment and evidence requirements" in loop_skill
    assert "confirmed Loop preview" not in loop_skill
    assert "READY bundle" not in loop_skill
    assert "Bash(LOOPORA_HOME=* loopora agent claude *)" in loop_skill
    assert "Bash(LOOPORA_HOME=* LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude *)" in loop_skill
    assert "Bash(LOOPORA_HOME=* loopora init claude *)" in loop_skill
    assert "LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill" in loop_skill
    assert 'loopora agent claude run --workdir "$PWD"' in loop_skill
    assert "loopora agent claude submit" in run_contract
    assert "Agent" in loop_skill
    assert "Task" in loop_skill
    assert "thin dispatcher" in loop_skill
    assert "references/loopora-run-contract.md" in loop_skill
    assert "references/loopora-recovery-matrix.md" in loop_skill
    _assert_loop_entry_native_run_contract(loop_skill)
    assert "--source-option-id" in loop_skill
    assert len(loop_skill.splitlines()) <= 80
    for snippet in AGENT_ENTRY_LOOP_CONTRACT_SNIPPETS:
        assert snippet in run_contract
    assert "Claude Code native dispatch guidance" in run_contract
    assert "Agent or Task tool" in run_contract
    assert "nested provider CLI" in run_contract
    assert "never cite todo completion, host status, or native trace as Loopora proof" in run_contract
    assert '--context-id "${CLAUDE_SESSION_ID}"' in loop_skill
    assert "--entry-source claude_project_skill" in loop_skill

def _assert_claude_agent_prompts(builder_agent: Path, orchestrator_agent: Path) -> None:
    builder_agent_text = builder_agent.read_text(encoding="utf-8")
    orchestrator_agent_text = orchestrator_agent.read_text(encoding="utf-8")
    assert "Loopora Builder" in builder_agent_text
    assert "tools: Read, Glob, Grep, Bash, Write, Edit, MultiEdit" in builder_agent_text
    assert "Loopora Orchestrator" in orchestrator_agent_text
    assert "tools: Agent, Task, Read, Write, Bash" in orchestrator_agent_text
    for snippet in AGENT_ORCHESTRATOR_CONTRACT_SNIPPETS:
        assert snippet in orchestrator_agent_text

def _assert_claude_manifest(manifest_path: Path) -> str:
    assert manifest_path.exists()
    first_manifest = manifest_path.read_text(encoding="utf-8")
    manifest_payload = json.loads(first_manifest)
    assert manifest_payload["managed_schema_version"] == agent_adapters.ADAPTER_MANAGED_SCHEMA_VERSION
    assert {item["path"] for item in manifest_payload["managed_files"]} == {
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
    orchestrator_agent = workdir / ".claude" / "agents" / "loopora-orchestrator.md"
    assert "LOOPORA-MANAGED: claude-code-adapter" in gen_skill
    assert not gen_command.exists()
    assert not loop_command.exists()
    assert not old_gen_skill.exists()
    assert not old_loop_skill.exists()
    for path in (session_hook, builder_agent, orchestrator_agent):
        assert path.exists()
    assert "CLAUDE_SESSION_ID" in session_hook.read_text(encoding="utf-8")
    assert _claude_settings_has_loopora_session_hook(settings)
    _assert_claude_gen_entry(gen_skill, plan_contract)
    assert "READY bundle" not in gen_skill
    _assert_claude_loop_entry(loop_skill, run_contract + recovery_matrix)
    _assert_claude_agent_prompts(builder_agent, orchestrator_agent)
    manifest_path = workdir / ".loopora" / "adapters" / "claude" / "manifest.json"
    return manifest_path, _assert_claude_manifest(manifest_path)

def _assert_opencode_managed_install(workdir: Path, command_paths: dict[str, Path]) -> tuple[Path, str]:  # noqa: PLR0915
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
    assert "description:" in gen_command
    assert "agent: build" not in gen_command
    assert "$ARGUMENTS" in gen_command
    assert "LOOPORA_AGENT_ENTRY_SOURCE=opencode_project_command" in gen_command
    assert 'loopora agent opencode plan --workdir "$PWD"' in gen_command
    assert '--context-id "${OPENCODE_SESSION_ID:-}"' in gen_command
    assert "--entry-source opencode_project_command" in gen_command
    assert "Create, revise, repair, or tighten the current OpenCode Loop preview" in gen_command
    assert "thin dispatcher" in gen_command
    assert ".opencode/loopora/references/loopora-plan-contract.md" in gen_command
    assert len(gen_command.splitlines()) <= 80
    for snippet in AGENT_ENTRY_GEN_CONTRACT_SNIPPETS:
        assert snippet in plan_contract
    assert "authoring YAML" not in gen_command
    assert "fix the YAML" not in gen_command
    assert "YAML" not in gen_command
    assert "reviewed Loop preview" in loop_command
    assert "preserves this OpenCode task judgment and evidence requirements" in loop_command
    assert "confirmed Loop preview" not in loop_command
    assert "READY bundle" not in gen_command
    assert "READY bundle" not in loop_command
    assert "LOOPORA_AGENT_ENTRY_SOURCE=opencode_project_command" in loop_command
    assert "agent: loopora-orchestrator" in loop_command
    assert "subtask: true" in loop_command
    assert 'loopora agent opencode run --workdir "$PWD"' in loop_command
    assert "loopora agent opencode submit" in run_contract
    assert "thin dispatcher" in loop_command
    assert ".opencode/loopora/references/loopora-run-contract.md" in loop_command
    assert ".opencode/loopora/references/loopora-recovery-matrix.md" in loop_command
    _assert_loop_entry_native_run_contract(loop_command)
    assert "--source-option-id" in loop_command
    assert len(loop_command.splitlines()) <= 80
    for snippet in AGENT_ENTRY_LOOP_CONTRACT_SNIPPETS:
        assert snippet in run_contract + recovery_matrix
    assert "OpenCode native dispatch guidance" in run_contract
    assert "agent: loopora-orchestrator" in run_contract
    assert "native task/agent capability" in run_contract
    assert "native `task` mechanism" in run_contract
    assert "native trace are not Loopora proof" in run_contract
    assert '--context-id "${OPENCODE_SESSION_ID:-}"' in loop_command
    assert "--entry-source opencode_project_command" in loop_command
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
    manifest_path = workdir / ".loopora" / "adapters" / "opencode" / "manifest.json"
    assert manifest_path.exists()
    first_manifest = manifest_path.read_text(encoding="utf-8")
    manifest_payload = json.loads(first_manifest)
    assert manifest_payload["managed_schema_version"] == agent_adapters.ADAPTER_MANAGED_SCHEMA_VERSION
    assert {item["path"] for item in manifest_payload["managed_files"]} == {
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
    assert "create, revise, repair, or tighten the reviewed Loop preview" in gen_skill
    assert "thin dispatcher" in gen_skill
    assert "references/loopora-plan-contract.md" in gen_skill
    assert len(gen_skill.splitlines()) <= 80
    for snippet in AGENT_ENTRY_GEN_CONTRACT_SNIPPETS:
        assert snippet in plan_contract
    assert "authoring YAML" not in gen_skill
    assert "fix the YAML" not in gen_skill
    assert "YAML" not in gen_skill
    assert "reviewed Loop preview" in loop_skill
    assert "preserves the current task judgment and evidence requirements" in loop_skill
    assert "confirmed Loop preview" not in loop_skill
    assert "READY bundle" not in gen_skill
    assert "READY bundle" not in loop_skill
    assert "name: loopora-run" in loop_skill
    assert "LOOPORA_AGENT_ENTRY_SOURCE=codex_project_skill" in loop_skill
    assert 'loopora agent codex run --workdir "$PWD"' in loop_skill
    assert "loopora agent codex submit" in run_contract
    assert "loopora-builder" in run_contract
    assert "thin dispatcher" in loop_skill
    assert "references/loopora-run-contract.md" in loop_skill
    assert "references/loopora-recovery-matrix.md" in loop_skill
    _assert_loop_entry_native_run_contract(loop_skill)
    assert "--source-option-id" in loop_skill
    assert len(loop_skill.splitlines()) <= 80
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
    assert {item["path"] for item in manifest_payload["managed_files"]} == {
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
    assert all(len(item["sha256"]) == 64 for item in manifest_payload["managed_files"])
    return manifest_path, first_manifest
