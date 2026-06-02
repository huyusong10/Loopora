from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.web import build_app

from alignment_test_support import _wait_for_status


def test_alignment_api_covers_session_events_bundle_and_import(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/alignments/sessions",
        json={"workdir": str(sample_workdir), "message": "Create a runnable bundle."},
    )
    assert response.status_code == HTTPStatus.CREATED
    session_id = response.json()["session"]["id"]
    _wait_for_status(service, session_id, "waiting_user")
    confirm_response = client.post(f"/api/alignments/sessions/{session_id}/messages", json={"message": "确认"})
    assert confirm_response.status_code == HTTPStatus.OK
    _wait_for_status(service, session_id, "ready")

    session_response = client.get(f"/api/alignments/sessions/{session_id}")
    assert session_response.status_code == HTTPStatus.OK
    assert session_response.json()["session"]["status"] == "ready"

    events_response = client.get(f"/api/alignments/sessions/{session_id}/events")
    assert events_response.status_code == HTTPStatus.OK
    assert any(event["event_type"] == "alignment_ready" for event in events_response.json())

    with client.stream("GET", f"/api/alignments/sessions/{session_id}/stream") as stream_response:
        assert stream_response.status_code == HTTPStatus.OK
        body = "".join(chunk.decode() if isinstance(chunk, bytes) else chunk for chunk in stream_response.iter_text())
    assert "alignment_ready" in body

    list_response = client.get("/api/alignments/sessions")
    assert list_response.status_code == HTTPStatus.OK
    assert list_response.json()["sessions"][0]["id"] == session_id
    assert list_response.json()["sessions"][0]["native_resume_available"] is True

    bundle_response = client.get(f"/api/alignments/sessions/{session_id}/bundle")
    assert bundle_response.status_code == HTTPStatus.OK
    bundle_payload = bundle_response.json()
    assert bundle_payload["ok"] is True
    assert bundle_payload["workflow_preview"]["roles"][0]["archetype"] == "builder"

    bundle_path = Path(service.get_alignment_session(session_id)["bundle_path"])
    bundle_path.write_text(
        bundle_path.read_text(encoding="utf-8").replace("Aligned Starter Bundle", "Synced Starter Bundle", 1),
        encoding="utf-8",
    )
    sync_response = client.post(f"/api/alignments/sessions/{session_id}/bundle/sync")
    assert sync_response.status_code == HTTPStatus.OK
    sync_payload = sync_response.json()
    assert sync_payload["ok"] is True
    assert sync_payload["metadata"]["name"] == "Synced Starter Bundle"
    assert sync_payload["session"]["status"] == "ready"
    assert any(event["event_type"] == "alignment_bundle_synced" for event in service.list_alignment_events(session_id))

    import_response = client.post(
        f"/api/alignments/sessions/{session_id}/import",
        json={"start_immediately": False},
    )
    assert import_response.status_code == HTTPStatus.CREATED
    assert import_response.json()["bundle"]["id"]
    assert import_response.json()["session"]["status"] == "imported"

    delete_response = client.delete(f"/api/alignments/sessions/{session_id}")
    assert delete_response.status_code == HTTPStatus.OK
    assert delete_response.json()["deleted"] is True
    assert client.get(f"/api/alignments/sessions/{session_id}").status_code == HTTPStatus.NOT_FOUND
    assert client.get("/api/alignments/sessions").json()["sessions"] == []
