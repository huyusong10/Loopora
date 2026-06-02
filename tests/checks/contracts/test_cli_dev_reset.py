from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from loopora import cli
from loopora.agent_adapter_templates import managed_templates
from loopora.branding import APP_HOME_ENV
from loopora.cli_dev_commands import DEV_RESET_SUMMARY_SCHEMA_VERSION


def _result_error_text(result) -> str:
    try:
        return result.stderr
    except ValueError:
        return result.output


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
