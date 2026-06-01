from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from loopora import cli
from loopora.db import LooporaRepository
from loopora.executor import FakeCodexExecutor
from loopora.run_artifacts import RunArtifactLayout
from loopora.service import LooporaService
from loopora.settings import AppSettings
from loopora.utils import utc_now


def test_event_redaction_audit_has_db_file_and_result_boundaries() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    audit_source = (repo_root / "src/loopora/event_redaction_audit.py").read_text(encoding="utf-8")
    db_source = (repo_root / "src/loopora/event_redaction_audit_db.py").read_text(encoding="utf-8")
    files_source = (repo_root / "src/loopora/event_redaction_audit_files.py").read_text(encoding="utf-8")
    results_source = (repo_root / "src/loopora/event_redaction_audit_results.py").read_text(encoding="utf-8")
    design_source = (repo_root / "design/contracts.md").read_text(encoding="utf-8")

    assert "from loopora.event_redaction_audit_db import" in audit_source
    assert "from loopora.event_redaction_audit_files import" in audit_source
    assert "from loopora.event_redaction_audit_results import combine_event_redaction_reports" in audit_source
    assert "def audit_db_events" in db_source
    assert "def audit_alignment_db_events" in db_source
    assert "def audit_timeline_files" in files_source
    assert "def audit_alignment_event_files" in files_source
    assert "def combine_event_redaction_reports" in results_source
    assert "state_dir_for_workdir" not in audit_source
    assert "event_redaction_audit_files.py" in design_source


def test_cli_diagnose_event_redaction_dry_run_and_fix(monkeypatch, tmp_path: Path) -> None:
    marker = "UNIQUE-CLI-REDACTION-MARKER"
    alignment_marker = "UNIQUE-ALIGNMENT-REDACTION-MARKER"
    repository = LooporaRepository(tmp_path / "app.db")
    service = LooporaService(
        repository=repository,
        settings=AppSettings(max_concurrent_runs=1, polling_interval_seconds=0.05, stop_grace_period_seconds=0.2),
        executor_factory=lambda: FakeCodexExecutor(scenario="success"),
    )
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nKeep sensitive data out of historical events.\n", encoding="utf-8")
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    loop = service.create_loop(
        name="Redaction Audit Loop",
        spec_path=spec_path,
        workdir=workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=1,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.start_run(loop["id"])
    unsafe_event = {
        "id": 999,
        "run_id": run["id"],
        "created_at": utc_now(),
        "event_type": "codex_event",
        "role": "generator",
        "payload": {
            "type": "command",
            "message": "uv run pytest -q",
            "prompt": marker,
            "json_schema": {"marker": marker},
        },
    }
    with repository.transaction() as connection:
        connection.execute(
            """
            INSERT INTO run_events (run_id, created_at, event_type, role, payload_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                run["id"],
                unsafe_event["created_at"],
                unsafe_event["event_type"],
                unsafe_event["role"],
                json.dumps(unsafe_event["payload"], ensure_ascii=False),
            ),
        )
    layout = RunArtifactLayout(Path(run["runs_dir"]))
    layout.timeline_events_path.write_text(json.dumps(unsafe_event, ensure_ascii=False) + "\n", encoding="utf-8")
    alignment = service.create_alignment_session(
        workdir=workdir,
        message="Create an alignment event redaction audit fixture.",
        start_immediately=False,
    )
    unsafe_alignment_event = {
        "id": 1000,
        "session_id": alignment["id"],
        "created_at": utc_now(),
        "event_type": "codex_event",
        "payload": {
            "type": "command",
            "message": f"codex exec --token {alignment_marker}",
            "prompt": alignment_marker,
            "json_schema": {"marker": alignment_marker},
        },
    }
    with repository.transaction() as connection:
        connection.execute(
            """
            INSERT INTO alignment_events (session_id, created_at, event_type, payload_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                alignment["id"],
                unsafe_alignment_event["created_at"],
                unsafe_alignment_event["event_type"],
                json.dumps(unsafe_alignment_event["payload"], ensure_ascii=False),
            ),
        )
    alignment_events_path = Path(alignment["artifact_dir"]) / "events" / "events.jsonl"
    with alignment_events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(unsafe_alignment_event, ensure_ascii=False) + "\n")

    class FakeService:
        def __init__(self, repository):
            self.repository = repository

    monkeypatch.setattr(cli, "create_service", lambda: FakeService(repository))
    runner = CliRunner()

    dry_run = runner.invoke(cli.app, ["diagnose", "event-redaction"])
    assert dry_run.exit_code == 0, dry_run.stdout
    dry_report = json.loads(dry_run.stdout)
    assert dry_report["mode"] == "dry-run"
    assert dry_report["suspect"] >= 2
    assert dry_report["alignment_db_events"]["suspect"] >= 1
    assert dry_report["alignment_event_files"]["suspect"] >= 1
    assert marker in layout.timeline_events_path.read_text(encoding="utf-8")
    assert alignment_marker in alignment_events_path.read_text(encoding="utf-8")

    fix_run = runner.invoke(cli.app, ["diagnose", "event-redaction", "--fix"])
    assert fix_run.exit_code == 0, fix_run.stdout
    fix_report = json.loads(fix_run.stdout)
    assert fix_report["mode"] == "fix"
    assert fix_report["fixed"] >= 4
    assert marker not in layout.timeline_events_path.read_text(encoding="utf-8")
    assert "uv run pytest -q" in layout.timeline_events_path.read_text(encoding="utf-8")
    fixed_payload = repository.list_events(run["id"], after_id=0, limit=20)[-1]["payload"]
    assert marker not in json.dumps(fixed_payload, ensure_ascii=False)
    assert fixed_payload["message"] == "uv run pytest -q"
    assert alignment_marker not in alignment_events_path.read_text(encoding="utf-8")
    fixed_alignment_payload = service.list_alignment_events(alignment["id"])[-1]["payload"]
    assert alignment_marker not in json.dumps(fixed_alignment_payload, ensure_ascii=False)
    assert fixed_alignment_payload["message"] == "codex exec --token <secret omitted>"


