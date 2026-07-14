from __future__ import annotations

import shlex

from agent_native_v3_helpers import assert_agent_v3_envelope
from agent_adapter_test_support import (
    CliRunner,
    Path,
    _assert_labeled_loopora_agent_command,
    _assert_loopora_cli_command,
    _error_text,
    cli,
    json,
    pytest,
)
from loopora import agent_adapter_command_prefix
from loopora import diagnose_doctor
from loopora.branding import APP_HOME_ENV


def test_cli_init_current_preserves_install_proof_when_plan_handoff_is_blocked(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    app_home = tmp_path / "home"
    workdir.mkdir()
    app_home.mkdir()
    real_build_doctor_report = diagnose_doctor.build_doctor_report

    def blocked_report(**kwargs):
        report = real_build_doctor_report(**kwargs)
        return {
            **report,
            "first_task_handoff_executable": False,
            "first_task_handoff_blockers": ["app_state_not_ready"],
            "next_steps": ["Preview the safe App-state recovery before /loopora-plan."],
        }

    monkeypatch.setattr("loopora.cli_agent_adapter_lifecycle_commands.build_doctor_report", blocked_report)
    result = CliRunner().invoke(
        cli.app,
        ["init", "current", "--workdir", str(workdir), "--json"],
        env={
            "CODEX_SESSION_ID": "",
            "CODEX_THREAD_ID": "private-thread",
            "CLAUDE_SESSION_ID": "",
            "OPENCODE_SESSION_ID": "",
            APP_HOME_ENV: str(app_home),
        },
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "installed"
    assert payload["setup_status"] == "needs_attention"
    assert payload["setup_ready"] is False
    assert payload["readiness"]["first_task_handoff_blockers"] == ["app_state_not_ready"]
    assert (workdir / ".agents" / "skills" / "loopora-plan" / "SKILL.md").is_file()
    assert "private-thread" not in result.stdout


def test_cli_init_current_chinese_plain_setup_and_json_semantics_stay_separate(tmp_path: Path) -> None:
    workdir, json_workdir, app_home = tmp_path / "project", tmp_path / "json-project", tmp_path / "home"
    workdir.mkdir()
    json_workdir.mkdir()
    app_home.mkdir()
    env = {
        "CODEX_SESSION_ID": "",
        "CODEX_THREAD_ID": "private-thread",
        "CLAUDE_SESSION_ID": "",
        "OPENCODE_SESSION_ID": "",
        APP_HOME_ENV: str(app_home),
    }
    runner = CliRunner()

    plain = runner.invoke(
        cli.app,
        ["init", "current", "--workdir", str(workdir), "--language", "zh-CN"],
        env=env,
    )
    structured = runner.invoke(
        cli.app,
        ["init", "current", "--workdir", str(json_workdir), "--language", "中文", "--json"],
        env=env,
    )

    assert plain.exit_code == structured.exit_code == 0
    assert all(term in plain.stdout for term in ("同一 Agent 设置：就绪", "当前宿主：Codex", "计划交接：可运行", "--language zh"))
    assert all(term not in plain.stdout for term in ("same-Agent setup:", "current host:", "plan handoff:"))
    payload = json.loads(structured.stdout)
    assert payload["kind"] == "same_agent_setup"
    assert payload["setup_ready"] is True
    assert payload["readiness"]["first_task_handoff_executable"] is True
    assert "language" not in payload
    assert "--language" not in structured.stdout
    assert "private-thread" not in plain.stdout + structured.stdout


def test_cli_init_chinese_fallback_check_and_workdir_recovery_preserve_language(tmp_path: Path) -> None:
    workdir, app_home = tmp_path / "project", tmp_path / "home"
    missing_workdir = tmp_path / "missing"
    workdir.mkdir()
    app_home.mkdir()
    no_host_env = {
        "CODEX_SESSION_ID": "",
        "CODEX_THREAD_ID": "",
        "CLAUDE_SESSION_ID": "",
        "OPENCODE_SESSION_ID": "",
        APP_HOME_ENV: str(app_home),
    }
    runner = CliRunner()

    fallback = runner.invoke(
        cli.app,
        ["init", "current", "--workdir", str(workdir), "--language", "zh"],
        env=no_host_env,
    )
    install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--language", "zh"], env=no_host_env)
    check = runner.invoke(
        cli.app,
        ["init", "codex", "--workdir", str(workdir), "--check", "--language", "zh"],
        env=no_host_env,
    )
    blocked = runner.invoke(
        cli.app,
        ["init", "codex", "--workdir", str(missing_workdir), "--language", "zh"],
        env=no_host_env,
    )
    invalid = runner.invoke(
        cli.app,
        ["init", "current", "--workdir", str(workdir), "--language", "fr", "--json"],
        env=no_host_env,
    )

    assert fallback.exit_code == blocked.exit_code == 1
    assert install.exit_code == check.exit_code == 0
    assert fallback.stdout.count("--language zh") == 3
    assert all(term in fallback.stdout for term in ("当前 Agent 宿主检测：不可用", "请选择将继续此任务的 Agent"))
    assert all(term in install.stdout for term in ("项目入口已安装", "首次任务消息交接：", "就绪报告：", "--language zh"))
    assert all(term in check.stdout for term in ("项目入口检查：通过", "安装状态：已安装", "诊断：", "--language zh"))
    agent_check_line = next(line for line in check.stdout.splitlines() if "agent codex check --workdir" in line)
    assert agent_check_line.endswith("--language zh")
    web_start_line = next(line for line in check.stdout.splitlines() if "loopora serve --open" in line)
    assert web_start_line.endswith("--language zh")
    assert all(term in blocked.stdout for term in ("项目入口未安装", "项目目录状态：不存在", "目标存在后重试安装"))
    assert blocked.stdout.count("--language zh") == 2
    assert not missing_workdir.exists()
    assert invalid.exit_code == 1
    assert json.loads(invalid.stdout)["error"].startswith("invalid --language: expected one of: en, zh")


def _plain_recovery_text(result) -> str:
    parts = [result.output, _error_text(result)]
    return "\n".join(part for part in parts if part)


def test_cli_codex_adapter_install_conflict_guides_recovery_without_overwriting(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workdir = tmp_path / "project"
    conflict = workdir / ".agents" / "skills" / "loopora-plan" / "SKILL.md"
    conflict.parent.mkdir(parents=True)
    conflict.write_text("# User-owned Codex entry\n", encoding="utf-8")
    runner = CliRunner()
    monkeypatch.setenv("UV_RUN_RECURSION_DEPTH", "1")
    monkeypatch.setattr(agent_adapter_command_prefix, "current_loopora_cli_entry", lambda: "uv run loopora")
    source_entry = agent_adapter_command_prefix.current_project_file_loopora_cli_entry()

    result = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir)])

    assert result.exit_code == 1
    assert conflict.read_text(encoding="utf-8") == "# User-owned Codex entry\n"
    assert not (workdir / ".loopora" / "adapters" / "codex" / "manifest.json").exists()
    error_text = _plain_recovery_text(result)
    assert "Codex Loopora entry was not installed." in error_text
    assert f"target project: {workdir.resolve()}" in error_text
    assert "left the project unchanged" in error_text
    assert "conflicting files:" in error_text
    assert ".agents/skills/loopora-plan/SKILL.md" in error_text
    assert "recovery:" in error_text
    assert "Inspect the listed file or config" in error_text
    assert "move or rename it" in error_text
    assert f"{source_entry} init codex --workdir" in error_text
    assert "loopora init codex --workdir" in error_text
    assert "refusing to overwrite" not in error_text
    assert "cli.command.failed" not in error_text

    zh_result = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--language", "zh-CN"])
    zh_error = _plain_recovery_text(zh_result)
    assert zh_result.exit_code == 1
    assert all(term in zh_error for term in ("项目入口未安装", "冲突文件：", "恢复：", "然后重跑：", "--language zh"))
    assert "left the project unchanged" not in zh_error

    json_result = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--json"])

    assert json_result.exit_code == 1
    payload = json.loads(json_result.stdout)
    assert payload["loop_recovery"] == "adapter_install_conflict"
    assert payload["install_status"] == "conflict"
    assert payload["status"] == "not_installed"
    assert payload["conflicting_files"] == [".agents/skills/loopora-plan/SKILL.md"]
    assert payload["recovery"]["state"] == "install_conflict"
    assert f"{source_entry} init codex --workdir" in payload["recovery"]["install_command"]
    _assert_loopora_cli_command(payload["recovery"]["install_command"], "loopora init codex --workdir")
    assert "left the project unchanged" in payload["recovery"]["summary"]


