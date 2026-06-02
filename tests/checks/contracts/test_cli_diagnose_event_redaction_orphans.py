from __future__ import annotations

import json
from pathlib import Path

from loopora import cli

from cli_diagnose_redaction_test_support import (
    install_cli_service,
    redaction_repository,
    registered_orphan_layout,
    write_unsafe_timeline_event,
)


def test_cli_diagnose_event_redaction_scans_registered_orphan_run_dirs(monkeypatch, tmp_path: Path) -> None:
    marker = "UNSAFE-ORPHAN-TIMELINE-MARKER"
    repository = redaction_repository(tmp_path)
    layout = registered_orphan_layout(repository, tmp_path, run_id="run_orphan")
    write_unsafe_timeline_event(layout, run_id="run_orphan", marker=marker)
    runner = install_cli_service(monkeypatch, repository)

    dry_run = runner.invoke(cli.app, ["diagnose", "event-redaction"])
    assert dry_run.exit_code == 0, dry_run.stdout
    assert json.loads(dry_run.stdout)["suspect"] == 1
    assert marker in layout.timeline_events_path.read_text(encoding="utf-8")

    fix_run = runner.invoke(cli.app, ["diagnose", "event-redaction", "--fix"])
    assert fix_run.exit_code == 0, fix_run.stdout
    assert json.loads(fix_run.stdout)["fixed"] == 1
    timeline_text = layout.timeline_events_path.read_text(encoding="utf-8")
    assert marker not in timeline_text
    assert "uv run pytest -q" in timeline_text


def test_cli_diagnose_event_redaction_reports_unreadable_timeline_files(monkeypatch, tmp_path: Path) -> None:
    repository = redaction_repository(tmp_path)
    layout = registered_orphan_layout(repository, tmp_path, run_id="run_unreadable")
    layout.timeline_events_path.write_bytes(b"\xff")
    runner = install_cli_service(monkeypatch, repository)

    dry_run = runner.invoke(cli.app, ["diagnose", "event-redaction"])
    assert dry_run.exit_code == 0, dry_run.stdout
    dry_report = json.loads(dry_run.stdout)
    assert dry_report["suspect"] == 0
    assert dry_report["fixed"] == 0
    assert dry_report["timeline_files"]["scanned_files"] == 1
    assert dry_report["timeline_files"]["scanned_events"] == 0
    assert any(
        item["source"] == "timeline"
        and item["reason"] == "read_failed"
        and item["error_type"] == "UnicodeDecodeError"
        for item in dry_report["unfixable"]
    )

    fix_run = runner.invoke(cli.app, ["diagnose", "event-redaction", "--fix"])
    assert fix_run.exit_code == 0, fix_run.stdout
    fix_report = json.loads(fix_run.stdout)
    assert fix_report["fixed"] == 0
    assert any(item["reason"] == "read_failed" for item in fix_report["unfixable"])
    assert layout.timeline_events_path.read_bytes() == b"\xff"
