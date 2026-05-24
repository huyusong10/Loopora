from __future__ import annotations

from agent_adapter_helpers import *

def test_agent_native_result_template_uses_schema_shaped_null_scaffold() -> None:
    template = ServiceAgentNativeMixin._agent_native_result_template(
        {
            "adapter": "codex",
            "run_id": "run-scaffold",
            "step_id": "builder_step",
            "role_dispatch": {
                "target_agent": "loopora-builder",
                "native_trace_contract": {
                    "optional": True,
                    "field": "native_trace",
                    "trace_ref_field": "native_trace_ref",
                },
            },
            "native_todo": {
                "recommended": True,
                "not_evidence": True,
                "items": ["Dispatch loopora-builder through the native task tool."],
            },
            "output_schema": {
                "type": "object",
                "required": ["summary", "checks", "nested"],
                "properties": {
                    "summary": {"type": "string"},
                    "checks": {"type": "array", "items": {"type": "string"}},
                    "nested": {
                        "type": "object",
                        "required": ["status"],
                        "properties": {
                            "status": {"type": "string", "enum": ["covered", "weak"]},
                            "notes": {"type": "array", "items": {"type": "string"}},
                        },
                        "additionalProperties": False,
                    },
                    "optional_flag": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "submit_hint": {
                "command": "loopora agent codex submit --run-id run-scaffold --step-id builder_step --result-file /tmp/builder.result.json --json",
                "result_file_absolute_path": "/tmp/builder.result.json",
                "result_template_absolute_path": "/tmp/builder.result.template.json",
            },
            "judgment_contract": {
                "coverage_targets": [
                    {
                        "id": "done_when.check_001",
                        "kind": "done_when",
                        "text": "The primary user flow works end to end.",
                        "required": True,
                    },
                    {
                        "id": "success_surface.surface_001",
                        "kind": "success_surface",
                        "label": "Success surface 1",
                        "required": False,
                    },
                ]
            },
        }
    )

    assert template["loopora_result_contract"]["result_is_schema_shaped_scaffold"] is True
    assert template["loopora_result_contract"]["replace_null_placeholders_before_submit"] is True
    assert template["loopora_result_contract"]["coverage_target_ids"] == [
        "done_when.check_001",
        "success_surface.surface_001",
    ]
    assert template["loopora_result_contract"]["coverage_targets"] == [
        {
            "id": "done_when.check_001",
            "kind": "done_when",
            "required": True,
            "text": "The primary user flow works end to end.",
        },
        {
            "id": "success_surface.surface_001",
            "kind": "success_surface",
            "required": False,
            "text": "Success surface 1",
        },
    ]
    assert template["loopora_result_contract"]["result_file_to_write"] == "/tmp/builder.result.json"
    assert template["loopora_result_contract"]["submit_command"].endswith("--json")
    assert template["loopora_result_contract"]["result_template_path"] == "/tmp/builder.result.template.json"
    assert template["loopora_result_contract"]["native_todo"]["not_evidence"] is True
    assert template["loopora_result_contract"]["native_trace_contract"]["field"] == "native_trace"
    assert template["loopora_host_dispatch"]["native_trace"]["available"] is False
    assert template["loopora_host_dispatch"]["native_tool_name"] == ""
    assert template["loopora_host_dispatch"]["native_trace_ref"] == ""
    assert template["result"] == {
        "summary": None,
        "checks": [None],
        "nested": {"status": None, "notes": [None]},
        "optional_flag": None,
    }

def test_agent_native_result_template_projects_active_iteration_repair_focus() -> None:
    template = ServiceAgentNativeMixin._agent_native_result_template(
        {
            "adapter": "codex",
            "run_id": "run-repair",
            "step_id": "builder_step",
            "role_dispatch": {"target_agent": "loopora-builder"},
            "iteration_repair": {
                "active": True,
                "source_step_id": "gatekeeper_step",
                "source_role": "GateKeeper",
                "status": "blocked",
                "summary": "GateKeeper rejected the pass attempt.",
                "blocking_items": ["gatekeeper_pass_refs_not_supporting_evidence: cite supporting upstream proof."],
                "recommended_next_action": "Produce direct project-owned proof before asking GateKeeper to pass again.",
                "evidence_refs": ["ev_000_03_gatekeeper_step"],
                "top_gaps": [
                    {
                        "target_id": "gatekeeper.finish",
                        "status": "blocked",
                        "text": "GateKeeper needs supporting evidence.",
                    }
                ],
            },
            "output_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        }
    )

    repair = template["loopora_result_contract"]["iteration_repair"]
    assert repair["source_step_id"] == "gatekeeper_step"
    assert repair["blocking_items"][0].startswith("gatekeeper_pass_refs_not_supporting_evidence:")
    assert repair["recommended_next_action"].startswith("Produce direct project-owned proof")
    assert repair["top_gaps"][0]["target_id"] == "gatekeeper.finish"
    assert "prompt" not in template["loopora_result_contract"]

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

@pytest.mark.parametrize(
    ("adapter", "label"),
    [
        ("codex", "Codex"),
        ("claude", "Claude Code"),
        ("opencode", "OpenCode"),
    ],
)
def test_cli_adapter_install_human_output_points_to_agent_next_steps(tmp_path: Path, adapter: str, label: str) -> None:
    workdir = tmp_path / adapter
    workdir.mkdir()
    runner = CliRunner()
    entry_paths = {
        "codex": ".agents/skills/loopora-plan/SKILL.md and .agents/skills/loopora-run/SKILL.md",
        "claude": ".claude/skills/loopora-plan/SKILL.md and .claude/skills/loopora-run/SKILL.md",
        "opencode": ".opencode/commands/loopora-plan.md and .opencode/commands/loopora-run.md",
    }

    result = runner.invoke(cli.app, ["init", adapter, "--workdir", str(workdir)])

    assert result.exit_code == 0, result.stdout
    assert f"{label} Loopora entry is installed" in result.stdout
    assert f"target project: {workdir.resolve()}" in result.stdout
    assert "next:" in result.stdout
    assert f"Return to {label} in this project" in result.stdout
    assert "task goal, fake-done risk, and required evidence" in result.stdout
    assert "/loopora-plan" in result.stdout
    assert "READY Loop preview" in result.stdout
    assert "/loopora-run" in result.stdout
    assert "same Agent session" in result.stdout
    assert "If /loopora-plan or /loopora-run is not visible" in result.stdout
    assert entry_paths[adapter] in result.stdout
    assert f"refresh or restart {label}" in result.stdout
    assert "observe evidence, gaps, and verdicts" in result.stdout
    assert "first task message example:" in result.stdout
    assert "Goal:" in result.stdout
    assert "Fake-done risks:" in result.stdout
    assert "Required evidence:" in result.stdout
    assert "Judgment tradeoffs:" in result.stdout
    assert "diagnostics:" in result.stdout
    assert "- verify install:" in result.stdout
    assert f"loopora init {adapter} --workdir {workdir.resolve()} --check" in result.stdout
    assert "- agent-runtime check:" in result.stdout
    assert f"loopora agent {adapter} check --workdir {workdir.resolve()}" in result.stdout
    assert "managed files:" in result.stdout
    assert result.stdout.index("next:") < result.stdout.index("managed files:")
    assert result.stdout.index("diagnostics:") < result.stdout.index("managed files:")
    assert "adapter installed" not in result.stdout
    assert "YAML bundle" not in result.stdout

    json_result = runner.invoke(cli.app, ["init", adapter, "--workdir", str(workdir), "--json"])

    assert json_result.exit_code == 0, json_result.stdout
    payload = json.loads(json_result.stdout)
    assert any(f"Return to {label}" in item for item in payload["next_steps"])
    assert any("/loopora-plan" in item for item in payload["next_steps"])
    assert any("/loopora-run" in item for item in payload["next_steps"])
    assert any(entry_paths[adapter] in item for item in payload["next_steps"])
    assert any(f"refresh or restart {label}" in item for item in payload["next_steps"])
    assert "Goal:" in payload["first_task_message_example"]
    assert "Fake-done risks:" in payload["first_task_message_example"]
    assert "Required evidence:" in payload["first_task_message_example"]
    assert "Judgment tradeoffs:" in payload["first_task_message_example"]
    assert payload["next_commands"]["plan"] == "/loopora-plan"
    assert payload["next_commands"]["run"] == "/loopora-run"
    _assert_loopora_cli_command(
        payload["next_commands"]["check"],
        f"loopora init {adapter} --workdir {workdir.resolve()} --check",
    )
    _assert_loopora_cli_command(
        payload["next_commands"]["agent_check"],
        f"loopora agent {adapter} check --workdir {workdir.resolve()}",
    )

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
    assert payload["check_recovery"]["state"] == "not_installed"
    assert payload["check_recovery"]["details_are_expected"] is True
    assert payload["check_recovery"]["install_command"].endswith(f"--workdir {workdir.resolve()}")
    assert any(item["name"] == "supporting_file" for item in payload["checks"])

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
    assert payload["check_status"] == "pass"
    assert payload["check_recovery"]["check_command"].endswith(f"--workdir {workdir.resolve()} --check")
    assert "first_task_message_example" in payload
    assert payload["next_commands"]["plan"] == "/loopora-plan"

def test_cli_adapter_check_validates_managed_supporting_files(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()

    install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--json"])
    assert install.exit_code == 0, install.stdout

    healthy = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--check", "--json"])
    assert healthy.exit_code == 0, healthy.stdout
    healthy_payload = json.loads(healthy.stdout)
    assert healthy_payload["check_status"] == "pass"
    assert any(item["name"] == "supporting_file" and item["status"] == "pass" for item in healthy_payload["checks"])

    reference = workdir / ".agents" / "skills" / "loopora-run" / "references" / "loopora-recovery-matrix.md"
    reference.unlink()

    unhealthy = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--check", "--json"])
    assert unhealthy.exit_code == 1
    unhealthy_payload = json.loads(unhealthy.stdout)
    assert unhealthy_payload["check_status"] == "fail"
    assert any(item["name"] == "supporting_file" and item["status"] == "fail" for item in unhealthy_payload["checks"])
    assert not reference.exists()

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
    payload = json.loads(json_result.stdout)
    failed_role = next(
        item
        for item in payload["checks"]
        if item["name"] == "role_agent" and item["path"] == ".codex/agents/loopora-builder.toml"
    )
    assert failed_role["status"] == "fail"
    assert "managed role agent config for loopora-builder is missing" in failed_role["message"]
    assert "before /loopora-run dispatch" in failed_role["message"]

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
    assert (
        "task_message_template: Goal: ...; Fake-done risks: ...; Required evidence: ...; Judgment tradeoffs: ..."
        in output_text
    )
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