def test_cli_claude_adapter_install_conflict_redacts_settings_parse_details(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    settings_path = workdir / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("{not json}\n", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(cli.app, ["init", "claude", "--workdir", str(workdir)])

    assert result.exit_code == 1
    assert settings_path.read_text(encoding="utf-8") == "{not json}\n"
    error_text = _plain_recovery_text(result)
    assert "Claude Code Loopora entry was not installed." in error_text
    assert "left the project unchanged" in error_text
    assert "conflicting files:" in error_text
    assert "- .claude/settings.json" in error_text
    assert str(settings_path) not in error_text
    assert "Expecting property name" not in error_text

    json_result = runner.invoke(cli.app, ["init", "claude", "--workdir", str(workdir), "--json"])

    assert json_result.exit_code == 1
    payload = json.loads(json_result.stdout)
    encoded = json.dumps(payload, ensure_ascii=False)
    assert payload["loop_recovery"] == "adapter_install_conflict"
    assert payload["conflicting_files"] == [".claude/settings.json"]
    assert payload["raw_conflict"] == "Claude Code settings must be valid JSON: .claude/settings.json"
    assert str(settings_path) not in encoded
    assert "Expecting property name" not in encoded


def test_cli_codex_adapter_install_conflict_redacts_unreadable_managed_file_details(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workdir = tmp_path / "project"
    conflict = workdir / ".agents" / "skills" / "loopora-plan" / "SKILL.md"
    local_path = tmp_path / "private" / "SKILL.md"
    conflict.parent.mkdir(parents=True)
    conflict.write_text("# User-owned Codex entry\n", encoding="utf-8")
    original_read_text = Path.read_text

    def fail_conflict_read(path: Path, *args: object, **kwargs: object) -> str:
        if path == conflict:
            raise OSError(f"permission denied: {local_path}")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_conflict_read)
    runner = CliRunner()

    result = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir)])

    assert result.exit_code == 1
    error_text = _plain_recovery_text(result)
    assert ".agents/skills/loopora-plan/SKILL.md" in error_text
    assert str(conflict) not in error_text
    assert str(local_path) not in error_text
    assert "permission denied" not in error_text

    json_result = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--json"])

    assert json_result.exit_code == 1
    payload = json.loads(json_result.stdout)
    encoded = json.dumps(payload, ensure_ascii=False)
    assert payload["loop_recovery"] == "adapter_install_conflict"
    assert payload["conflicting_files"] == [".agents/skills/loopora-plan/SKILL.md"]
    assert "refusing to overwrite non-Loopora Codex adapter files" in payload["raw_conflict"]
    assert str(conflict) not in encoded
    assert str(local_path) not in encoded
    assert "permission denied" not in encoded


