from __future__ import annotations

import json
from pathlib import Path

from loopora import cli

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
