from __future__ import annotations

from pathlib import Path

from alignment_test_support import (
    _confirm_alignment_agreement,
    _wait_for_status,
)


def test_alignment_service_reuses_executor_session_ref_between_turns(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="alignment_question")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="I need help shaping this task.",
    )
    first = _wait_for_status(service, created["id"], "waiting_user")
    first_session_id = first["executor_session_ref"]["session_id"]

    service.append_alignment_message(created["id"], "更怕做糙。")
    second = _wait_for_status(service, created["id"], "waiting_user")

    assert second["executor_session_ref"]["session_id"] == first_session_id
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_executor_session_ref" for event in events)


def test_alignment_service_falls_back_when_native_resume_fails(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="alignment_resume_failure")

    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Generate a bundle after resume trouble.",
        start_immediately=False,
    )
    service.repository.update_alignment_session(session["id"], executor_session_ref={"session_id": "stale-session"})
    service.start_alignment_session_async(session["id"])
    _wait_for_status(service, session["id"], "waiting_user")
    service.repository.update_alignment_session(
        session["id"],
        alignment_stage="confirmed",
        working_agreement={"summary": "Confirmed test agreement.", "confirmed_at": "test"},
    )
    service.start_alignment_session_async(session["id"])
    ready = _wait_for_status(service, session["id"], "ready")

    assert ready["validation"]["ok"] is True
    events = service.list_alignment_events(session["id"])
    assert any(event["event_type"] == "alignment_native_resume_fallback" for event in events)


def test_alignment_service_repairs_invalid_bundle_once(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="alignment_invalid_then_valid")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Generate a bundle, and recover if the first draft is malformed.",
    )
    session = _confirm_alignment_agreement(service, created["id"])

    assert session["repair_attempts"] == 1
    assert session["validation"]["ok"] is True
    events = service.list_alignment_events(session["id"])
    assert any(event["event_type"] == "alignment_repair_started" for event in events)


def test_alignment_service_repairs_semantically_incomplete_bundle_once(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_semantic_invalid_then_valid")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Generate a semantically complete bundle.",
    )
    session = _confirm_alignment_agreement(service, created["id"])

    assert session["repair_attempts"] == 1
    assert session["validation"]["ok"] is True
    failed_events = [
        event for event in service.list_alignment_events(created["id"]) if event["event_type"] == "alignment_validation_failed"
    ]
    assert failed_events
    assert "semantic lint" in failed_events[0]["payload"]["error"]


def test_alignment_service_fails_after_invalid_repair(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="alignment_invalid")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Generate a bundle that remains invalid.",
    )
    session = _confirm_alignment_agreement(service, created["id"], "failed")

    assert session["repair_attempts"] == 1
    assert session["validation"]["ok"] is False
    assert "collaboration_summary" in session["error_message"]
