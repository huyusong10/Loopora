from __future__ import annotations

from http import HTTPStatus

from fastapi.testclient import TestClient

from loopora.web import build_app


def test_prompt_template_download_and_validation_endpoints(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    template_response = client.get("/api/prompts/templates/builder.md")
    assert template_response.status_code == HTTPStatus.OK
    markdown_text = template_response.text
    assert "archetype: builder" in markdown_text

    localized_template_response = client.get("/api/prompts/templates/builder.md?locale=zh")
    assert localized_template_response.status_code == HTTPStatus.OK
    assert "# Builder Prompt" in localized_template_response.text
    assert "archetype: builder" in localized_template_response.text

    validation_response = client.post(
        "/api/prompts/validate",
        json={
            "markdown": markdown_text,
            "archetype": "builder",
        },
    )
    assert validation_response.status_code == HTTPStatus.OK
    assert validation_response.json()["ok"] is True

    mismatch_response = client.post(
        "/api/prompts/validate",
        json={
            "markdown": markdown_text,
            "archetype": "gatekeeper",
        },
    )
    assert mismatch_response.status_code == HTTPStatus.OK
    assert mismatch_response.json()["ok"] is False
