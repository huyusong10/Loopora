from __future__ import annotations

import json
from http import HTTPStatus

from fastapi.testclient import TestClient

from loopora.settings import configure_logging
from loopora.web import build_app

from web_api_test_support import _read_service_log_records
from compacted_contract_support import stream_response_text


DEFAULT_RUN_EVENT_STREAM_LIMIT = 200
STREAM_FAILURE_AFTER_ID = 42


def test_api_run_stream_emits_redacted_stream_error_on_backend_failure() -> None:
    configure_logging()

    class FlakyService:
        def get_run(self, run_id: str) -> dict:
            return {"id": run_id, "status": "running", "loop_id": "loop_test"}

        def latest_run_event_id(self, run_id: str) -> int:
            assert run_id == "run_test"
            return STREAM_FAILURE_AFTER_ID

        def stream_events(self, run_id: str, after_id: int = 0, limit: int = DEFAULT_RUN_EVENT_STREAM_LIMIT) -> list[dict]:
            assert run_id == "run_test"
            assert after_id == STREAM_FAILURE_AFTER_ID
            assert limit == DEFAULT_RUN_EVENT_STREAM_LIMIT
            raise RuntimeError("database unavailable")

    client = TestClient(build_app(service=FlakyService()))

    with client.stream("GET", f"/api/runs/run_test/stream?after_id={STREAM_FAILURE_AFTER_ID}") as response:
        assert response.status_code == HTTPStatus.OK
        body = stream_response_text(response)

    assert "event: stream_error" in body
    assert "database unavailable" not in body
    payload = json.loads(next(line.removeprefix("data: ") for line in body.splitlines() if line.startswith("data: ")))
    assert payload == {
        "run_id": "run_test",
        "after_id": STREAM_FAILURE_AFTER_ID,
        "error": "stream_unavailable",
        "retryable": True,
    }
    assert any(
        record.get("event") == "web.run_stream.failed" and (record.get("error") or {}).get("message") == "database unavailable"
        for record in _read_service_log_records()
    )