@pytest.mark.parametrize(
    ("plain_template", "json_template", "retry_kind", "retry_command_fragment"),
    [
        (
            ["init", "codex", "--workdir", "{workdir}"],
            ["init", "codex", "--workdir", "{workdir}", "--json"],
            "retry_install",
            "loopora init codex --workdir",
        ),
        (
            ["init", "codex", "--workdir", "{workdir}", "--check"],
            ["init", "codex", "--workdir", "{workdir}", "--check", "--json"],
            "retry_check",
            "loopora init codex --workdir",
        ),
        (
            ["agent", "codex", "check", "--workdir", "{workdir}"],
            ["agent", "codex", "check", "--workdir", "{workdir}", "--json"],
            "retry_check",
            "loopora init codex --workdir",
        ),
        (
            ["uninstall", "codex", "--workdir", "{workdir}"],
            ["uninstall", "codex", "--workdir", "{workdir}", "--json"],
            "retry_uninstall",
            "loopora uninstall codex --workdir",
        ),
    ],
)
def test_cli_adapter_entry_commands_explain_missing_workdir_before_mutation(
    tmp_path: Path,
    plain_template: list[str],
    json_template: list[str],
    retry_kind: str,
    retry_command_fragment: str,
) -> None:
    missing_workdir = tmp_path / "missing project"
    runner = CliRunner()

    plain_args = [str(missing_workdir) if value == "{workdir}" else value for value in plain_template]
    json_args = [str(missing_workdir) if value == "{workdir}" else value for value in json_template]
    plain = runner.invoke(cli.app, plain_args)
    json_result = runner.invoke(cli.app, json_args)

    assert plain.exit_code == 1
    assert not missing_workdir.exists()
    output_text = _plain_recovery_text(plain)
    assert "Invalid value for '--workdir'" not in output_text
    assert "Codex Loopora entry" in output_text
    assert "project directory state: missing" in output_text
    assert "note:" in output_text
    assert "summary:" not in output_text
    assert "Target project directory does not exist yet" in output_text
    assert f"mkdir -p {str(missing_workdir.resolve())!r}" in output_text
    assert "loopora doctor --workdir" in output_text
    assert retry_command_fragment in output_text
    assert "after readiness" not in output_text
    assert "Retry" in output_text
    assert "after the target exists" in output_text

    assert json_result.exit_code == 1
    assert not missing_workdir.exists()
    payload = json.loads(json_result.stdout)
    assert next(iter(payload)) == "adapter_workdir_recovery_summary"
    assert payload["loop_recovery"] == "adapter_workdir_unavailable"
    assert payload["status"] == "blocked_by_workdir"
    assert payload["adapter"] == "codex"
    assert payload["workdir"] == str(missing_workdir.resolve())
    assert payload["workdir_state"]["status"] == "missing"
    assert payload["workdir_state"]["usable_for_agent_entries"] is False
    assert payload["workdir_state"]["commands"]["create"] == f"mkdir -p {str(missing_workdir.resolve())!r}"
    action_kinds = [item["kind"] for item in payload["next_actions"]]
    assert payload["adapter_workdir_recovery_summary"]["next_action_kinds"] == action_kinds
    assert action_kinds == ["create_workdir", retry_kind, "confirm_readiness"]
    expected_ready_after = {retry_kind: "create_workdir", "confirm_readiness": retry_kind}
    assert payload["next_action_ready_now_kinds"] == ["create_workdir"]
    assert payload["next_action_ready_after_actions"] == expected_ready_after
    assert payload["adapter_workdir_recovery_summary"]["next_action_ready_now_kinds"] == ["create_workdir"]
    assert payload["adapter_workdir_recovery_summary"]["next_action_ready_after_actions"] == expected_ready_after
    _assert_loopora_cli_command(payload["next_actions"][1]["command"], retry_command_fragment)
    _assert_loopora_cli_command(payload["next_actions"][2]["command"], "loopora doctor --workdir")
    assert payload["next_actions"][1]["after_action"] == "create_workdir"
    assert payload["next_actions"][2]["after_action"] == retry_kind


