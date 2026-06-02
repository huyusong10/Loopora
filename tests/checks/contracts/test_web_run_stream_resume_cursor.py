from __future__ import annotations

from http import HTTPStatus

from fastapi.testclient import TestClient

from loopora.settings import configure_logging
from loopora.web import build_app

from web_api_test_support import _read_service_log_records
from compacted_contract_support import stream_response_text


DEFAULT_RUN_EVENT_STREAM_LIMIT = 200
LATEST_RUN_EVENT_ID = 10
REQUESTED_AFTER_ID = 7


def test_api_run_stream_logs_invalid_resume_cursor_and_keeps_request_cursor() -> None:
    configure_logging()
    captured: dict[str, int] = {}

    class CursorAwareService:
        def get_run(self, run_id: str) -> dict:
            return {"id": run_id, "status": "succeeded", "loop_id": "loop_test"}

        def latest_run_event_id(self, run_id: str) -> int:
            assert run_id == "run_test"
            return LATEST_RUN_EVENT_ID

        def stream_events(self, run_id: str, after_id: int = 0, limit: int = DEFAULT_RUN_EVENT_STREAM_LIMIT) -> list[dict]:
            assert run_id == "run_test"
            assert limit == DEFAULT_RUN_EVENT_STREAM_LIMIT
            captured["after_id"] = after_id
            return []

    client = TestClient(build_app(service=CursorAwareService()))

    with client.stream(
        "GET",
        f"/api/runs/run_test/stream?after_id={REQUESTED_AFTER_ID}",
        headers={"Last-Event-ID": "not-a-number"},
    ) as response:
        assert response.status_code == HTTPStatus.OK
        assert stream_response_text(response) == ""

    assert captured["after_id"] == REQUESTED_AFTER_ID
    record = next(item for item in _read_service_log_records() if item["event"] == "web.run_stream.resume_cursor_invalid")
    assert record["run_id"] == "run_test"
    assert record["context"]["after_id"] == REQUESTED_AFTER_ID
    assert record["context"]["latest_event_id"] == LATEST_RUN_EVENT_ID
    assert record["context"]["invalid_last_event_id"] == "not-a-number"


def test_api_run_stream_ignores_resume_cursor_beyond_current_run_events() -> None:
    configure_logging()
    captured: dict[str, int] = {}

    class CursorAwareService:
        def get_run(self, run_id: str) -> dict:
            return {"id": run_id, "status": "succeeded", "loop_id": "loop_test"}

        def latest_run_event_id(self, run_id: str) -> int:
            assert run_id == "run_test"
            return LATEST_RUN_EVENT_ID

        def stream_events(self, run_id: str, after_id: int = 0, limit: int = DEFAULT_RUN_EVENT_STREAM_LIMIT) -> list[dict]:
            assert run_id == "run_test"
            assert limit == DEFAULT_RUN_EVENT_STREAM_LIMIT
            captured["after_id"] = after_id
            return []

    client = TestClient(build_app(service=CursorAwareService()))

    with client.stream(
        "GET",
        f"/api/runs/run_test/stream?after_id={REQUESTED_AFTER_ID}",
        headers={"Last-Event-ID": "11"},
    ) as response:
        assert response.status_code == HTTPStatus.OK
        assert stream_response_text(response) == ""

    assert captured["after_id"] == REQUESTED_AFTER_ID
    record = next(item for item in _read_service_log_records() if item["event"] == "web.run_stream.resume_cursor_invalid")
    assert record["run_id"] == "run_test"
    assert record["context"]["after_id"] == REQUESTED_AFTER_ID
    assert record["context"]["latest_event_id"] == LATEST_RUN_EVENT_ID
    assert record["context"]["invalid_last_event_id"] == "11"
