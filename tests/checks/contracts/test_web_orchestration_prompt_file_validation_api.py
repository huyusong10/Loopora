from __future__ import annotations

from http import HTTPStatus

import pytest

from web_orchestration_api_test_support import web_client


def prompt_markdown(archetype: str, body: str) -> str:
    return f"""---
version: 1
archetype: {archetype}
---

{body}
"""


def role(role_id: str, archetype: str, prompt_ref: str) -> dict:
    return {"id": role_id, "archetype": archetype, "prompt_ref": prompt_ref}


def workflow_with_roles(*roles: dict) -> dict:
    return {
        "version": 1,
        "roles": list(roles),
        "steps": [{"id": f"{item['id']}_step", "role_id": item["id"]} for item in roles],
    }


def builder_workflow(prompt_ref: str) -> dict:
    return workflow_with_roles(role("builder", "builder", prompt_ref))


def orchestration_payload(*, name: str, workflow: dict, prompt_files: dict[str, str]) -> dict:
    return {
        "name": name,
        "description": "Exercises prompt file validation.",
        "workflow": workflow,
        "prompt_files": prompt_files,
    }


INVALID_PROMPT_FILE_CASES = [
    pytest.param(
        orchestration_payload(
            name="Shared Prompt Ref Mismatch",
            workflow=workflow_with_roles(
                role("builder", "builder", "shared.md"),
                role("inspector", "inspector", "shared.md"),
            ),
            prompt_files={"shared.md": prompt_markdown("builder", "Keep the builder prompt stable.")},
        ),
        "prompt archetype builder does not match expected archetype inspector",
        id="shared-ref-mismatched-archetype",
    ),
    pytest.param(
        orchestration_payload(
            name="Unsafe Prompt Ref",
            workflow=builder_workflow("../escape.md"),
            prompt_files={
                "../escape.md": prompt_markdown("builder", "This should never be written outside prompts/."),
            },
        ),
        "prompt_ref must be a safe relative path",
        id="unsafe-role-prompt-ref",
    ),
    pytest.param(
        orchestration_payload(
            name="Unsafe Prompt Files",
            workflow=builder_workflow("builder.md"),
            prompt_files={
                "../escape.md": prompt_markdown("builder", "This key should be rejected instead of silently dropped."),
            },
        ),
        "prompt_ref must be a safe relative path",
        id="unsafe-prompt-file-key",
    ),
]


@pytest.mark.parametrize(("payload", "error_message"), INVALID_PROMPT_FILE_CASES)
def test_api_orchestration_rejects_invalid_prompt_file_payloads(service_factory, payload: dict, error_message: str) -> None:
    client = web_client(service_factory(scenario="success"))

    response = client.post("/api/orchestrations", json=payload)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    response_payload = response.json()
    assert error_message in response_payload["error"]
    assert response_payload["error_code"] == "asset_validation_failed"
    fields = [item["field"] for item in response_payload["field_errors"]]
    assert "prompt_files_json" in fields
    assert response_payload["next_actions"][0]["fields"] == fields


def test_api_get_orchestration_sanitizes_invalid_persisted_prompt_file_keys(service_factory) -> None:
    service = service_factory(scenario="success")
    service.repository.create_orchestration(
        {
            "id": "orch_legacy",
            **orchestration_payload(
                name="Legacy Builder Flow",
                workflow=builder_workflow("builder.md"),
                prompt_files={
                    "../escape.md": prompt_markdown("builder", "Legacy invalid key."),
                    "builder.md": prompt_markdown("builder", "Legit builder prompt."),
                },
            ),
        }
    )
    client = web_client(service)

    response = client.get("/api/orchestrations/orch_legacy")

    assert response.status_code == HTTPStatus.OK
    orchestration = response.json()
    assert list(orchestration["prompt_files_json"].keys()) == ["builder.md"]
