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


UNSAFE_EVENT_TYPE = "codex_event"
UNSAFE_RUN_ROLE = "generator"
UNSAFE_RUN_MESSAGE = "uv run pytest -q"


class FakeService:
    def __init__(self, repository):
        self.repository = repository


def redaction_repository(tmp_path: Path) -> LooporaRepository:
    return LooporaRepository(tmp_path / "app.db")


def install_cli_service(monkeypatch, repository: LooporaRepository) -> CliRunner:
    monkeypatch.setattr(cli, "create_service", lambda: FakeService(repository))
    return CliRunner()


def create_redaction_run_fixture(tmp_path: Path):
    repository = redaction_repository(tmp_path)
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
    return repository, service, service.start_run(loop["id"]), workdir


def insert_unsafe_run_event(repository: LooporaRepository, run: dict, marker: str) -> RunArtifactLayout:
    unsafe_event = _unsafe_run_event(run["id"], marker, event_id=999)
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
    layout.timeline_events_path.write_text(_event_jsonl_line(unsafe_event), encoding="utf-8")
    return layout


def insert_unsafe_alignment_event(service, repository: LooporaRepository, workdir: Path, marker: str):
    alignment = service.create_alignment_session(
        workdir=workdir,
        message="Create an alignment event redaction audit fixture.",
        start_immediately=False,
    )
    unsafe_event = {
        "id": 1000,
        "session_id": alignment["id"],
        "created_at": utc_now(),
        "event_type": UNSAFE_EVENT_TYPE,
        "payload": _unsafe_payload(marker, message=f"codex exec --token {marker}"),
    }
    with repository.transaction() as connection:
        connection.execute(
            """
            INSERT INTO alignment_events (session_id, created_at, event_type, payload_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                alignment["id"],
                unsafe_event["created_at"],
                unsafe_event["event_type"],
                json.dumps(unsafe_event["payload"], ensure_ascii=False),
            ),
        )
    alignment_events_path = Path(alignment["artifact_dir"]) / "events" / "events.jsonl"
    with alignment_events_path.open("a", encoding="utf-8") as handle:
        handle.write(_event_jsonl_line(unsafe_event))
    return alignment, alignment_events_path


def registered_orphan_layout(repository: LooporaRepository, tmp_path: Path, *, run_id: str) -> RunArtifactLayout:
    run_dir = tmp_path / ".loopora" / "runs" / run_id
    layout = RunArtifactLayout(run_dir)
    layout.timeline_dir.mkdir(parents=True)
    repository.upsert_local_asset_root(
        resource_type="run",
        resource_id=run_id,
        path=run_dir,
        workdir=str(tmp_path),
        owner_id="loop_missing",
        state="orphaned",
    )
    return layout


def write_unsafe_timeline_event(layout: RunArtifactLayout, *, run_id: str, marker: str) -> None:
    layout.timeline_events_path.write_text(_event_jsonl_line(_unsafe_run_event(run_id, marker, event_id=1)), encoding="utf-8")


def _unsafe_run_event(run_id: str, marker: str, *, event_id: int) -> dict:
    return {
        "id": event_id,
        "run_id": run_id,
        "created_at": utc_now(),
        "event_type": UNSAFE_EVENT_TYPE,
        "role": UNSAFE_RUN_ROLE,
        "payload": _unsafe_payload(marker, message=UNSAFE_RUN_MESSAGE),
    }


def _event_jsonl_line(event: dict) -> str:
    return json.dumps(event, ensure_ascii=False) + "\n"


def _unsafe_payload(marker: str, *, message: str) -> dict:
    return {
        "type": "command",
        "message": message,
        "prompt": marker,
        "json_schema": {"marker": marker},
    }
