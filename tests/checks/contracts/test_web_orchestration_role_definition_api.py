from __future__ import annotations

from http import HTTPStatus

from web_orchestration_api_test_support import (
    RELEASE_BUILDER_PROMPT,
    create_release_builder_role_definition,
    role_definition_snapshot_workflow,
    web_client,
)


def test_api_orchestration_hydrates_role_snapshots_from_role_definition_id(service_factory) -> None:
    service = service_factory(scenario="success")
    role_definition = create_release_builder_role_definition(service)
    client = web_client(service)

    response = client.post(
        "/api/orchestrations",
        json={
            "name": "Uses Role Definition Snapshot",
            "description": "Hydrates missing role fields from a role definition.",
            "workflow": role_definition_snapshot_workflow(role_definition["id"]),
        },
    )

    assert response.status_code == HTTPStatus.CREATED
    orchestration = response.json()["orchestration"]
    builder_role = orchestration["workflow_json"]["roles"][0]
    assert builder_role["name"] == "Release Builder"
    assert builder_role["prompt_ref"] == "release-builder.md"
    assert builder_role["executor_kind"] == "claude"
    assert builder_role["model"] == "gpt-5.4-mini"
    assert orchestration["prompt_files_json"]["release-builder.md"].startswith("---\nversion: 1")


def test_api_orchestration_rejects_unknown_role_definition_ids(service_factory) -> None:
    service = service_factory(scenario="success")
    client = web_client(service)

    response = client.post(
        "/api/orchestrations",
        json={
            "name": "Broken Role Definition Reference",
            "description": "Should fail fast.",
            "workflow": role_definition_snapshot_workflow("role_missing"),
        },
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "unknown role definition: role_missing" in response.json()["error"]


def test_api_orchestration_rejects_conflicting_role_definition_snapshot_fields(service_factory) -> None:
    service = service_factory(scenario="success")
    role_definition = create_release_builder_role_definition(service)
    client = web_client(service)

    response = client.post(
        "/api/orchestrations",
        json={
            "name": "Conflicting Role Snapshot",
            "description": "Should fail when snapshot fields conflict with the role definition.",
            "workflow": role_definition_snapshot_workflow(
                role_definition["id"],
                role_updates={"model": "gpt-5.4"},
            ),
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert f"conflicts with role_definition_id {role_definition['id']} on model" in response.json()["error"]


def test_api_orchestration_rejects_conflicting_prompt_files_for_role_definition_id(service_factory) -> None:
    service = service_factory(scenario="success")
    role_definition = create_release_builder_role_definition(service)
    client = web_client(service)

    response = client.post(
        "/api/orchestrations",
        json={
            "name": "Conflicting Role Prompt Snapshot",
            "description": "Should fail when prompt_files override a role definition prompt.",
            "workflow": role_definition_snapshot_workflow(role_definition["id"]),
            "prompt_files": {
                "release-builder.md": RELEASE_BUILDER_PROMPT.replace("safe release work", "risky release work"),
            },
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert f"conflicts with role_definition_id {role_definition['id']} on prompt_markdown" in response.json()["error"]