def test_cli_diagnose_event_redaction_scans_registered_orphan_run_dirs(monkeypatch, tmp_path: Path) -> None:
    marker = "UNSAFE-ORPHAN-TIMELINE-MARKER"
    repository = LooporaRepository(tmp_path / "app.db")
    run_dir = tmp_path / ".loopora" / "runs" / "run_orphan"
    layout = RunArtifactLayout(run_dir)
    layout.timeline_dir.mkdir(parents=True)
    unsafe_event = {
        "id": 1,
        "run_id": "run_orphan",
        "created_at": utc_now(),
        "event_type": "codex_event",
        "role": "generator",
        "payload": {
            "type": "command",
            "message": "uv run pytest -q",
            "prompt": marker,
            "json_schema": {"marker": marker},
        },
    }
    layout.timeline_events_path.write_text(json.dumps(unsafe_event, ensure_ascii=False) + "\n", encoding="utf-8")
    repository.upsert_local_asset_root(
        resource_type="run",
        resource_id="run_orphan",
        path=run_dir,
        workdir=str(tmp_path),
        owner_id="loop_missing",
        state="orphaned",
    )

    class FakeService:
        def __init__(self, repository):
            self.repository = repository

    monkeypatch.setattr(cli, "create_service", lambda: FakeService(repository))
    runner = CliRunner()

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
    repository = LooporaRepository(tmp_path / "app.db")
    run_dir = tmp_path / ".loopora" / "runs" / "run_unreadable"
    layout = RunArtifactLayout(run_dir)
    layout.timeline_dir.mkdir(parents=True)
    layout.timeline_events_path.write_bytes(b"\xff")
    repository.upsert_local_asset_root(
        resource_type="run",
        resource_id="run_unreadable",
        path=run_dir,
        workdir=str(tmp_path),
        owner_id="loop_missing",
        state="orphaned",
    )

    class FakeService:
        def __init__(self, repository):
            self.repository = repository

    monkeypatch.setattr(cli, "create_service", lambda: FakeService(repository))
    runner = CliRunner()

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
