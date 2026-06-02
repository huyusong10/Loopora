from __future__ import annotations

from fastapi.testclient import TestClient

from loopora.web import build_app


RELEASE_BUILDER_PROMPT = """---
version: 1
archetype: builder
---

Focus on safe release work.
"""


def web_client(service) -> TestClient:
    return TestClient(build_app(service=service))


def create_release_builder_role_definition(service) -> dict:
    return service.create_role_definition(
        name="Release Builder",
        description="Ships focused release work.",
        archetype="builder",
        prompt_ref="release-builder.md",
        prompt_markdown=RELEASE_BUILDER_PROMPT,
        executor_kind="claude",
        executor_mode="preset",
        model="gpt-5.4-mini",
        reasoning_effort="high",
    )


def role_definition_snapshot_workflow(role_definition_id: str, *, role_updates: dict | None = None) -> dict:
    role = {"id": "builder", "role_definition_id": role_definition_id}
    if role_updates:
        role.update(role_updates)
    return {
        "version": 1,
        "roles": [role],
        "steps": [
            {"id": "builder_step", "role_id": "builder"},
        ],
    }
