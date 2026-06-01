from __future__ import annotations

from agent_native_v3_helpers import assert_agent_v3_envelope
from agent_adapter_test_support import (
    CliRunner,
    LooporaConflictError,
    Path,
    _assert_claude_managed_install,
    _assert_codex_managed_install,
    _assert_labeled_loopora_agent_command,
    _assert_loopora_cli_command,
    _assert_opencode_managed_install,
    _claude_settings_has_loopora_session_hook,
    _claude_skill_paths,
    _codex_skill_paths,
    _error_text,
    _opencode_command_paths,
    agent_adapters,
    cli,
    json,
    pytest,
)


def _agent_check_payload(payload: dict, *, status: str) -> tuple[dict, dict]:
    return assert_agent_v3_envelope(payload, kind="agent_check", summary_key="agent_check_summary", status=status)


def test_cli_codex_adapter_install_uninstall_are_idempotent(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()

    first_install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--json"])
    assert first_install.exit_code == 0, first_install.stdout
    assert json.loads(first_install.stdout)["status"] == "installed"
    skill_paths = _codex_skill_paths(workdir)
    assert skill_paths["plan"].exists()
    assert skill_paths["run"].exists()
    manifest_path, first_manifest = _assert_codex_managed_install(workdir, skill_paths)

    second_install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--json"])

    assert second_install.exit_code == 0, second_install.stdout
    assert json.loads(second_install.stdout)["status"] == "installed"
    assert manifest_path.read_text(encoding="utf-8") == first_manifest

    first_uninstall = runner.invoke(cli.app, ["uninstall", "codex", "--workdir", str(workdir), "--json"])
    second_uninstall = runner.invoke(cli.app, ["uninstall", "codex", "--workdir", str(workdir), "--json"])

    assert first_uninstall.exit_code == 0, first_uninstall.stdout
    assert second_uninstall.exit_code == 0, second_uninstall.stdout
    assert json.loads(first_uninstall.stdout)["status"] == "not_installed"
    assert json.loads(second_uninstall.stdout)["status"] == "not_installed"
    assert not skill_paths["plan"].exists()
    assert not skill_paths["run"].exists()
    assert (workdir / ".agents").exists()
    assert (workdir / ".codex").exists()
    assert (workdir / ".loopora").exists()
    assert not (workdir / ".loopora" / "adapters" / "codex" / "manifest.json").exists()

def test_cli_adapter_check_before_install_reports_install_state_not_internal_missing_files(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()

    text_result = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--check"])

    assert text_result.exit_code == 1
    assert "Codex Loopora entry check: fail" in text_result.stdout
    assert "install_state: not_installed" in text_result.stdout
    assert "missing managed files are expected before install" in text_result.stdout
    assert "Run:" in text_result.stdout
    assert f"loopora init codex --workdir {workdir.resolve()}" in text_result.stdout
    assert "Then verify:" in text_result.stdout
    assert f"loopora init codex --workdir {workdir.resolve()} --check" in text_result.stdout
    assert "supporting_file" not in text_result.stdout
    assert "role_agent" not in text_result.stdout
    assert "If a file is unmanaged" not in text_result.stdout

    json_result = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--check", "--json"])
    assert json_result.exit_code == 1
    payload = json.loads(json_result.stdout)
    summary, _legacy = _agent_check_payload(payload, status="fail")
    assert summary["check_status"] == "fail"
    assert summary["check_recovery"]["state"] == "not_installed"
    assert summary["check_recovery"]["details_are_expected"] is True
    assert summary["check_recovery"]["install_command"].endswith(f"--workdir {workdir.resolve()}")

def test_cli_agent_adapter_check_alias_reports_actionable_install_state(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()

    text_result = runner.invoke(cli.app, ["agent", "codex", "check", "--workdir", str(workdir)])

    assert text_result.exit_code == 1
    assert "Codex Loopora entry check: fail" in text_result.stdout
    assert "install_state: not_installed" in text_result.stdout
    assert "Run:" in text_result.stdout
    assert f"loopora init codex --workdir {workdir.resolve()}" in text_result.stdout
    assert "No such command" not in text_result.output

    install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--json"])
    assert install.exit_code == 0, install.stdout
    json_result = runner.invoke(cli.app, ["agent", "codex", "check", "--workdir", str(workdir), "--json"])
    assert json_result.exit_code == 0, json_result.stdout
    payload = json.loads(json_result.stdout)
    summary, _legacy = _agent_check_payload(payload, status="pass")
    assert summary["check_status"] == "pass"
    assert summary["check_recovery"]["check_command"].endswith(f"--workdir {workdir.resolve()} --check")
    assert summary["agent_surface"]["entry_kind"] == "project_skill"
    assert summary["agent_surface"]["role_agents"]["builder"]["path"] == ".codex/agents/loopora-builder.toml"
    assert summary["agent_surface"]["native_dispatch"]["accepted_native_tools"] == ["spawn_agent"]
    assert "CODEX_SESSION_ID" in summary["agent_surface"]["context_identity_env"]

def test_cli_adapter_check_validates_managed_supporting_files(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()

    install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--json"])
    assert install.exit_code == 0, install.stdout

    healthy = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--check", "--json"])
    assert healthy.exit_code == 0, healthy.stdout
    _healthy_summary, healthy_payload = _agent_check_payload(json.loads(healthy.stdout), status="pass")
    assert healthy_payload["check_status"] == "pass"
    assert any(item["name"] == "supporting_file" and item["status"] == "pass" for item in healthy_payload["checks"])

    reference = workdir / ".agents" / "skills" / "loopora-run" / "references" / "loopora-recovery-matrix.md"
    reference.unlink()

    unhealthy = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--check", "--json"])
    assert unhealthy.exit_code == 1
    _unhealthy_summary, unhealthy_payload = _agent_check_payload(json.loads(unhealthy.stdout), status="fail")
    assert unhealthy_payload["check_status"] == "fail"
    assert any(item["name"] == "supporting_file" and item["status"] == "fail" for item in unhealthy_payload["checks"])
    assert not reference.exists()


def test_cli_adapter_check_validates_native_run_entry_contract(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()

    install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--json"])
    assert install.exit_code == 0, install.stdout
    run_entry = workdir / ".agents" / "skills" / "loopora-run" / "SKILL.md"
    contract_block = (
        f"## {agent_adapters.NATIVE_RUN_ENTRY_CONTRACT_TITLE}\n\n"
        + "\n".join(f"- {item}" for item in agent_adapters.NATIVE_RUN_ENTRY_CONTRACT_BULLETS)
        + "\n\n"
    )
    run_entry_text = run_entry.read_text(encoding="utf-8")
    assert contract_block in run_entry_text
    run_entry.write_text(
        run_entry_text.replace(contract_block, ""),
        encoding="utf-8",
    )

    result = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--check", "--json"])

    assert result.exit_code == 1
    _summary, payload = _agent_check_payload(json.loads(result.stdout), status="fail")
    failed_contract = next(item for item in payload["checks"] if item["name"] == "entry_native_run_contract")
    assert failed_contract["status"] == "fail"
    assert failed_contract["path"] == ".agents/skills/loopora-run/SKILL.md"
    assert "native-run contract" in failed_contract["message"]


@pytest.mark.parametrize(
    "case",
    [
        {
            "adapter": "codex",
            "entry_path": ".agents/skills/loopora-run/SKILL.md",
            "old": "name: loopora-run",
            "new": "name: loopora-start",
            "expected_message": "name=loopora-run",
        },
        {
            "adapter": "claude",
            "entry_path": ".claude/skills/loopora-plan/SKILL.md",
            "old": "disable-model-invocation: true",
            "new": "disable-model-invocation: false",
            "expected_message": "disable-model-invocation=true",
        },
        {
            "adapter": "opencode",
            "entry_path": ".opencode/commands/loopora-run.md",
            "old": "agent: loopora-orchestrator",
            "new": "agent: build",
            "expected_message": "agent=loopora-orchestrator",
        },
    ],
)
def test_cli_adapter_check_validates_entry_frontmatter_contract(
    tmp_path: Path,
    case: dict[str, str],
) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()
    adapter = case["adapter"]
    entry_path = case["entry_path"]

    install = runner.invoke(cli.app, ["init", adapter, "--workdir", str(workdir), "--json"])
    assert install.exit_code == 0, install.stdout
    healthy = runner.invoke(cli.app, ["agent", adapter, "check", "--workdir", str(workdir), "--json"])
    assert healthy.exit_code == 0, healthy.stdout
    entry = workdir / entry_path
    entry.write_text(entry.read_text(encoding="utf-8").replace(case["old"], case["new"]), encoding="utf-8")

    result = runner.invoke(cli.app, ["agent", adapter, "check", "--workdir", str(workdir), "--json"])

    assert result.exit_code == 1
    _summary, payload = _agent_check_payload(json.loads(result.stdout), status="fail")
    failed_entry = next(
        item
        for item in payload["checks"]
        if item["name"] == "entry_frontmatter_contract" and item["path"] == entry_path
    )
    assert failed_entry["status"] == "fail"
    assert case["expected_message"] in failed_entry["message"]
    assert "discoverable frontmatter" in failed_entry["message"]


def test_cli_agent_adapter_check_explains_missing_role_agent_config(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()

    install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--json"])
    assert install.exit_code == 0, install.stdout
    role_agent = workdir / ".codex" / "agents" / "loopora-builder.toml"
    role_agent.unlink()

    text_result = runner.invoke(cli.app, ["agent", "codex", "check", "--workdir", str(workdir)])

    assert text_result.exit_code == 1
    assert "fail: role_agent (.codex/agents/loopora-builder.toml)" in text_result.stdout
    assert "managed role agent config for loopora-builder is missing" in text_result.stdout
    assert f"loopora init codex --workdir {workdir.resolve()}" in text_result.stdout
    assert "before /loopora-run dispatch" in text_result.stdout

    json_result = runner.invoke(cli.app, ["agent", "codex", "check", "--workdir", str(workdir), "--json"])
    assert json_result.exit_code == 1
    _summary, payload = _agent_check_payload(json.loads(json_result.stdout), status="fail")
    failed_role = next(
        item
        for item in payload["checks"]
        if item["name"] == "role_agent" and item["path"] == ".codex/agents/loopora-builder.toml"
    )
    assert failed_role["status"] == "fail"
    assert "managed role agent config for loopora-builder is missing" in failed_role["message"]
    assert "before /loopora-run dispatch" in failed_role["message"]


def test_cli_agent_adapter_check_validates_opencode_role_permission_boundary(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()

    install = runner.invoke(cli.app, ["init", "opencode", "--workdir", str(workdir), "--json"])
    assert install.exit_code == 0, install.stdout
    healthy = runner.invoke(cli.app, ["agent", "opencode", "check", "--workdir", str(workdir), "--json"])
    assert healthy.exit_code == 0, healthy.stdout

    orchestrator_agent = workdir / ".opencode" / "agents" / "loopora-orchestrator.md"
    builder_agent = workdir / ".opencode" / "agents" / "loopora-builder.md"
    orchestrator_agent.write_text(
        orchestrator_agent.read_text(encoding="utf-8").replace(
            "    loopora-inspector: allow",
            "    loopora-inspector: deny",
        ),
        encoding="utf-8",
    )
    builder_agent.write_text(
        builder_agent.read_text(encoding="utf-8").replace(
            "  task: deny",
            "  task:\n    external-reviewer: allow",
        ),
        encoding="utf-8",
    )

    text_result = runner.invoke(cli.app, ["agent", "opencode", "check", "--workdir", str(workdir)])
    assert text_result.exit_code == 1
    assert "fail: role_permissions (.opencode/agents/loopora-orchestrator.md)" in text_result.stdout
    assert "allow only Loopora role agents" in text_result.stdout
    assert "permission.task.loopora-inspector=allow" in text_result.stdout
    assert "permission.task deny" in text_result.stdout

    json_result = runner.invoke(cli.app, ["agent", "opencode", "check", "--workdir", str(workdir), "--json"])
    assert json_result.exit_code == 1
    _summary, payload = _agent_check_payload(json.loads(json_result.stdout), status="fail")
    assert payload["check_status"] == "fail"
    failed_permissions = {
        item["path"]: item
        for item in payload["checks"]
        if item["name"] == "role_permissions" and item["status"] == "fail"
    }
    assert ".opencode/agents/loopora-orchestrator.md" in failed_permissions
    assert ".opencode/agents/loopora-builder.md" in failed_permissions
    assert "permission.task.loopora-inspector=allow" in failed_permissions[".opencode/agents/loopora-orchestrator.md"]["message"]
    assert "nested subagents/provider flows" in failed_permissions[".opencode/agents/loopora-builder.md"]["message"]


def test_cli_agent_adapter_check_validates_claude_role_frontmatter_and_tools(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()

    install = runner.invoke(cli.app, ["init", "claude", "--workdir", str(workdir), "--json"])
    assert install.exit_code == 0, install.stdout
    healthy = runner.invoke(cli.app, ["agent", "claude", "check", "--workdir", str(workdir), "--json"])
    assert healthy.exit_code == 0, healthy.stdout

    inspector_agent = workdir / ".claude" / "agents" / "loopora-inspector.md"
    orchestrator_agent = workdir / ".claude" / "agents" / "loopora-orchestrator.md"
    inspector_agent.write_text(
        inspector_agent.read_text(encoding="utf-8").replace(
            "tools: Read, Glob, Grep, Bash",
            "tools: Read, Glob, Grep, Bash, Write",
        ),
        encoding="utf-8",
    )
    orchestrator_agent.write_text(
        orchestrator_agent.read_text(encoding="utf-8").replace(
            "name: loopora-orchestrator",
            "name: loopora-coordinator",
        ),
        encoding="utf-8",
    )

    text_result = runner.invoke(cli.app, ["agent", "claude", "check", "--workdir", str(workdir)])
    assert text_result.exit_code == 1
    assert "fail: role_permissions (.claude/agents/loopora-inspector.md)" in text_result.stdout
    assert "fail: role_permissions (.claude/agents/loopora-orchestrator.md)" in text_result.stdout
    assert "discoverable frontmatter and role tool allowlist" in text_result.stdout
    assert "tools=Bash,Glob,Grep,Read" in text_result.stdout
    assert "name=loopora-orchestrator" in text_result.stdout

    json_result = runner.invoke(cli.app, ["agent", "claude", "check", "--workdir", str(workdir), "--json"])
    assert json_result.exit_code == 1
    _summary, payload = _agent_check_payload(json.loads(json_result.stdout), status="fail")
    assert payload["check_status"] == "fail"
    failed_permissions = {
        item["path"]: item
        for item in payload["checks"]
        if item["name"] == "role_permissions" and item["status"] == "fail"
    }
    assert "tools=Bash,Glob,Grep,Read" in failed_permissions[".claude/agents/loopora-inspector.md"]["message"]
    assert "name=loopora-orchestrator" in failed_permissions[".claude/agents/loopora-orchestrator.md"]["message"]


def test_cli_agent_adapter_check_validates_codex_role_toml_and_contract(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()

    install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--json"])
    assert install.exit_code == 0, install.stdout
    healthy = runner.invoke(cli.app, ["agent", "codex", "check", "--workdir", str(workdir), "--json"])
    assert healthy.exit_code == 0, healthy.stdout

    builder_agent = workdir / ".codex" / "agents" / "loopora-builder.toml"
    guide_agent = workdir / ".codex" / "agents" / "loopora-guide.toml"
    builder_agent.write_text(
        builder_agent.read_text(encoding="utf-8").replace(
            'name = "loopora-builder"',
            'name = "loopora-maker"',
        ),
        encoding="utf-8",
    )
    guide_agent.write_text(
        guide_agent.read_text(encoding="utf-8").replace(
            "Do not launch codex, claude, or opencode from inside this role.",
            "Nested provider CLIs may be launched from inside this role.",
        ),
        encoding="utf-8",
    )

    text_result = runner.invoke(cli.app, ["agent", "codex", "check", "--workdir", str(workdir)])
    assert text_result.exit_code == 1
    assert "fail: role_permissions (.codex/agents/loopora-builder.toml)" in text_result.stdout
    assert "fail: role_permissions (.codex/agents/loopora-guide.toml)" in text_result.stdout
    assert "discoverable TOML metadata and the Loopora role contract" in text_result.stdout
    assert "name=loopora-builder" in text_result.stdout
    assert "Do not launch codex, claude, or opencode" in text_result.stdout

    json_result = runner.invoke(cli.app, ["agent", "codex", "check", "--workdir", str(workdir), "--json"])
    assert json_result.exit_code == 1
    _summary, payload = _agent_check_payload(json.loads(json_result.stdout), status="fail")
    assert payload["check_status"] == "fail"
    failed_permissions = {
        item["path"]: item
        for item in payload["checks"]
        if item["name"] == "role_permissions" and item["status"] == "fail"
    }
    assert "name=loopora-builder" in failed_permissions[".codex/agents/loopora-builder.toml"]["message"]
    assert "Do not launch codex, claude, or opencode" in failed_permissions[".codex/agents/loopora-guide.toml"]["message"]


def test_cli_codex_adapter_install_conflict_guides_recovery_without_overwriting(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    conflict = workdir / ".agents" / "skills" / "loopora-plan" / "SKILL.md"
    conflict.parent.mkdir(parents=True)
    conflict.write_text("# User-owned Codex entry\n", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir)])

    assert result.exit_code == 1
    assert result.stdout == ""
    assert conflict.read_text(encoding="utf-8") == "# User-owned Codex entry\n"
    assert not (workdir / ".loopora" / "adapters" / "codex" / "manifest.json").exists()
    error_text = _error_text(result)
    assert "Codex Loopora entry was not installed." in error_text
    assert f"target project: {workdir.resolve()}" in error_text
    assert "left the project unchanged" in error_text
    assert "conflicting files:" in error_text
    assert ".agents/skills/loopora-plan/SKILL.md" in error_text
    assert "recovery:" in error_text
    assert "Inspect the listed file or config" in error_text
    assert "move or rename it" in error_text
    assert "loopora init codex --workdir" in error_text
    assert "refusing to overwrite" not in error_text
    assert "cli.command.failed" not in error_text

    json_result = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--json"])

    assert json_result.exit_code == 1
    assert _error_text(json_result) == ""
    payload = json.loads(json_result.stdout)
    assert payload["loop_recovery"] == "adapter_install_conflict"
    assert payload["install_status"] == "conflict"
    assert payload["status"] == "not_installed"
    assert payload["conflicting_files"] == [".agents/skills/loopora-plan/SKILL.md"]
    assert payload["recovery"]["state"] == "install_conflict"
    _assert_loopora_cli_command(payload["recovery"]["install_command"], "loopora init codex --workdir")
    assert "left the project unchanged" in payload["recovery"]["summary"]

def test_cli_codex_loop_requires_ready_bundle(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "run",
            "--workdir",
            str(workdir),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
        ],
    )

    assert result.exit_code == 1
    output_text = result.output
    assert _error_text(result) == ""
    assert "loop_recovery: run /loopora-plan before /loopora-run can start" in output_text
    assert "ready Loop preview" in output_text
    assert "required_inputs:" in output_text
    assert "- task_goal" in output_text
    assert "- fake_done_risks" in output_text
    assert "- required_evidence" in output_text
    assert "- judgment_tradeoffs" in output_text
    assert "ask_user: What long-running task should Loopora govern?" in output_text
    assert "question_action: Use the host's official user-question or follow-up capability" in output_text
    assert "example_user_reply:" in output_text
    assert "task_message_template: Goal: ..." in output_text
    assert "Fake-done risks: ..." in output_text
    assert "Required evidence: ..." in output_text
    assert "Judgment tradeoffs: ..." in output_text
    assert "first_task_message_example:" in output_text
    assert "After /loopora-plan, send: Goal:" in output_text
    assert "debug_cli_example_command:" in output_text
    _assert_labeled_loopora_agent_command(output_text, "debug_cli_example_command", "plan", json_mode=False)
    assert "READY Loopora bundle" not in output_text

def test_cli_claude_adapter_install_uninstall_are_idempotent_and_preserve_user_config(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    claude_md = workdir / "CLAUDE.md"
    claude_settings = workdir / ".claude" / "settings.json"
    claude_settings.parent.mkdir()
    claude_md.write_text("# User Claude instructions\n", encoding="utf-8")
    claude_settings.write_text('{"permissions": {"allow": []}}\n', encoding="utf-8")
    runner = CliRunner()

    first_install = runner.invoke(cli.app, ["init", "claude", "--workdir", str(workdir), "--json"])

    assert first_install.exit_code == 0, first_install.stdout
    assert json.loads(first_install.stdout)["status"] == "installed"
    skill_paths = _claude_skill_paths(workdir)
    assert skill_paths["plan"].exists()
    assert skill_paths["run"].exists()
    manifest_path, first_manifest = _assert_claude_managed_install(workdir, skill_paths)
    assert claude_md.read_text(encoding="utf-8") == "# User Claude instructions\n"
    settings_after_install = json.loads(claude_settings.read_text(encoding="utf-8"))
    assert settings_after_install["permissions"] == {"allow": []}
    assert _claude_settings_has_loopora_session_hook(settings_after_install)

    second_install = runner.invoke(cli.app, ["init", "claude", "--workdir", str(workdir), "--json"])

    assert second_install.exit_code == 0, second_install.stdout
    assert manifest_path.read_text(encoding="utf-8") == first_manifest

    first_uninstall = runner.invoke(cli.app, ["uninstall", "claude", "--workdir", str(workdir), "--json"])
    second_uninstall = runner.invoke(cli.app, ["uninstall", "claude", "--workdir", str(workdir), "--json"])

    assert first_uninstall.exit_code == 0, first_uninstall.stdout
    assert second_uninstall.exit_code == 0, second_uninstall.stdout
    assert json.loads(first_uninstall.stdout)["status"] == "not_installed"
    assert json.loads(second_uninstall.stdout)["status"] == "not_installed"
    assert not skill_paths["plan"].exists()
    assert not skill_paths["run"].exists()
    assert not (workdir / ".claude" / "hooks" / "loopora-session-context.py").exists()
    assert claude_md.exists()
    assert claude_settings.exists()
    settings_after_uninstall = json.loads(claude_settings.read_text(encoding="utf-8"))
    assert settings_after_uninstall == {"permissions": {"allow": []}}

def test_claude_adapter_removes_obsolete_managed_command_wrappers(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    commands_dir = workdir / ".claude" / "commands"
    commands_dir.mkdir(parents=True)
    gen_command = commands_dir / "loopora-plan.md"
    loop_command = commands_dir / "loopora-run.md"
    gen_command.write_text("<!-- LOOPORA-MANAGED: claude-code-adapter old gen -->\n", encoding="utf-8")
    loop_command.write_text("<!-- LOOPORA-MANAGED: claude-code-adapter old loop -->\n", encoding="utf-8")

    result = service.install_agent_adapter("claude", workdir=workdir)

    assert result["status"] == "installed"
    assert result["removed_obsolete_files"] == [
        ".claude/commands/loopora-plan.md",
        ".claude/commands/loopora-run.md",
    ]
    assert not gen_command.exists()
    assert not loop_command.exists()
    manifest = json.loads((workdir / ".loopora" / "adapters" / "claude" / "manifest.json").read_text(encoding="utf-8"))
    assert ".claude/commands/loopora-plan.md" not in {item["path"] for item in manifest["managed_files"]}

def test_claude_adapter_refuses_unowned_obsolete_command_wrappers(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    command = workdir / ".claude" / "commands" / "loopora-plan.md"
    command.parent.mkdir(parents=True)
    command.write_text("# User-owned Claude command\n", encoding="utf-8")

    with pytest.raises(LooporaConflictError, match="obsolete Claude Code adapter files"):
        service.install_agent_adapter("claude", workdir=workdir)

    assert command.read_text(encoding="utf-8") == "# User-owned Claude command\n"
    assert not (workdir / ".loopora" / "adapters" / "claude" / "manifest.json").exists()

@pytest.mark.parametrize(
    ("adapter", "old_paths"),
    [
        (
            "codex",
            [
                ".agents/skills/loopora-gen/SKILL.md",
                ".agents/skills/loopora-loop/SKILL.md",
            ],
        ),
        (
            "claude",
            [
                ".claude/skills/loopora-gen/SKILL.md",
                ".claude/skills/loopora-loop/SKILL.md",
            ],
        ),
        (
            "opencode",
            [
                ".opencode/commands/loopora-gen.md",
                ".opencode/commands/loopora-loop.md",
            ],
        ),
    ],
)
def test_adapter_install_removes_legacy_managed_slash_entries(service_factory, tmp_path: Path, adapter: str, old_paths: list[str]) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / adapter
    workdir.mkdir()
    for relative_path in old_paths:
        target = workdir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        marker = agent_adapters.MANAGED_MARKERS[adapter]
        target.write_text(f"<!-- {marker} legacy slash entry -->\n", encoding="utf-8")

    result = service.install_agent_adapter(adapter, workdir=workdir)

    assert result["status"] == "installed"
    for relative_path in old_paths:
        assert relative_path in result["removed_obsolete_files"]
        assert not (workdir / relative_path).exists()
    manifest = json.loads((workdir / ".loopora" / "adapters" / adapter / "manifest.json").read_text(encoding="utf-8"))
    managed_paths = {item["path"] for item in manifest["managed_files"]}
    assert all(relative_path not in managed_paths for relative_path in old_paths)

def test_cli_claude_loop_requires_ready_bundle(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()

    result = runner.invoke(cli.app, ["agent", "claude", "run", "--workdir", str(workdir), "--no-web"])

    assert result.exit_code == 1
    output_text = result.output
    assert _error_text(result) == ""
    assert "loop_recovery: run /loopora-plan before /loopora-run can start" in output_text
    assert "ready Loop preview" in output_text
    assert "READY Loopora bundle" not in output_text

def test_cli_opencode_adapter_install_uninstall_are_idempotent_and_preserve_user_config(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    opencode_json = workdir / "opencode.json"
    opencode_project_json = workdir / ".opencode" / "opencode.jsonc"
    opencode_agent = workdir / ".opencode" / "agents" / "review.md"
    opencode_project_json.parent.mkdir()
    opencode_agent.parent.mkdir()
    opencode_json.write_text('{"model": "user/model"}\n', encoding="utf-8")
    opencode_project_json.write_text('{"permission": {"bash": "ask"}}\n', encoding="utf-8")
    opencode_agent.write_text("# User-owned OpenCode agent\n", encoding="utf-8")
    runner = CliRunner()

    first_install = runner.invoke(cli.app, ["init", "opencode", "--workdir", str(workdir), "--json"])

    assert first_install.exit_code == 0, first_install.stdout
    assert json.loads(first_install.stdout)["status"] == "installed"
    command_paths = _opencode_command_paths(workdir)
    assert command_paths["plan"].exists()
    assert command_paths["run"].exists()
    manifest_path, first_manifest = _assert_opencode_managed_install(workdir, command_paths)
    assert opencode_json.read_text(encoding="utf-8") == '{"model": "user/model"}\n'
    assert opencode_project_json.read_text(encoding="utf-8") == '{"permission": {"bash": "ask"}}\n'
    assert opencode_agent.read_text(encoding="utf-8") == "# User-owned OpenCode agent\n"

    second_install = runner.invoke(cli.app, ["init", "opencode", "--workdir", str(workdir), "--json"])

    assert second_install.exit_code == 0, second_install.stdout
    assert manifest_path.read_text(encoding="utf-8") == first_manifest

    first_uninstall = runner.invoke(cli.app, ["uninstall", "opencode", "--workdir", str(workdir), "--json"])
    second_uninstall = runner.invoke(cli.app, ["uninstall", "opencode", "--workdir", str(workdir), "--json"])

    assert first_uninstall.exit_code == 0, first_uninstall.stdout
    assert second_uninstall.exit_code == 0, second_uninstall.stdout
    assert json.loads(first_uninstall.stdout)["status"] == "not_installed"
    assert json.loads(second_uninstall.stdout)["status"] == "not_installed"
    assert not command_paths["plan"].exists()
    assert not command_paths["run"].exists()
    assert opencode_json.exists()
    assert opencode_project_json.exists()
    assert opencode_agent.exists()

def test_adapter_project_entries_are_namespaced_and_do_not_set_host_models(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    banned_model_defaults = (
        "gpt-",
        "anthropic/",
        "openai/",
        "model =",
        "\nmodel:",
        "reasoning_effort =",
        "\nreasoning_effort:",
    )

    for adapter in ("codex", "claude", "opencode"):
        workdir = tmp_path / adapter
        workdir.mkdir()
        service.install_agent_adapter(adapter, workdir=workdir)
        manifest = json.loads((workdir / ".loopora" / "adapters" / adapter / "manifest.json").read_text(encoding="utf-8"))
        managed_paths = [item["path"] for item in manifest["managed_files"]]
        assert managed_paths
        for relative_path in managed_paths:
            name = Path(relative_path).name
            if relative_path.endswith((".md", ".toml")) and "loopora-session-context" not in relative_path:
                assert name.startswith("loopora-") or name == "SKILL.md"
            text = (workdir / relative_path).read_text(encoding="utf-8")
            for banned in banned_model_defaults:
                assert banned not in text
        assert not (workdir / ".claude" / "commands" / "loopora-plan.md").exists()

def test_cli_opencode_loop_requires_ready_bundle(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()

    result = runner.invoke(cli.app, ["agent", "opencode", "run", "--workdir", str(workdir), "--no-web"])

    assert result.exit_code == 1
    output_text = result.output
    assert _error_text(result) == ""
    assert "loop_recovery: run /loopora-plan before /loopora-run can start" in output_text
    assert "ready Loop preview" in output_text
    assert "READY Loopora bundle" not in output_text
