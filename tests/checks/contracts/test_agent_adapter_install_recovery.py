from __future__ import annotations

from agent_adapter_test_support import (
    CliRunner,
    Path,
    _assert_labeled_loopora_agent_command,
    _assert_loopora_cli_command,
    _error_text,
    cli,
    json,
)


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
