from __future__ import annotations

from pathlib import Path

from loopora.db import LooporaRepository
from loopora.db_event_records import RunObservationSnapshotRowsRequest
import loopora.db_row_decoding as row_decoding

from db_test_support import _create_run


def test_list_events_normalizes_cursor_and_limit_before_sqlite(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    _create_run(repository, tmp_path)
    for index in range(3):
        repository.append_event("run_test", "progress", {"index": index})

    assert [event["payload"]["index"] for event in repository.list_events("run_test", after_id=-10, limit=2)] == [0, 1]
    assert [event["payload"]["index"] for event in repository.list_events("run_test", after_id=True, limit=2)] == [0, 1]
    assert [event["payload"]["index"] for event in repository.list_events("run_test", after_id="1", limit=2)] == [0, 1]
    assert repository.list_events("run_test", limit=0) == []
    assert repository.list_events("run_test", limit=-1) == []
    assert repository.list_events("run_test", limit=True) == []
    assert repository.list_events("run_test", limit="2") == []


def test_takeaway_projection_source_event_id_requires_integer_sequence(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path, run_id="run_projection_source_event", status="succeeded")
    event = repository.append_event(run["id"], "run_finished", {"status": "succeeded"})
    boolean_source_event_id = True

    assert repository.record_run_takeaway_projection(run["id"], boolean_source_event_id, {"run_status": "failed"}) is False
    assert repository.record_run_takeaway_projection(run["id"], str(event["id"]), {"run_status": "failed"}) is False
    assert repository.record_run_takeaway_projection(run["id"], event["id"], {"run_status": "succeeded"}) is True

    snapshot = repository.run_observation_snapshot_rows(
        RunObservationSnapshotRowsRequest(
            run_id=run["id"],
            timeline_event_types=["run_finished"],
            progress_event_types=[],
        )
    )

    assert snapshot["key_takeaway_projection"] == {"run_status": "succeeded", "source_event_id": event["id"]}


def test_append_event_does_not_write_takeaway_projection(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path, run_id="run_projection_boundary", status="running")

    event = repository.append_event(run["id"], "run_finished", {"status": "succeeded"})

    assert event["event_type"] == "run_finished"
    with repository._connect() as connection:
        row = connection.execute(
            "SELECT 1 FROM run_takeaway_projections WHERE run_id = ?",
            (run["id"],),
        ).fetchone()
    assert row is None


def test_takeaway_projection_shape_mismatch_degrades_with_diagnostic(tmp_path: Path, monkeypatch) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path, run_id="run_projection_shape", status="succeeded")
    event = repository.append_event(run["id"], "run_finished", {"status": "succeeded"})
    repository.record_run_takeaway_projection(run["id"], event["id"], {"run_status": "succeeded"})
    log_calls: list[dict] = []

    def capture_log_event(_logger, _level, event_name, _message, **context):
        log_calls.append({"event": event_name, "context": context})

    monkeypatch.setattr(row_decoding, "log_event", capture_log_event)
    with repository.transaction() as connection:
        connection.execute(
            "UPDATE run_takeaway_projections SET payload_json = ? WHERE run_id = ? AND source_event_id = ?",
            ("[]", run["id"], event["id"]),
        )

    snapshot = repository.run_observation_snapshot_rows(
        RunObservationSnapshotRowsRequest(
            run_id=run["id"],
            timeline_event_types=["run_finished"],
            progress_event_types=[],
        )
    )

    assert snapshot["key_takeaway_projection"] == {"source_event_id": event["id"]}
    assert any(
        call["event"] == "db.row.decode_json_shape_mismatch"
        and call["context"]["column"] == "payload_json"
        and call["context"]["expected_type"] == "dict"
        and call["context"]["actual_type"] == "list"
        for call in log_calls
    )
