from __future__ import annotations

from agent_adapter_test_support import (
    CliRunner,
    LooporaConflictError,
    Path,
    assert_agent_check_payload,
    cli,
    json,
    pytest,
)

WEB_CREATION_PATH_TERMS = (
    "open Fit Guide/Web choices in Web",
    "Fit Guide first, then creation choices: Web conversation outside an Agent session",
    "Plan File import",
    "manual expert paths",
    "review evidence, gaps, and verdicts:",
)


def test_codex_adapter_status_reports_needs_update_for_managed_drift(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    workdir.mkdir()

    service.install_agent_adapter("codex", workdir=workdir)
    skill_path = workdir / ".agents" / "skills" / "loopora-plan" / "SKILL.md"
    skill_path.write_text(skill_path.read_text(encoding="utf-8") + "\n<!-- locally stale managed file -->\n", encoding="utf-8")

    status = service.get_agent_adapter("codex", workdir=workdir)

    assert status["status"] == "needs_update"
    assert any(
        item["path"].endswith("loopora-plan/SKILL.md") and item["state"] == "needs_update"
        for item in status["managed_files"]
    )


def test_cli_adapter_check_drift_recovery_returns_to_readiness_path(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()

    install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--json"])
    skill_path = workdir / ".agents" / "skills" / "loopora-plan" / "SKILL.md"
    skill_path.write_text(skill_path.read_text(encoding="utf-8") + "\n<!-- locally stale managed file -->\n", encoding="utf-8")
    plain = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--check"])
    structured = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--check", "--json"])

    assert install.exit_code == 0, install.stdout
    assert plain.exit_code == 1
    assert "install state: needs update" in plain.stdout
    assert "install_state:" not in plain.stdout
    assert "note:" in plain.stdout
    assert "summary:" not in plain.stdout
    assert "Inspect failed checks before reinstalling" in plain.stdout
    assert "Run:" in plain.stdout
    assert f"loopora init codex --workdir {workdir.resolve()}" in plain.stdout
    assert "Then verify:" in plain.stdout
    assert f"loopora init codex --workdir {workdir.resolve()} --check" in plain.stdout
    assert "Then confirm readiness:" in plain.stdout
    assert f"loopora doctor --workdir {workdir.resolve()}" in plain.stdout
    assert all(
        fragment in plain.stdout
        for fragment in (
            "Return to the Agent with the Loopora fit reason",
            "task goal, fake-done risk",
            "required evidence, judgment tradeoffs, and optional direct-path context.",
        )
    )
    assert "If /loopora-plan or /loopora-run is not visible after install, refresh or restart the Agent." in plain.stdout
    assert "Run /loopora-plan to prepare the Loop preview." in plain.stdout
    assert "After readiness passes, choose one path:" in plain.stdout
    assert all(term in plain.stdout for term in WEB_CREATION_PATH_TERMS)
    assert "Plan-file/expert path:" in plain.stdout
    assert "Existing work path:" in plain.stdout
    assert "Review whether the READY Loop preview matches the task judgment." in plain.stdout
    assert "After the READY Loop preview matches the task judgment, run /loopora-run in the same Agent session." in plain.stdout
    assert plain.stdout.index("Then confirm readiness:") < plain.stdout.index("After readiness passes, choose one path:")
    assert plain.stdout.index("Same-Agent path: Run /loopora-plan") < plain.stdout.index("open Fit Guide/Web choices in Web")
    assert plain.stdout.index("open Fit Guide/Web choices in Web") < plain.stdout.index(
        "Review whether the READY Loop preview matches the task judgment."
    )

    assert structured.exit_code == 1
    summary, _legacy = assert_agent_check_payload(json.loads(structured.stdout), status="fail")
    recovery = summary["check_recovery"]
    assert recovery["state"] == "needs_update"
    assert recovery["details_are_expected"] is False
    assert [item["kind"] for item in recovery["next_action_items"]] == [
        "inspect_failed_checks",
        "install_agent_entry",
        "verify_agent_entry",
        "confirm_readiness",
        "return_to_agent",
        "confirm_agent_visibility",
        "run_loopora_plan",
        "review_ready_loop_preview",
        "run_loopora_run",
        "start_web",
    ]


def test_codex_adapter_status_reports_error_for_manifest_tracked_user_edit_without_marker(
    service_factory,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    workdir.mkdir()

    service.install_agent_adapter("codex", workdir=workdir)
    skill_path = workdir / ".agents" / "skills" / "loopora-plan" / "SKILL.md"
    skill_path.write_text("# User edited this file after install\n", encoding="utf-8")

    status = service.get_agent_adapter("codex", workdir=workdir)

    assert status["status"] == "error"
    assert "loopora-plan/SKILL.md" in status["error"]
    with pytest.raises(LooporaConflictError):
        service.install_agent_adapter("codex", workdir=workdir)
    assert skill_path.read_text(encoding="utf-8") == "# User edited this file after install\n"


def test_claude_adapter_status_reports_needs_update_for_managed_drift(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    workdir.mkdir()

    service.install_agent_adapter("claude", workdir=workdir)
    skill_path = workdir / ".claude" / "skills" / "loopora-plan" / "SKILL.md"
    skill_path.write_text(skill_path.read_text(encoding="utf-8") + "\n<!-- locally stale managed file -->\n", encoding="utf-8")

    status = service.get_agent_adapter("claude", workdir=workdir)

    assert status["status"] == "needs_update"
    assert any(
        item["path"].endswith("loopora-plan/SKILL.md") and item["state"] == "needs_update"
        for item in status["managed_files"]
    )


def test_claude_adapter_status_reports_needs_update_for_missing_managed_session_hook(
    service_factory,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    workdir.mkdir()

    service.install_agent_adapter("claude", workdir=workdir)
    settings_path = workdir / ".claude" / "settings.json"
    settings_path.write_text(json.dumps({"permissions": {"allow": []}}) + "\n", encoding="utf-8")

    status = service.get_agent_adapter("claude", workdir=workdir)

    assert status["status"] == "needs_update"
    assert any(
        item["path"] == ".claude/settings.json#hooks.SessionStart.loopora" and item["state"] == "missing"
        for item in status["managed_files"]
    )


def test_claude_adapter_status_redacts_unreadable_settings_details(service_factory, tmp_path: Path, monkeypatch) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    settings_path = workdir / ".claude" / "settings.json"
    local_path = tmp_path / "private" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text('{"hooks": {}}\n', encoding="utf-8")
    original_read_text = Path.read_text

    def fail_settings_read(path: Path, *args: object, **kwargs: object) -> str:
        if path == settings_path:
            raise OSError(f"permission denied: {local_path}")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_settings_read)

    status = service.get_agent_adapter("claude", workdir=workdir)
    encoded = json.dumps(status, ensure_ascii=False)
    host_config = next(
        item
        for item in status["managed_files"]
        if item["path"] == ".claude/settings.json#hooks.SessionStart.loopora"
    )

    assert host_config["state"] == "error"
    assert host_config["error"] == "Claude Code settings could not be read: .claude/settings.json"
    assert str(settings_path) not in encoded
    assert str(local_path) not in encoded
    assert "permission denied" not in encoded


def test_codex_adapter_status_redacts_unreadable_managed_file_details(
    service_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    workdir.mkdir()
    local_path = tmp_path / "private" / "SKILL.md"
    service.install_agent_adapter("codex", workdir=workdir)
    skill_path = workdir / ".agents" / "skills" / "loopora-plan" / "SKILL.md"
    original_read_text = Path.read_text

    def fail_managed_file_read(path: Path, *args: object, **kwargs: object) -> str:
        if path == skill_path:
            raise OSError(f"permission denied: {local_path}")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_managed_file_read)

    status = service.get_agent_adapter("codex", workdir=workdir)
    encoded = json.dumps(status, ensure_ascii=False)
    managed_file = next(
        item
        for item in status["managed_files"]
        if item["path"] == ".agents/skills/loopora-plan/SKILL.md"
    )

    assert status["status"] == "error"
    assert managed_file["state"] == "error"
    assert managed_file["error"] == "managed file could not be read"
    assert ".agents/skills/loopora-plan/SKILL.md" in status["error"]
    assert str(skill_path) not in encoded
    assert str(local_path) not in encoded
    assert "permission denied" not in encoded


def test_opencode_adapter_status_reports_needs_update_for_managed_drift(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    workdir.mkdir()

    service.install_agent_adapter("opencode", workdir=workdir)
    command_path = workdir / ".opencode" / "commands" / "loopora-plan.md"
    command_path.write_text(command_path.read_text(encoding="utf-8") + "\n<!-- locally stale managed file -->\n", encoding="utf-8")

    status = service.get_agent_adapter("opencode", workdir=workdir)

    assert status["status"] == "needs_update"
    assert any(
        item["path"].endswith("loopora-plan.md") and item["state"] == "needs_update"
        for item in status["managed_files"]
    )
