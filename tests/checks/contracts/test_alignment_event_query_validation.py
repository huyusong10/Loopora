from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.web import build_app
from loopora.web_streaming import MAX_EVENT_CURSOR_ID


MIN_ALIGNMENT_CURSOR_EVENTS = 2


def test_alignment_event_api_rejects_out_of_range_query_params(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    for path in (
        "/api/alignments/sessions?limit=0",
        "/api/alignments/sessions?limit=101",
        "/api/alignments/sessions/session_test/events?after_id=-1",
        f"/api/alignments/sessions/session_test/events?after_id={MAX_EVENT_CURSOR_ID + 1}",
        "/api/alignments/sessions/session_test/events?limit=0",
        "/api/alignments/sessions/session_test/events?limit=5001",
        "/api/alignments/sessions/session_test/stream?after_id=-1",
        f"/api/alignments/sessions/session_test/stream?after_id={MAX_EVENT_CURSOR_ID + 1}",
    ):
        response = client.get(path)
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["error"] == "request validation failed"


def test_alignment_event_cursor_requires_integer_sequence(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a focused starter experience.",
    )
    service.repository.append_alignment_event(session["id"], "alignment_status_checked", {"status": "idle"})

    events = service.list_alignment_events(session["id"])
    assert len(events) >= MIN_ALIGNMENT_CURSOR_EVENTS
    first_id = events[0]["id"]

    assert [event["id"] for event in service.list_alignment_events(session["id"], after_id=True, limit=2)] == [
        event["id"] for event in events[:2]
    ]
    assert [event["id"] for event in service.list_alignment_events(session["id"], after_id=str(first_id), limit=2)] == [
        event["id"] for event in events[:2]
    ]
    assert service.list_alignment_events(session["id"], limit=True) == []


def test_alignment_event_api_rejects_cursor_beyond_current_events() -> None:
    class CursorAwareService:
        def get_alignment_session(self, session_id: str) -> dict:
            return {"id": session_id, "status": "ready"}

        def latest_alignment_event_id(self, session_id: str) -> int:
            assert session_id == "session_test"
            return 10

    client = TestClient(build_app(service=CursorAwareService()))

    response = client.get("/api/alignments/sessions/session_test/events?after_id=11")

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()["error"] == "event cursor is out of range"
