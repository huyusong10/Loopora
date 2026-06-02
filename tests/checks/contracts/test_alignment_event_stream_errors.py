from __future__ import annotations

import json
import logging
from http import HTTPStatus

from fastapi.testclient import TestClient

from loopora.web import build_app


BACKEND_FAILURE_AFTER_ID = 9
DEFAULT_ALIGNMENT_EVENT_STREAM_LIMIT = 200
INVALID_CURSOR_LATEST_EVENT_ID = 10
INVALID_CURSOR_REQUEST_AFTER_ID = 7


def test_alignment_stream_emits_redacted_stream_error_on_backend_failure(caplog) -> None:
    class FlakyService:
        def get_alignment_session(self, session_id: str) -> dict:
            return {"id": session_id, "status": "running"}

        def latest_alignment_event_id(self, session_id: str) -> int:
            assert session_id == "session_test"
            return BACKEND_FAILURE_AFTER_ID

        def list_alignment_events(
            self,
            session_id: str,
            after_id: int = 0,
            limit: int = DEFAULT_ALIGNMENT_EVENT_STREAM_LIMIT,
        ) -> list[dict]:
            assert session_id == "session_test"
            assert after_id == BACKEND_FAILURE_AFTER_ID
            assert limit == DEFAULT_ALIGNMENT_EVENT_STREAM_LIMIT
            raise RuntimeError("alignment database unavailable")

    client = TestClient(build_app(service=FlakyService()))

    with (
        caplog.at_level(logging.ERROR, logger="loopora.web"),
        client.stream("GET", f"/api/alignments/sessions/session_test/stream?after_id={BACKEND_FAILURE_AFTER_ID}") as response,
    ):
        assert response.status_code == HTTPStatus.OK
        body = "".join(chunk.decode() if isinstance(chunk, bytes) else chunk for chunk in response.iter_text())

    assert "event: stream_error" in body
    assert "alignment database unavailable" not in body
    payload = json.loads(next(line.removeprefix("data: ") for line in body.splitlines() if line.startswith("data: ")))
    assert payload == {
        "session_id": "session_test",
        "after_id": BACKEND_FAILURE_AFTER_ID,
        "error": "stream_unavailable",
        "retryable": True,
    }
    assert any(
        getattr(record, "event", "") == "web.alignment_stream.failed"
        and record.exc_info
        and "alignment database unavailable" in str(record.exc_info[1])
        for record in caplog.records
    )


def test_alignment_stream_logs_invalid_resume_cursor_and_keeps_request_cursor(caplog) -> None:
    captured: dict[str, int] = {}

    class CursorAwareService:
        def get_alignment_session(self, session_id: str) -> dict:
            return {"id": session_id, "status": "ready"}

        def latest_alignment_event_id(self, session_id: str) -> int:
            assert session_id == "session_test"
            return INVALID_CURSOR_LATEST_EVENT_ID

        def list_alignment_events(
            self,
            session_id: str,
            after_id: int = 0,
            limit: int = DEFAULT_ALIGNMENT_EVENT_STREAM_LIMIT,
        ) -> list[dict]:
            assert session_id == "session_test"
            assert limit == DEFAULT_ALIGNMENT_EVENT_STREAM_LIMIT
            captured["after_id"] = after_id
            return []

    client = TestClient(build_app(service=CursorAwareService()))

    with (
        caplog.at_level(logging.WARNING, logger="loopora.web"),
        client.stream(
            "GET",
            f"/api/alignments/sessions/session_test/stream?after_id={INVALID_CURSOR_REQUEST_AFTER_ID}",
            headers={"Last-Event-ID": "11"},
        ) as response,
    ):
        assert response.status_code == HTTPStatus.OK
        assert "".join(chunk.decode() if isinstance(chunk, bytes) else chunk for chunk in response.iter_text()) == ""

    assert captured["after_id"] == INVALID_CURSOR_REQUEST_AFTER_ID
    assert any(
        getattr(record, "event", "") == "web.alignment_stream.resume_cursor_invalid"
        and getattr(record, "context", {}).get("session_id") == "session_test"
        and getattr(record, "context", {}).get("after_id") == INVALID_CURSOR_REQUEST_AFTER_ID
        and getattr(record, "context", {}).get("latest_event_id") == INVALID_CURSOR_LATEST_EVENT_ID
        and getattr(record, "context", {}).get("invalid_last_event_id") == "11"
        for record in caplog.records
    )
