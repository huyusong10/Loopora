from __future__ import annotations

from http import HTTPStatus

from web_role_definition_api_test_support import (
    custom_executor_preset_payload,
    role_definition_client,
    unsafe_prompt_ref_payload,
)


def test_api_role_definition_rejects_custom_executor_preset_mode(service_factory) -> None:
    client = role_definition_client(service_factory)

    response = client.post("/api/role-definitions", json=custom_executor_preset_payload())

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "only supports command mode" in response.json()["error"]


def test_api_role_definition_rejects_unsafe_prompt_ref(service_factory) -> None:
    client = role_definition_client(service_factory)

    response = client.post("/api/role-definitions", json=unsafe_prompt_ref_payload())

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "prompt_ref must be a safe relative path" in response.json()["error"]
