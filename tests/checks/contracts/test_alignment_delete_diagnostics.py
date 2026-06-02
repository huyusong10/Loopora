from __future__ import annotations

import json
import logging
from pathlib import Path

import loopora.service_alignment_session_layout_context as alignment_session_layout_context_module
import loopora.service_cleanup_diagnostics as cleanup_diagnostics


def test_alignment_delete_logs_session_dir_cleanup_failure(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
    caplog,
) -> None:
    service = service_factory(scenario="success")
    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Create a deletable alignment session.",
        start_immediately=False,
    )

    def fail_rmtree(path: Path) -> None:
        if Path(path) == Path(session["artifact_dir"]):
            raise OSError("alignment dir locked")
        raise AssertionError(f"unexpected cleanup target: {path}")

    monkeypatch.setattr(cleanup_diagnostics.shutil, "rmtree", fail_rmtree)
    with caplog.at_level(logging.WARNING, logger="loopora.service_alignment"):
        deleted = service.delete_alignment_session(session["id"])

    assert deleted is True
    artifact_events = [
        json.loads(line)
        for line in (Path(session["artifact_dir"]) / "events" / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    diagnostic_event = next(event for event in artifact_events if event["event_type"] == "alignment_session_cleanup_failed")
    assert diagnostic_event["payload"]["operation"] == "alignment_session_delete"
    assert diagnostic_event["payload"]["resource_type"] == "path"
    assert diagnostic_event["payload"]["owner_id"] == session["id"]
    diagnostics = service.local_asset_diagnostics()
    assert any(item["session_id"] == session["id"] for item in diagnostics["orphan_alignment_dirs"])
    assert any(
        getattr(record, "event", "") == "service.cleanup.failed"
        and (getattr(record, "context", {}) or {}).get("operation") == "alignment_session_delete"
        for record in caplog.records
    )


def test_alignment_delete_logs_cleanup_diagnostic_callback_failure(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
    caplog,
) -> None:
    service = service_factory(scenario="success")
    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Delete with a broken diagnostic callback.",
        start_immediately=False,
    )

    def fail_rmtree(path: Path) -> None:
        if Path(path) == Path(session["artifact_dir"]):
            raise OSError("alignment dir locked")
        raise AssertionError(f"unexpected cleanup target: {path}")

    def fail_diagnostic_callback(*_args: object) -> None:
        raise RuntimeError("diagnostic callback down")

    monkeypatch.setattr(cleanup_diagnostics.shutil, "rmtree", fail_rmtree)
    monkeypatch.setattr(
        alignment_session_layout_context_module,
        "append_alignment_local_diagnostic_event",
        fail_diagnostic_callback,
    )
    with caplog.at_level(logging.WARNING, logger="loopora.service_alignment"):
        deleted = service.delete_alignment_session(session["id"])

    assert deleted is True
    operations = [
        (getattr(record, "context", {}) or {}).get("operation")
        for record in caplog.records
        if getattr(record, "event", "") == "service.cleanup.failed"
    ]
    assert "alignment_session_delete" in operations


def test_alignment_delete_logs_local_diagnostic_event_write_failure(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
    caplog,
) -> None:
    service = service_factory(scenario="success")
    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Delete with a broken local event sink.",
        start_immediately=False,
    )
    hydrated_session = service.get_alignment_session(session["id"])

    def fail_rmtree(path: Path) -> None:
        if Path(path) == Path(session["artifact_dir"]):
            raise OSError("alignment dir locked")
        raise AssertionError(f"unexpected cleanup target: {path}")

    def fail_ensure_alignment_artifact_dirs(_root: Path) -> None:
        raise OSError("alignment artifact events locked")

    monkeypatch.setattr(cleanup_diagnostics.shutil, "rmtree", fail_rmtree)
    monkeypatch.setattr(service, "get_alignment_session", lambda _session_id: hydrated_session)
    monkeypatch.setattr(
        alignment_session_layout_context_module,
        "ensure_alignment_artifact_dirs",
        fail_ensure_alignment_artifact_dirs,
    )
    with caplog.at_level(logging.WARNING, logger="loopora.service_alignment"):
        deleted = service.delete_alignment_session(session["id"])

    assert deleted is True
    assert any(
        getattr(record, "event", "") == "service.cleanup.failed"
        and (getattr(record, "context", {}) or {}).get("operation") == "alignment_session_delete"
        for record in caplog.records
    )
