from __future__ import annotations

from http import HTTPStatus

from fastapi.testclient import TestClient

from loopora.settings import configure_logging
from loopora.web import build_app

from web_api_test_support import _read_service_log_records


def test_api_unhandled_error_returns_stable_json_and_logs_exception() -> None:
    configure_logging()
    raw_error = "database unavailable for api-internal-error-test"

    class FlakyService:
        def latest_run_event_id(self, run_id: str) -> int:
            assert run_id == "run_test"
            raise RuntimeError(raw_error)

    client = TestClient(build_app(service=FlakyService()), raise_server_exceptions=False)

    response = client.get("/api/runs/run_test/events")

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json() == {"error": "internal server error"}
    assert raw_error not in response.text
    assert any(
        record.get("event") == "web.request.failed"
        and (record.get("error") or {}).get("message") == raw_error
        and (record.get("context") or {}).get("request_path") == "/api/runs/run_test/events"
        and (record.get("context") or {}).get("status_code") == HTTPStatus.INTERNAL_SERVER_ERROR
        for record in _read_service_log_records()
    )


def test_web_logs_completed_requests(service_factory) -> None:
    configure_logging()
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.get("/tutorial")

    assert response.status_code == HTTPStatus.OK
    records = _read_service_log_records()
    record = next(
        item for item in records if item["event"] == "web.request.completed" and item["context"]["request_path"] == "/tutorial"
    )
    assert record["context"]["status_code"] == HTTPStatus.OK
    assert record["context"]["duration_ms"] >= 0