def test_cli_adapter_entry_missing_workdir_preserves_current_cli_entry(monkeypatch, tmp_path: Path) -> None:
    missing_workdir = tmp_path / "missing project"
    monkeypatch.setenv("UV_RUN_RECURSION_DEPTH", "1")
    monkeypatch.setattr(agent_adapter_command_prefix, "current_loopora_cli_entry", lambda: "uv run loopora")
    source_entry = agent_adapter_command_prefix.current_project_file_loopora_cli_entry()

    plain = CliRunner().invoke(cli.app, ["init", "codex", "--workdir", str(missing_workdir)])

    assert plain.exit_code == 1
    output_text = _plain_recovery_text(plain)
    assert f"{source_entry} doctor --workdir" in output_text
    assert f"{source_entry} init codex --workdir" in output_text


def test_cli_adapter_entry_commands_reject_file_workdir_before_mutation(tmp_path: Path) -> None:
    workdir_file = tmp_path / "not-a-project"
    workdir_file.write_text("not a directory\n", encoding="utf-8")
    original = workdir_file.read_text(encoding="utf-8")
    runner = CliRunner()

    plain = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir_file)])
    json_result = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir_file), "--json"])

    assert plain.exit_code == 1
    assert workdir_file.read_text(encoding="utf-8") == original
    output_text = _plain_recovery_text(plain)
    assert "Invalid value for '--workdir'" not in output_text
    assert "project directory state: not_directory" in output_text
    assert "Target project path exists but is not a directory" in output_text
    assert "Choose an existing project directory" in output_text
    assert "mkdir -p" not in output_text

    assert json_result.exit_code == 1
    assert workdir_file.read_text(encoding="utf-8") == original
    payload = json.loads(json_result.stdout)
    assert payload["loop_recovery"] == "adapter_workdir_unavailable"
    assert payload["status"] == "blocked_by_workdir"
    assert payload["workdir"] == str(workdir_file.resolve())
    assert payload["workdir_state"]["status"] == "not_directory"
    assert payload["workdir_state"]["usable_for_agent_entries"] is False
    assert payload["workdir_state"]["commands"] == {}
    action_kinds = [item["kind"] for item in payload["next_actions"]]
    assert payload["adapter_workdir_recovery_summary"]["next_action_kinds"] == action_kinds == ["choose_workdir", "retry_install", "confirm_readiness"]
    expected_ready_after = {"retry_install": "choose_workdir", "confirm_readiness": "retry_install"}
    assert payload["next_action_ready_now_kinds"] == ["choose_workdir"]
    assert payload["next_action_ready_after_actions"] == expected_ready_after
    assert payload["adapter_workdir_recovery_summary"]["next_action_ready_after_actions"] == expected_ready_after
    assert "command" not in payload["next_actions"][1]
    assert "command" not in payload["next_actions"][2]
    assert payload["next_actions"][1]["after_action"] == "choose_workdir"
    assert payload["next_actions"][2]["after_action"] == "retry_install"


