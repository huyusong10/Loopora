from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.web import build_app

from web_file_access_test_support import create_file_preview_run


BROKEN_JSONL_LINE_NUMBER = 2


def test_api_file_preview_reports_json_parse_errors(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    run = create_file_preview_run(service, sample_spec_file, sample_workdir, name="JSON Preview Loop")
    broken_json_path = sample_workdir / "broken.json"
    broken_json_path.write_text("{\n", encoding="utf-8")

    client = TestClient(build_app(service=service))
    response = client.get(f"/api/files?run_id={run['id']}&root=workdir&path=broken.json")

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["kind"] == "file"
    assert payload["content"] == "{\n"
    assert payload["parse_error"]


def test_api_file_preview_keeps_valid_jsonl_lines_when_some_are_broken(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    run = create_file_preview_run(service, sample_spec_file, sample_workdir, name="JSONL Preview Loop")
    log_path = sample_workdir / "events.jsonl"
    log_path.write_text('{"event":"good"}\n{\n{"event":"also-good"}\n', encoding="utf-8")

    client = TestClient(build_app(service=service))
    response = client.get(f"/api/files?run_id={run['id']}&root=workdir&path=events.jsonl")

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["kind"] == "file"
    assert '"event": "good"' in payload["content"]
    assert '"event": "also-good"' in payload["content"]
    assert payload["jsonl_parse_errors"] == [
        {"line": BROKEN_JSONL_LINE_NUMBER, "error": "Expecting property name enclosed in double quotes"}
    ]
