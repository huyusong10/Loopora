from __future__ import annotations

from http import HTTPStatus

from fastapi.testclient import TestClient

from loopora.web import build_app


def test_api_json_endpoints_reject_invalid_json_body(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/markdown/render",
        content="{",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "invalid JSON body" in response.json()["error"]

    invalid_utf8_response = client.post(
        "/api/markdown/render",
        content=b'{"markdown":"\xff"}',
        headers={"content-type": "application/json"},
    )

    assert invalid_utf8_response.status_code == HTTPStatus.BAD_REQUEST
    assert "invalid JSON body" in invalid_utf8_response.json()["error"]
    assert "UTF-8" in invalid_utf8_response.json()["error"]


def test_api_json_endpoints_require_object_bodies(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post("/api/markdown/render", json=["not", "an", "object"])

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()["error"] == "request body must be a JSON object"


def test_api_markdown_render_can_strip_prompt_front_matter(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/markdown/render",
        json={
            "markdown": "---\nversion: 1\narchetype: builder\n---\n\n# Prompt Body\n\nShip the change.\n",
            "strip_front_matter": True,
        },
    )

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["ok"] is True
    assert "<h1>Prompt Body</h1>" in payload["rendered_html"]
    assert "version: 1" not in payload["rendered_html"]
    assert "archetype: builder" not in payload["rendered_html"]
    assert "Ship the change." in payload["rendered_html"]