@pytest.mark.parametrize(
    "case",
    [
        {
            "plain": ["agent", "codex", "plan", "--workdir", "{workdir}", "--message", "Ship the audit review"],
            "json": ["agent", "codex", "plan", "--workdir", "{workdir}", "--message", "Ship the audit review", "--json"],
            "action": "plan",
            "retry_kind": "retry_plan",
            "retry_fragment": "loopora agent codex plan --workdir",
        },
        {
            "plain": ["agent", "codex", "run", "--workdir", "{workdir}", "--no-web"],
            "json": ["agent", "codex", "run", "--workdir", "{workdir}", "--no-web", "--json"],
            "action": "run",
            "retry_kind": "retry_run",
            "retry_fragment": "loopora agent codex run --workdir",
        },
        {
            "plain": ["agent", "codex", "next", "--workdir", "{workdir}", "--no-web"],
            "json": ["agent", "codex", "next", "--workdir", "{workdir}", "--no-web", "--json"],
            "action": "next",
            "retry_kind": "retry_next",
            "retry_fragment": "loopora agent codex next --workdir",
        },
        {
            "plain": ["agent", "codex", "submit", "--result-file", "{result_file}", "--workdir", "{workdir}", "--no-web"],
            "json": [
                "agent",
                "codex",
                "submit",
                "--result-file",
                "{result_file}",
                "--workdir",
                "{workdir}",
                "--no-web",
                "--json",
            ],
            "action": "submit",
            "retry_kind": "retry_submit",
            "retry_fragment": "loopora agent codex submit",
        },
    ],
)
def test_cli_agent_runtime_commands_explain_missing_workdir_before_service(
    tmp_path: Path,
    monkeypatch,
    case: dict,
) -> None:
    missing_workdir = tmp_path / "missing project"
    result_file = tmp_path / "result.json"
    runner = CliRunner()

    def fail_if_service_starts():
        raise AssertionError("missing runtime workdir recovery must not initialize Loopora service")

    monkeypatch.setattr(cli, "create_service", fail_if_service_starts)
    plain_args = [
        str(missing_workdir) if value == "{workdir}" else str(result_file) if value == "{result_file}" else value
        for value in case["plain"]
    ]
    json_args = [
        str(missing_workdir) if value == "{workdir}" else str(result_file) if value == "{result_file}" else value
        for value in case["json"]
    ]

    plain = runner.invoke(cli.app, plain_args)
    json_result = runner.invoke(cli.app, json_args)

    assert plain.exit_code == 1
    assert not missing_workdir.exists()
    output_text = _plain_recovery_text(plain)
    assert "Invalid value for '--workdir'" not in output_text
    assert "Codex Loopora Agent" in output_text
    assert f"{case['action']} is blocked" in output_text
    assert "project directory state: missing" in output_text
    assert f"mkdir -p {shlex.quote(str(missing_workdir.resolve()))}" in output_text
    assert "loopora doctor --workdir" in output_text
    assert case["retry_fragment"] in output_text

    assert json_result.exit_code == 1
    assert not missing_workdir.exists()
    payload = json.loads(json_result.stdout)
    summary, legacy = assert_agent_v3_envelope(
        payload,
        kind="agent_recovery",
        summary_key="agent_workdir_recovery_summary",
        status="blocked",
    )
    assert summary["loop_recovery"] == "adapter_workdir_unavailable"
    assert summary["status"] == "blocked_by_workdir"
    assert summary["adapter"] == "codex"
    assert summary["action"] == case["action"]
    assert summary["workdir"] == str(missing_workdir.resolve())
    assert summary["workdir_state"]["status"] == "missing"
    assert summary["workdir_state"]["usable_for_agent_runtime"] is False
    assert summary["workdir_state"]["commands"]["create"] == f"mkdir -p {shlex.quote(str(missing_workdir.resolve()))}"
    assert summary["next_action_kinds"] == [item["kind"] for item in summary["next_actions"]] == ["create_workdir", "confirm_readiness", case["retry_kind"]]
    assert summary["next_action_ready_now_kinds"] == ["create_workdir"]
    assert summary["next_action_ready_after_actions"] == {"confirm_readiness": "create_workdir", case["retry_kind"]: "confirm_readiness"}
    _assert_loopora_cli_command(summary["next_actions"][1]["command"], "loopora doctor --workdir")
    _assert_loopora_cli_command(summary["next_actions"][2]["command"], case["retry_fragment"])
    assert legacy["loop_recovery"] == "adapter_workdir_unavailable"


