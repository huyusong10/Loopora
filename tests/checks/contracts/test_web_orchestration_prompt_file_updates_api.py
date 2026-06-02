from __future__ import annotations

import json
from http import HTTPStatus

from fastapi.testclient import TestClient

from loopora.web import build_app


def test_api_orchestration_update_preserves_existing_prompt_files_when_omitted(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    create_response = client.post(
        "/api/orchestrations",
        json={
            "name": "Custom Builder Flow",
            "description": "Uses a custom builder prompt.",
            "strategy_source": {
                "version": 1,
                "roles": [
                    {"id": "builder", "archetype": "builder", "prompt_ref": "custom-builder.md"},
                ],
                "steps": [
                    {"id": "builder_step", "role_id": "builder"},
                ],
            },
            "prompt_files": {
                "custom-builder.md": """---
version: 1
archetype: builder
---

Keep the builder prompt stable.
""",
            },
        },
    )
    assert create_response.status_code == HTTPStatus.CREATED
    orchestration_id = create_response.json()["orchestration"]["id"]

    update_response = client.put(
        f"/api/orchestrations/{orchestration_id}",
        json={
            "name": "Custom Builder Flow v2",
            "description": "Workflow changed, prompt payload omitted.",
            "strategy_json": json.dumps(
                {
                    "version": 1,
                    "roles": [
                        {"id": "builder", "archetype": "builder", "prompt_ref": "custom-builder.md"},
                    ],
                    "steps": [
                        {"id": "builder_retry_step", "role_id": "builder"},
                    ],
                },
                ensure_ascii=False,
            ),
        },
    )

    assert update_response.status_code == HTTPStatus.OK
    orchestration = update_response.json()["orchestration"]
    assert orchestration["name"] == "Custom Builder Flow v2"
    assert orchestration["workflow_json"]["steps"][0]["id"] == "builder_retry_step"
    assert orchestration["prompt_files_json"]["custom-builder.md"].startswith("---\nversion: 1")


def test_api_orchestration_update_prunes_unused_prompt_files(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    create_response = client.post(
        "/api/orchestrations",
        json={
            "name": "Custom Builder Flow",
            "description": "Uses a custom builder prompt.",
            "workflow": {
                "version": 1,
                "roles": [
                    {"id": "builder", "archetype": "builder", "prompt_ref": "custom-builder.md"},
                ],
                "steps": [
                    {"id": "builder_step", "role_id": "builder"},
                ],
            },
            "prompt_files": {
                "custom-builder.md": """---
version: 1
archetype: builder
---

Keep the builder prompt stable.
""",
            },
        },
    )
    assert create_response.status_code == HTTPStatus.CREATED
    orchestration_id = create_response.json()["orchestration"]["id"]

    update_response = client.put(
        f"/api/orchestrations/{orchestration_id}",
        json={
            "name": "Builtin Builder Flow",
            "description": "Now uses the built-in builder prompt.",
            "workflow": {
                "version": 1,
                "roles": [
                    {"id": "builder", "archetype": "builder", "prompt_ref": "builder.md"},
                ],
                "steps": [
                    {"id": "builder_step", "role_id": "builder"},
                ],
            },
        },
    )

    assert update_response.status_code == HTTPStatus.OK
    orchestration = update_response.json()["orchestration"]
    assert orchestration["workflow_json"]["roles"][0]["prompt_ref"] == "builder.md"
    assert list(orchestration["prompt_files_json"].keys()) == ["builder.md"]
    assert "custom-builder.md" not in orchestration["prompt_files_json"]
