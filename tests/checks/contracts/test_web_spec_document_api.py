from __future__ import annotations

import json
from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.web import build_app


SPEC_DOCUMENT_GET_ENDPOINTS = ("/api/specs/validate", "/api/specs/preview", "/api/specs/document")
SPEC_WITH_TWO_CHECKS = (
    "# Task\n\nKeep editing local.\n\n"
    "# Done When\n\n- The disk file updates after save.\n- The rendered preview updates too.\n"
)
SAVED_SPEC = "# Task\n\nSaved copy.\n\n# Done When\n\n- The file matches the editor after save.\n"
SPEC_WITH_TWO_CHECKS_VALIDATION_COUNT = 2


def test_api_spec_document_returns_content_rendering_and_validation(tmp_path: Path, service_factory) -> None:
    client = spec_client(service_factory)
    spec_path = write_text_file(tmp_path / "editable-spec.md", SPEC_WITH_TWO_CHECKS)

    response = client.get("/api/specs/document", params={"path": str(spec_path)})

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["ok"] is True
    assert payload["path"] == str(spec_path.resolve())
    assert payload["content"].startswith("# Task")
    assert "<h1>Task</h1>" in payload["rendered_html"]
    assert payload["validation"]["ok"] is True
    assert payload["validation"]["check_count"] == SPEC_WITH_TWO_CHECKS_VALIDATION_COUNT
    assert payload["validation"]["check_mode"] == "specified"


def test_api_spec_document_save_writes_file_and_returns_validation(tmp_path: Path, service_factory) -> None:
    client = spec_client(service_factory)
    spec_path = write_text_file(tmp_path / "editable-spec.md", "# Task\n\nInitial\n")

    response = client.put(
        "/api/specs/document",
        json={
            "path": str(spec_path),
            "content": SAVED_SPEC.replace("\n", "\r\n"),
        },
    )

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["ok"] is True
    assert payload["content"] == SAVED_SPEC
    assert spec_path.read_text(encoding="utf-8") == payload["content"]
    assert payload["validation"]["ok"] is True
    assert payload["validation"]["check_count"] == 1
    assert "<h1>Done When</h1>" in payload["rendered_html"]


def test_api_spec_document_endpoints_reject_non_markdown_paths(tmp_path: Path, service_factory) -> None:
    client = spec_client(service_factory)
    non_spec_path = write_text_file(tmp_path / "not-a-spec.txt", "# Task\n\nSensitive but parseable local text.\n")

    assert_get_endpoints_reject(client, non_spec_path, "Markdown file", hidden_text="Sensitive but parseable")

    save_response = client.put(
        "/api/specs/document",
        json={"path": str(non_spec_path), "content": "# Task\n\nOverwritten\n"},
    )
    assert_json_error(save_response, "Markdown file")
    assert "Sensitive but parseable" in non_spec_path.read_text(encoding="utf-8")

    init_response = client.post("/api/specs/init", json={"path": str(tmp_path / "created.txt"), "locale": "en"})
    assert init_response.status_code == HTTPStatus.BAD_REQUEST
    assert "Markdown file" in init_response.json()["error"]


def test_api_spec_document_endpoints_reject_oversized_markdown(tmp_path: Path, service_factory) -> None:
    client = spec_client(service_factory)
    oversized_path = write_text_file(tmp_path / "oversized-spec.md", "# Task\n\n" + ("x" * 1_000_001))

    assert_get_endpoints_reject(client, oversized_path, "too large")

    save_response = client.put(
        "/api/specs/document",
        json={"path": str(tmp_path / "new-spec.md"), "content": "# Task\n\n" + ("x" * 1_000_001)},
    )
    assert_json_error(save_response, "too large")
    assert not (tmp_path / "new-spec.md").exists()


def test_api_spec_document_endpoints_reject_binary_markdown(tmp_path: Path, service_factory) -> None:
    client = spec_client(service_factory)

    binary_path = tmp_path / "binary-spec.md"
    binary_path.write_bytes(b"# Task\n\n\x00binary-like content\n")

    assert_get_endpoints_reject(client, binary_path, "text markdown", hidden_text="binary-like content")
    save_path = write_text_file(tmp_path / "save-target.md", "# Task\n\nKeep this text.\n")

    save_response = client.put(
        "/api/specs/document",
        json={"path": str(save_path), "content": "# Task\n\n\u0000binary-like content\n"},
    )
    assert_json_error(save_response, "text markdown")
    assert save_path.read_text(encoding="utf-8") == "# Task\n\nKeep this text.\n"


def test_api_spec_document_endpoints_reject_non_utf8_markdown(tmp_path: Path, service_factory) -> None:
    client = spec_client(service_factory)

    invalid_path = tmp_path / "invalid-spec.md"
    invalid_path.write_bytes(b"# Task\n\n\xff\n")

    assert_get_endpoints_reject(client, invalid_path, "UTF-8 encoded Markdown")


def spec_client(service_factory) -> TestClient:
    return TestClient(build_app(service=service_factory(scenario="success")))


def write_text_file(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def assert_json_error(response, expected_error: str) -> dict:
    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["ok"] is False
    assert expected_error in payload["error"]
    return payload


def assert_get_endpoints_reject(client: TestClient, path: Path, expected_error: str, *, hidden_text: str = "") -> None:
    for endpoint in SPEC_DOCUMENT_GET_ENDPOINTS:
        response = client.get(endpoint, params={"path": str(path)})
        payload = assert_json_error(response, expected_error)
        if hidden_text:
            assert hidden_text not in json.dumps(payload, ensure_ascii=False)
