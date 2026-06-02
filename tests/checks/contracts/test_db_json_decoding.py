from __future__ import annotations

from pathlib import Path

from loopora.db import LooporaRepository

from db_test_support import _create_run


def test_corrupted_run_json_columns_fall_back_to_empty_objects(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path, run_id="run_corrupt", status="running")

    with repository.transaction() as connection:
        connection.execute(
            "UPDATE loop_runs SET last_verdict_json = ?, task_verdict_json = ?, workflow_json = ? WHERE id = ?",
            ("{", "{", "{", run["id"]),
        )

    refreshed = repository.get_run(run["id"])

    assert refreshed["last_verdict_json"] == {}
    assert refreshed["task_verdict_json"] == {}
    assert refreshed["workflow_json"] == {}


def test_corrupted_array_json_columns_fall_back_to_empty_lists(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    workdir = tmp_path / "bundle-workdir"
    workdir.mkdir()
    bundle = repository.create_bundle(
        {
            "id": "bundle_corrupt_arrays",
            "name": "Corrupt Arrays",
            "workdir": str(workdir),
            "role_definition_ids": ["role_builder", "role_gatekeeper"],
        }
    )
    session = repository.create_alignment_session(
        {
            "id": "alignment_corrupt_arrays",
            "workdir": str(workdir),
            "bundle_path": str(workdir / ".loopora" / "alignment_sessions" / "alignment_corrupt_arrays" / "artifacts" / "bundle.yml"),
            "transcript": [{"role": "user", "content": "Build this."}],
        }
    )

    with repository.transaction() as connection:
        connection.execute(
            "UPDATE bundle_definitions SET role_definition_ids_json = ? WHERE id = ?",
            ("{", bundle["id"]),
        )
        connection.execute(
            "UPDATE alignment_sessions SET transcript_json = ? WHERE id = ?",
            ("{", session["id"]),
        )

    assert repository.get_bundle(bundle["id"])["role_definition_ids_json"] == []
    assert repository.get_alignment_session(session["id"])["transcript"] == []


def test_corrupted_event_payload_json_falls_back_to_empty_object(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path, run_id="run_event_corrupt", status="running")
    event = repository.append_event(run["id"], "run_started", {"status": "running"})

    with repository.transaction() as connection:
        connection.execute(
            "UPDATE run_events SET payload_json = ? WHERE id = ?",
            ("{", event["id"]),
        )

    events = repository.list_events(run["id"])

    assert len(events) == 1
    assert events[0]["payload"] == {}


def test_json_column_shape_mismatches_fall_back_to_declared_defaults(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path, run_id="run_shape_mismatch", status="running")
    event = repository.append_event(run["id"], "run_started", {"status": "running"})
    workdir = tmp_path / "shape-bundle-workdir"
    workdir.mkdir()
    bundle = repository.create_bundle(
        {
            "id": "bundle_shape_mismatch",
            "name": "Shape Mismatch",
            "workdir": str(workdir),
            "role_definition_ids": ["role_builder"],
        }
    )
    session = repository.create_alignment_session(
        {
            "id": "alignment_shape_mismatch",
            "workdir": str(workdir),
            "bundle_path": str(workdir / ".loopora" / "alignment_sessions" / "alignment_shape_mismatch" / "artifacts" / "bundle.yml"),
            "transcript": [{"role": "user", "content": "Build this."}],
            "validation": {"ready": False},
        }
    )

    with repository.transaction() as connection:
        connection.execute(
            "UPDATE loop_runs SET workflow_json = ? WHERE id = ?",
            ("[]", run["id"]),
        )
        connection.execute(
            "UPDATE run_events SET payload_json = ? WHERE id = ?",
            ("[]", event["id"]),
        )
        connection.execute(
            "UPDATE bundle_definitions SET role_definition_ids_json = ? WHERE id = ?",
            ('{"role": "role_builder"}', bundle["id"]),
        )
        connection.execute(
            "UPDATE alignment_sessions SET transcript_json = ?, validation_json = ? WHERE id = ?",
            ('{"role": "user"}', "[]", session["id"]),
        )

    assert repository.get_run(run["id"])["workflow_json"] == {}
    assert repository.list_events(run["id"])[0]["payload"] == {}
    assert repository.get_bundle(bundle["id"])["role_definition_ids_json"] == []
    refreshed_session = repository.get_alignment_session(session["id"])
    assert refreshed_session["transcript"] == []
    assert refreshed_session["validation"] == {}
