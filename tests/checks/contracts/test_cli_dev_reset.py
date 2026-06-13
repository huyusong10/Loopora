from __future__ import annotations

import json
from pathlib import Path
import re

from typer.testing import CliRunner

from loopora import cli
from loopora.agent_adapter_templates import managed_templates
from loopora.branding import APP_HOME_ENV
from loopora.cli_dev_commands import DEV_RESET_SUMMARY_SCHEMA_VERSION
from loopora.dev_check import DEFAULT_FAST_COMMANDS, DEV_CHECK_SCHEMA_VERSION, DevCheckCommandResult, run_dev_check


def _result_error_text(result) -> str:
    try:
        return result.stderr
    except ValueError:
        return result.output


def test_cli_dev_check_lists_default_fast_gate_without_running(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(cli.app, ["dev", "check", "--workdir", str(tmp_path), "--list", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    summary = payload["dev_check_summary"]
    assert summary["schema_version"] == DEV_CHECK_SCHEMA_VERSION
    assert summary["profile"] == "default-fast"
    assert summary["status"] == "listed"
    assert summary["ready"] is True
    assert summary["workdir"] == str(tmp_path.resolve())
    assert [step["id"] for step in payload["steps"]] == [step[0] for step in DEFAULT_FAST_COMMANDS]
    assert [step["command"] for step in payload["steps"]] == [step[2] for step in DEFAULT_FAST_COMMANDS]
    assert all(step["status"] == "listed" for step in payload["steps"])

    plain = runner.invoke(cli.app, ["dev", "check", "--workdir", str(tmp_path), "--list"])
    assert plain.exit_code == 0, plain.stdout
    assert "Loopora dev check: default-fast" in plain.stdout
    assert "uv run pytest -q tests/checks/contracts" in plain.stdout
    assert "next: rerun without --list" in plain.stdout


def test_dev_check_stops_after_first_failed_step_and_reports_command(tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_runner(command: tuple[str, ...], _cwd: Path) -> DevCheckCommandResult:
        calls.append(command)
        if command == ("uv", "pip", "check"):
            return DevCheckCommandResult(returncode=7, stdout="dependency conflict\n", stderr="broken lock\n")
        return DevCheckCommandResult(returncode=0, stdout="ok\n")

    result = run_dev_check(workdir=tmp_path, command_runner=fake_runner)
    steps = {step["id"]: step for step in result["steps"]}

    assert result["status"] == "fail"
    assert result["ready"] is False
    assert result["dev_check_summary"]["failed_step_id"] == "dependency_compatibility"
    assert steps["dependency_sync"]["status"] == "pass"
    assert steps["dependency_compatibility"]["status"] == "fail"
    assert steps["dependency_compatibility"]["returncode"] == 7
    assert "broken lock" in steps["dependency_compatibility"]["stderr"]
    assert steps["static_js_syntax"]["status"] == "skipped"
    assert calls == [("uv", "sync", "--locked", "--dry-run"), ("uv", "pip", "check")]


def test_dev_check_package_build_cleans_generated_package_metadata(tmp_path: Path) -> None:
    stale_metadata = tmp_path / "src" / "loopora.egg-info" / "PKG-INFO"
    stale_metadata.parent.mkdir(parents=True)
    stale_metadata.write_text("stale\n", encoding="utf-8")

    def fake_runner(command: tuple[str, ...], cwd: Path) -> DevCheckCommandResult:
        if command == ("uv", "build", "--out-dir", "tmp/package-check"):
            assert not (cwd / "src" / "loopora.egg-info").exists()
            generated_metadata = cwd / "src" / "loopora.egg-info" / "PKG-INFO"
            generated_metadata.parent.mkdir(parents=True)
            generated_metadata.write_text("generated\n", encoding="utf-8")
        return DevCheckCommandResult(returncode=0, stdout="ok\n")

    result = run_dev_check(workdir=tmp_path, command_runner=fake_runner)

    assert result["status"] == "pass"
    assert (tmp_path / "tmp" / "package-check").exists()
    assert not (tmp_path / "src" / "loopora.egg-info").exists()


def test_cli_dev_help_surfaces_check_as_default_contributor_gate() -> None:
    runner = CliRunner()

    root_help = runner.invoke(cli.app, ["--help"])
    dev_help = runner.invoke(cli.app, ["dev", "--help"])
    check_help = runner.invoke(cli.app, ["dev", "check", "--help"])
    normalized_check_help = re.sub(r"\s+", " ", check_help.stdout)

    assert root_help.exit_code == 0, root_help.stdout
    assert "run local checks" in root_help.stdout
    assert dev_help.exit_code == 0, dev_help.stdout
    assert "check" in dev_help.stdout
    assert "Run the local default-fast verification gate" in dev_help.stdout
    assert check_help.exit_code == 0, check_help.stdout
    assert "Verification profile to run" in check_help.stdout
    assert "--list" in normalized_check_help
    assert "verification steps" in normalized_check_help
    assert "commands" in normalized_check_help


def test_cli_dev_reset_previews_then_removes_v3_development_state_without_deleting_unmanaged_files(tmp_path: Path) -> None:
    runner = CliRunner()
    workdir = tmp_path / "project"
    home = tmp_path / "home"
    workdir.mkdir()
    home.mkdir()
    db = home / "app.db"
    db.write_text("legacy-db", encoding="utf-8")
    state_sentinel = workdir / ".loopora" / "runs" / "run_old" / "state.json"
    state_sentinel.parent.mkdir(parents=True)
    state_sentinel.write_text("{}", encoding="utf-8")
    templates = managed_templates("codex")
    managed_relative = ".codex/agents/loopora-builder.toml"
    managed_file = workdir / managed_relative
    managed_file.parent.mkdir(parents=True)
    managed_file.write_text(templates[managed_relative], encoding="utf-8")
    unmanaged_relative = ".agents/skills/loopora-plan/SKILL.md"
    unmanaged_file = workdir / unmanaged_relative
    unmanaged_file.parent.mkdir(parents=True)
    unmanaged_file.write_text("# user-owned file\n", encoding="utf-8")

    preview = runner.invoke(
        cli.app,
        ["dev", "reset", "--workdir", str(workdir), "--json"],
        env={APP_HOME_ENV: str(home)},
    )

    assert preview.exit_code == 0, _result_error_text(preview)
    preview_payload = json.loads(preview.stdout)
    planned = set(preview_payload["planned"])
    skipped = set(preview_payload["skipped"])
    assert preview_payload["dev_reset_summary"]["schema_version"] == DEV_RESET_SUMMARY_SCHEMA_VERSION
    assert preview_payload["dev_reset_summary"]["dry_run"] is True
    assert str(db) in planned
    assert str(workdir / ".loopora") in planned
    assert str(managed_file) in planned
    assert str(unmanaged_file) in skipped
    assert db.exists()
    assert (workdir / ".loopora").exists()
    assert managed_file.exists()
    assert unmanaged_file.exists()

    result = runner.invoke(
        cli.app,
        ["dev", "reset", "--workdir", str(workdir), "--yes", "--json"],
        env={APP_HOME_ENV: str(home)},
    )

    assert result.exit_code == 0, _result_error_text(result)
    payload = json.loads(result.stdout)
    removed = set(payload["removed"])
    skipped = set(payload["skipped"])
    assert payload["dev_reset_summary"]["schema_version"] == DEV_RESET_SUMMARY_SCHEMA_VERSION
    assert payload["dev_reset_summary"]["dry_run"] is False
    assert str(db) in removed
    assert str(workdir / ".loopora") in removed
    assert str(managed_file) in removed
    assert str(unmanaged_file) in skipped
    assert not db.exists()
    assert not (workdir / ".loopora").exists()
    assert not managed_file.exists()
    assert unmanaged_file.exists()
