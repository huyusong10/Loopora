from __future__ import annotations

from http import HTTPStatus

from web_role_definition_api_test_support import (
    archetype_change_payload,
    release_builder_payload,
    role_definition_client,
    updated_release_builder_payload,
)


def test_api_role_definition_crud(service_factory) -> None:
    client = role_definition_client(service_factory)

    create_response = client.post("/api/role-definitions", json=release_builder_payload())
    assert create_response.status_code == HTTPStatus.CREATED
    role_definition = create_response.json()["role_definition"]
    assert role_definition["name"] == "Release Builder"
    assert role_definition["archetype"] == "builder"
    assert role_definition["executor_kind"] == "claude"
    assert role_definition["reasoning_effort"] == "high"
    assert role_definition["posture_notes"] == "Prefer maintainability evidence before calling this ready."
    assert role_definition["prompt_ref"].endswith(".md")
    generated_prompt_ref = role_definition["prompt_ref"]

    list_response = client.get("/api/role-definitions")
    assert list_response.status_code == HTTPStatus.OK
    assert any(item["id"] == role_definition["id"] for item in list_response.json())

    update_response = client.put(
        f"/api/role-definitions/{role_definition['id']}",
        json=updated_release_builder_payload(),
    )
    assert update_response.status_code == HTTPStatus.OK
    updated_role_definition = update_response.json()["role_definition"]
    assert updated_role_definition["name"] == "Release Builder v2"
    assert updated_role_definition["executor_mode"] == "command"
    assert updated_role_definition["model"] == "gpt-5.4"
    assert updated_role_definition["posture_notes"] == "Tighten the evidence bar for refactors."
    assert updated_role_definition["prompt_ref"] == generated_prompt_ref

    invalid_update_response = client.put(
        f"/api/role-definitions/{role_definition['id']}",
        json=archetype_change_payload(),
    )
    assert invalid_update_response.status_code == HTTPStatus.BAD_REQUEST
    assert "saved role definitions cannot change archetype" in invalid_update_response.json()["error"]

    delete_response = client.delete(f"/api/role-definitions/{role_definition['id']}")
    assert delete_response.status_code == HTTPStatus.OK
    assert delete_response.json()["deleted"] is True
