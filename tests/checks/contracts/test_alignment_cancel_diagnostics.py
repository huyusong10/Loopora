from __future__ import annotations

import logging

import loopora.service_alignment_context_factory as alignment_context_factory_module


def test_alignment_cancel_signal_failure_writes_structured_diagnostics(
    service_factory,
    sample_workdir,
    monkeypatch,
    caplog,
) -> None:
    service = service_factory(scenario="success")
    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Cancel a running alignment.",
        start_immediately=False,
    )
    service.repository.update_alignment_session(
        session["id"],
        status="running",
        active_child_pid=987654,
    )

    def fail_signal(_pid: int, _signal: int) -> None:
        raise OSError("signal denied")

    monkeypatch.setattr(alignment_context_factory_module.os, "kill", fail_signal)
    with caplog.at_level(logging.WARNING, logger="loopora.service_alignment"):
        cancelled = service.cancel_alignment_session(session["id"])

    assert cancelled["stop_requested"] is True
    events = service.list_alignment_events(session["id"])
    diagnostic_event = next(event for event in events if event["event_type"] == "alignment_cancel_signal_failed")
    assert diagnostic_event["payload"]["operation"] == "alignment_cancel_signal"
    assert diagnostic_event["payload"]["resource_type"] == "process"
    assert diagnostic_event["payload"]["resource_id"] == "987654"
    assert diagnostic_event["payload"]["owner_id"] == session["id"]
    assert diagnostic_event["payload"]["error_type"] == "OSError"
    assert any(
        getattr(record, "event", "") == "service.cleanup.failed"
        and (getattr(record, "context", {}) or {}).get("operation") == "alignment_cancel_signal"
        for record in caplog.records
    )


def test_alignment_cancel_signal_diagnostic_event_failure_is_logged_without_masking_cancel(
    service_factory,
    sample_workdir,
    monkeypatch,
    caplog,
) -> None:
    service = service_factory(scenario="success")
    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Cancel a running alignment with a broken event sink.",
        start_immediately=False,
    )
    service.repository.update_alignment_session(
        session["id"],
        status="running",
        active_child_pid=987654,
    )
    original_append_alignment_event = service.repository.append_alignment_event

    def fail_diagnostic_event(session_id: str, event_type: str, payload: dict) -> dict:
        if event_type == "alignment_cancel_signal_failed":
            raise OSError("alignment event sink locked")
        return original_append_alignment_event(session_id, event_type, payload)

    def fail_signal(_pid: int, _signal: int) -> None:
        raise OSError("signal denied")

    monkeypatch.setattr(service.repository, "append_alignment_event", fail_diagnostic_event)
    monkeypatch.setattr(alignment_context_factory_module.os, "kill", fail_signal)
    with caplog.at_level(logging.WARNING, logger="loopora.service_alignment"):
        cancelled = service.cancel_alignment_session(session["id"])

    assert cancelled["stop_requested"] is True
    assert any(
        getattr(record, "event", "") == "service.cleanup.failed"
        and (getattr(record, "context", {}) or {}).get("operation") == "alignment_cancel_signal_event_write"
        and (getattr(record, "context", {}) or {}).get("resource_type") == "alignment_event"
        for record in caplog.records
    )