def test_cli_agent_runtime_commands_reject_file_workdir_before_service(tmp_path: Path, monkeypatch) -> None:
    workdir_file = tmp_path / "not-a-project"
    workdir_file.write_text("not a directory\n", encoding="utf-8")
    original = workdir_file.read_text(encoding="utf-8")
    runner = CliRunner()

    def fail_if_service_starts():
        raise AssertionError("file runtime workdir recovery must not initialize Loopora service")

    monkeypatch.setattr(cli, "create_service", fail_if_service_starts)

    plain = runner.invoke(cli.app, ["agent", "codex", "plan", "--workdir", str(workdir_file), "--message", "Ship it"])
    json_result = runner.invoke(
        cli.app,
        ["agent", "codex", "plan", "--workdir", str(workdir_file), "--message", "Ship it", "--json"],
    )

    assert plain.exit_code == 1
    assert workdir_file.read_text(encoding="utf-8") == original
    output_text = _plain_recovery_text(plain)
    assert "Invalid value for '--workdir'" not in output_text
    assert "project directory state: not_directory" in output_text
    assert "Target project path exists but is not a directory" in output_text
    assert "Choose an existing project directory" in output_text

    assert json_result.exit_code == 1
    assert workdir_file.read_text(encoding="utf-8") == original
    payload = json.loads(json_result.stdout)
    summary, _legacy = assert_agent_v3_envelope(
        payload,
        kind="agent_recovery",
        summary_key="agent_workdir_recovery_summary",
        status="blocked",
    )
    assert summary["loop_recovery"] == "adapter_workdir_unavailable"
    assert summary["status"] == "blocked_by_workdir"
    assert summary["workdir_state"]["status"] == "not_directory"
    assert summary["workdir_state"]["usable_for_agent_runtime"] is False
    assert summary["workdir_state"]["commands"] == {}
    assert summary["next_action_kinds"] == [item["kind"] for item in summary["next_actions"]] == ["choose_workdir", "confirm_readiness", "retry_plan"]
    assert summary["next_action_ready_now_kinds"] == ["choose_workdir"]
    assert summary["next_action_ready_after_actions"] == {"confirm_readiness": "choose_workdir", "retry_plan": "confirm_readiness"}
    assert "command" not in summary["next_actions"][1]
    assert "command" not in summary["next_actions"][2]


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
    output_text = _plain_recovery_text(result)
    assert "loop_recovery: run /loopora-plan before /loopora-run can start" in output_text
    assert "ready Loop preview" in output_text
    assert "required_inputs:" in output_text
    assert "- Loopora fit reason (loopora_fit_reason)" in output_text
    assert "- Task goal (task_goal)" in output_text
    assert "- Fake-done risks (fake_done_risks)" in output_text
    assert "- Required evidence (required_evidence)" in output_text
    assert "- Judgment tradeoffs (judgment_tradeoffs)" in output_text
    assert "ask_user: What long-running task should Loopora govern?" in output_text
    assert "question_action: Use the host's official user-question or follow-up capability" in output_text
    assert "Loopora fit: ..." in output_text
    assert "example_user_reply:" in output_text
    assert "Fake-done risks: ..." in output_text
    assert "Required evidence: ..." in output_text
    assert "Judgment tradeoffs: ..." in output_text
    assert "message_cli_command:" in output_text
    _assert_labeled_loopora_agent_command(output_text, "message_cli_command", "plan")
    assert "agent_surface: current host Agent remains the executor" in output_text
    assert "task_message_template:" not in output_text
    assert "first_task_message_example:" not in output_text
    assert "debug_cli_example_command:" not in output_text
    assert "READY Loopora bundle" not in output_text


def test_cli_claude_loop_requires_ready_bundle(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()

    result = runner.invoke(cli.app, ["agent", "claude", "run", "--workdir", str(workdir), "--no-web"])

    assert result.exit_code == 1
    output_text = _plain_recovery_text(result)
    assert "loop_recovery: run /loopora-plan before /loopora-run can start" in output_text
    assert "ready Loop preview" in output_text
    assert "READY Loopora bundle" not in output_text


def test_cli_opencode_loop_requires_ready_bundle(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()

    result = runner.invoke(cli.app, ["agent", "opencode", "run", "--workdir", str(workdir), "--no-web"])

    assert result.exit_code == 1
    output_text = _plain_recovery_text(result)
    assert "loop_recovery: run /loopora-plan before /loopora-run can start" in output_text
    assert "ready Loop preview" in output_text
    assert "READY Loopora bundle" not in output_text
