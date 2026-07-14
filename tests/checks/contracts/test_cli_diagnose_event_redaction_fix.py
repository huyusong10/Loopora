from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from loopora import cli
from loopora.branding import APP_HOME_ENV

from cli_diagnose_redaction_test_support import (
    create_redaction_run_fixture,
    insert_unsafe_alignment_event,
    insert_unsafe_run_event,
    install_cli_service,
)


MIN_ALIGNMENT_EVENT_FILE_SUSPECT_COUNT = 1
MIN_ALIGNMENT_EVENT_SUSPECT_COUNT = 1
MIN_DRY_RUN_SUSPECT_COUNT = 2
MIN_FIXED_REDACTION_COUNT = 4


def test_cli_diagnose_event_redaction_reports_development_reset_without_traceback(monkeypatch, tmp_path: Path) -> None:
    app_home = tmp_path / "home"
    app_home.mkdir()
    _create_legacy_app_db(app_home / "app.db")
    monkeypatch.setenv(APP_HOME_ENV, str(app_home))

    result = CliRunner().invoke(cli.app, ["diagnose", "event-redaction"])

    assert result.exit_code == 1
    assert result.stderr == ""
    assert "Traceback" not in result.output
    payload = json.loads(result.stdout)
    assert payload["loop_recovery"] == "development_reset_required"
    assert "loopora dev reset --scope app --workdir" in payload["reset_command"]
    assert "<project>" not in payload["reset_command"]
    assert payload["preview_is_destructive"] is False
    assert payload["destructive_apply_requires_yes"] is True
    assert "local App database files" in payload["scope_description"]
    assert "managed Agent entries are left alone" in payload["scope_description"]


def test_cli_diagnose_event_redaction_dry_run_and_fix(monkeypatch, tmp_path: Path) -> None:
    marker = "UNIQUE-CLI-REDACTION-MARKER"
    alignment_marker = "UNIQUE-ALIGNMENT-REDACTION-MARKER"
    repository, service, run, workdir = create_redaction_run_fixture(tmp_path)
    layout = insert_unsafe_run_event(repository, run, marker)
    alignment, alignment_events_path = insert_unsafe_alignment_event(service, repository, workdir, alignment_marker)
    runner = install_cli_service(monkeypatch, repository)

    dry_run = runner.invoke(cli.app, ["diagnose", "event-redaction"])
    assert dry_run.exit_code == 0, dry_run.stdout
    dry_report = json.loads(dry_run.stdout)
    assert dry_report["mode"] == "dry-run"
    assert dry_report["suspect"] >= MIN_DRY_RUN_SUSPECT_COUNT
    assert dry_report["alignment_db_events"]["suspect"] >= MIN_ALIGNMENT_EVENT_SUSPECT_COUNT
    assert dry_report["alignment_event_files"]["suspect"] >= MIN_ALIGNMENT_EVENT_FILE_SUSPECT_COUNT
    assert marker in layout.timeline_events_path.read_text(encoding="utf-8")
    assert alignment_marker in alignment_events_path.read_text(encoding="utf-8")

    fix_run = runner.invoke(cli.app, ["diagnose", "event-redaction", "--fix"])
    assert fix_run.exit_code == 0, fix_run.stdout
    fix_report = json.loads(fix_run.stdout)
    assert fix_report["mode"] == "fix"
    assert fix_report["fixed"] >= MIN_FIXED_REDACTION_COUNT
    assert marker not in layout.timeline_events_path.read_text(encoding="utf-8")
    assert "uv run pytest -q" in layout.timeline_events_path.read_text(encoding="utf-8")
    fixed_payload = repository.list_events(run["id"], after_id=0, limit=20)[-1]["payload"]
    assert marker not in json.dumps(fixed_payload, ensure_ascii=False)
    assert fixed_payload["message"] == "uv run pytest -q"
    assert alignment_marker not in alignment_events_path.read_text(encoding="utf-8")
    fixed_alignment_payload = service.list_alignment_events(alignment["id"])[-1]["payload"]
    assert alignment_marker not in json.dumps(fixed_alignment_payload, ensure_ascii=False)
    assert fixed_alignment_payload["message"] == "codex exec --token <secret omitted>"


def _create_legacy_app_db(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE loop_definitions (id TEXT PRIMARY KEY, name TEXT NOT NULL)")
        connection.execute("PRAGMA user_version = 1")
