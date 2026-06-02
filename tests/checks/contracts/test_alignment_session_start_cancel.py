from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.web import build_app

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
    _wait_for_status(service, session_id, "failed")

    continued = client.post(f"/api/alignments/sessions/{session_id}/messages", json={"message": "Continue after cancel."})
    assert continued.status_code == HTTPStatus.OK
    assert continued.json()["session"]["status"] == "running"
