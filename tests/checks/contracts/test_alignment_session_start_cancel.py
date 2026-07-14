from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.web import build_app
from loopora.service_alignment_failure_recovery import ALIGNMENT_WORKER_INTERRUPTED

from alignment_test_support import _wait_for_status


def test_alignment_api_start_immediately_false_keeps_new_session_idle(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/alignments/sessions",
        json={
            "workdir": str(sample_workdir),
            "message": "Create a bundle later.",
            "start_immediately": "false",
        },
    )

    assert response.status_code == HTTPStatus.CREATED
    session_id = response.json()["session"]["id"]
    session = service.get_alignment_session(session_id)
    assert session["status"] == "idle"
    assert session["transcript"][-1]["content"] == "Create a bundle later."
    assert not any(event["event_type"] == "alignment_started" for event in service.list_alignment_events(session_id))


def test_alignment_api_create_requires_non_empty_task_message(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    missing = client.post("/api/alignments/sessions", json={"workdir": str(sample_workdir)})
    blank = client.post(
        "/api/alignments/sessions",
        json={"workdir": str(sample_workdir), "message": "   ", "start_immediately": False},
    )
    legacy_user_message = client.post(
        "/api/alignments/sessions",
        json={"workdir": str(sample_workdir), "user_message": "Create from legacy client.", "start_immediately": False},
    )

    assert missing.status_code == HTTPStatus.BAD_REQUEST
    assert missing.json()["error"] == "message is required"
    assert blank.status_code == HTTPStatus.BAD_REQUEST
    assert blank.json()["error"] == "message is required"
    assert legacy_user_message.status_code == HTTPStatus.CREATED
    assert legacy_user_message.json()["session"]["transcript"][-1]["content"] == "Create from legacy client."
    assert len(service.list_alignment_sessions()) == 1


def test_alignment_api_rejects_busy_messages_and_allows_continue_after_cancel(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success", role_delay=0.4)
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/alignments/sessions",
        json={"workdir": str(sample_workdir), "message": "Start slowly."},
    )
    assert response.status_code == HTTPStatus.CREATED
    session_id = response.json()["session"]["id"]

    busy = client.post(f"/api/alignments/sessions/{session_id}/messages", json={"message": "Too soon."})
    assert busy.status_code == HTTPStatus.CONFLICT
    assert "already running" in busy.json()["error"]

    cancelled = client.post(f"/api/alignments/sessions/{session_id}/cancel")
    assert cancelled.status_code == HTTPStatus.OK
    stopped = _wait_for_status(service, session_id, "failed")
    assert stopped["status"] == "failed"
    assert stopped["status_label"] == "cancelled"

    continued = client.post(f"/api/alignments/sessions/{session_id}/messages", json={"message": "Continue after cancel."})
    assert continued.status_code == HTTPStatus.OK
    assert continued.json()["session"]["status"] == "running"


def test_service_restart_recovers_orphaned_planning_and_keeps_task_retryable(
    service_factory,
    sample_workdir: Path,
) -> None:
    original = service_factory(scenario="success")
    created = original.create_alignment_session(
        workdir=sample_workdir,
        message="Preserve this planning task across a local restart.",
        start_immediately=False,
    )
    original.repository.update_alignment_session(
        created["id"],
        status="running",
        active_child_pid=2_147_483_647,
    )

    restarted = service_factory(scenario="success")
    recovered = restarted.get_alignment_session(created["id"])

    assert recovered["status"] == "failed"
    assert recovered["status_label"] == "interrupted"
    assert recovered["active_child_pid"] is None
    assert recovered["failure_recovery"]["kind"] == ALIGNMENT_WORKER_INTERRUPTED
    assert recovered["transcript"][0]["content"] == "Preserve this planning task across a local restart."
    events = restarted.list_alignment_events(created["id"])
    assert events[-1]["event_type"] == "alignment_interrupted"
    assert events[-1]["payload"]["reason"] == "local_worker_interrupted"

    response = TestClient(build_app(service=restarted)).post(
        f"/api/alignments/sessions/{created['id']}/retry-generation",
        json={},
    )
    assert response.status_code == HTTPStatus.OK
    waiting = _wait_for_status(restarted, created["id"], "waiting_user")
    assert [item["content"] for item in waiting["transcript"] if item["role"] == "user"] == [
        "Preserve this planning task across a local restart."
    ]


def test_service_restart_finishes_orphaned_user_cancellation(service_factory, sample_workdir: Path) -> None:
    original = service_factory(scenario="success")
    created = original.create_alignment_session(
        workdir=sample_workdir,
        message="Stop this interrupted task.",
        start_immediately=False,
    )
    original.repository.update_alignment_session(
        created["id"],
        status="running",
        stop_requested=True,
        active_child_pid=2_147_483_647,
    )

    recovered = service_factory(scenario="success").get_alignment_session(created["id"])

    assert recovered["status"] == "failed"
    assert recovered["status_label"] == "cancelled"
    assert recovered["failure_recovery"]["kind"] == "user_cancelled"
