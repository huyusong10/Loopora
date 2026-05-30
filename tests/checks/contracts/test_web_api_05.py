from __future__ import annotations

import json
from pathlib import Path

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
    assert create_response.status_code == 201
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

    assert update_response.status_code == 200
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
    assert create_response.status_code == 201
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

    assert update_response.status_code == 200
    orchestration = update_response.json()["orchestration"]
    assert orchestration["workflow_json"]["roles"][0]["prompt_ref"] == "builder.md"
    assert list(orchestration["prompt_files_json"].keys()) == ["builder.md"]
    assert "custom-builder.md" not in orchestration["prompt_files_json"]

def test_api_orchestration_rejects_shared_prompt_ref_with_mismatched_archetype(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/orchestrations",
        json={
            "name": "Shared Prompt Ref Mismatch",
            "description": "Should fail when one prompt ref is reused across incompatible archetypes.",
            "workflow": {
                "version": 1,
                "roles": [
                    {"id": "builder", "archetype": "builder", "prompt_ref": "shared.md"},
                    {"id": "inspector", "archetype": "inspector", "prompt_ref": "shared.md"},
                ],
                "steps": [
                    {"id": "builder_step", "role_id": "builder"},
                    {"id": "inspector_step", "role_id": "inspector"},
                ],
            },
            "prompt_files": {
                "shared.md": """---
version: 1
archetype: builder
---

Keep the builder prompt stable.
""",
            },
        },
    )

    assert response.status_code == 400
    assert "prompt archetype builder does not match expected archetype inspector" in response.json()["error"]

def test_api_orchestration_rejects_unsafe_prompt_ref_paths(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/orchestrations",
        json={
            "name": "Unsafe Prompt Ref",
            "description": "Should fail when a prompt ref escapes the asset root.",
            "workflow": {
                "version": 1,
                "roles": [
                    {"id": "builder", "archetype": "builder", "prompt_ref": "../escape.md"},
                ],
                "steps": [
                    {"id": "builder_step", "role_id": "builder"},
                ],
            },
            "prompt_files": {
                "../escape.md": """---
version: 1
archetype: builder
---

This should never be written outside prompts/.
""",
            },
        },
    )

    assert response.status_code == 400
    assert "prompt_ref must be a safe relative path" in response.json()["error"]

def test_api_orchestration_rejects_invalid_prompt_file_keys(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/orchestrations",
        json={
            "name": "Unsafe Prompt Files",
            "description": "Should reject invalid prompt_files keys instead of ignoring them.",
            "workflow": {
                "version": 1,
                "roles": [
                    {"id": "builder", "archetype": "builder", "prompt_ref": "builder.md"},
                ],
                "steps": [
                    {"id": "builder_step", "role_id": "builder"},
                ],
            },
            "prompt_files": {
                "../escape.md": """---
version: 1
archetype: builder
---

This key should be rejected instead of silently dropped.
""",
            },
        },
    )

    assert response.status_code == 400
    assert "prompt_ref must be a safe relative path" in response.json()["error"]

def test_api_get_orchestration_sanitizes_invalid_persisted_prompt_file_keys(service_factory) -> None:
    service = service_factory(scenario="success")
    service.repository.create_orchestration(
        {
            "id": "orch_legacy",
            "name": "Legacy Builder Flow",
            "description": "Contains stale invalid prompt file keys.",
            "workflow": {
                "version": 1,
                "roles": [
                    {"id": "builder", "archetype": "builder", "prompt_ref": "builder.md"},
                ],
                "steps": [
                    {"id": "builder_step", "role_id": "builder"},
                ],
            },
            "prompt_files": {
                "../escape.md": """---
version: 1
archetype: builder
---

Legacy invalid key.
""",
                "builder.md": """---
version: 1
archetype: builder
---

Legit builder prompt.
""",
            },
        }
    )
    client = TestClient(build_app(service=service))

    response = client.get("/api/orchestrations/orch_legacy")

    assert response.status_code == 200
    orchestration = response.json()
    assert list(orchestration["prompt_files_json"].keys()) == ["builder.md"]

def test_builtin_orchestration_form_route_is_read_only(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    builtin = service.get_orchestration("builtin:build_first")
    custom_before = [item for item in service.list_orchestrations() if item["source"] == "custom"]

    response = client.post(
        "/orchestrations/builtin:build_first/edit",
        data={
            "name": "Attempted Custom Copy",
            "description": "Should not be created from the built-in edit route.",
            "workflow_preset": "build_first",
            "workflow_json": json.dumps(builtin["workflow_json"], ensure_ascii=False),
            "prompt_files_json": json.dumps(builtin["prompt_files_json"], ensure_ascii=False),
        },
    )

    assert response.status_code == 200
    assert "built-in orchestrations are read-only" in response.text
    custom_after = [item for item in service.list_orchestrations() if item["source"] == "custom"]
    assert custom_after == custom_before

def test_blank_orchestration_form_does_not_fall_back_to_build_first(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/orchestrations/new",
        data={
            "name": "Blank Starter",
            "description": "Should stay blank until steps are added.",
            "workflow_json": json.dumps({"version": 1, "preset": "", "roles": [], "steps": []}, ensure_ascii=False),
            "prompt_files_json": json.dumps({}, ensure_ascii=False),
        },
    )

    assert response.status_code == 200
    assert "workflow requires at least one role" in response.text
    custom_records = [item for item in service.list_orchestrations() if item["source"] == "custom"]
    assert custom_records == []

def test_api_can_create_round_based_loop_without_gatekeeper(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/loops",
        json={
            "name": "Round Builder Loop",
            "spec_path": str(sample_spec_file),
            "workdir": str(sample_workdir),
            "executor_kind": "codex",
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
            "completion_mode": "rounds",
            "iteration_interval_seconds": 0.1,
            "max_iters": 2,
            "max_role_retries": 1,
            "delta_threshold": 0.005,
            "trigger_window": 2,
            "regression_window": 2,
            "strategy_source": {
                "version": 1,
                "roles": [
                    {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
                ],
                "steps": [
                    {"id": "builder_step", "role_id": "builder"},
                ],
            },
            "start_immediately": False,
        },
    )

    assert response.status_code == 201
    loop = response.json()["loop"]
    assert loop["completion_mode"] == "rounds"
    assert loop["iteration_interval_seconds"] == 0.1
    assert loop["workflow_json"]["steps"][0]["role_id"] == "builder"

def test_api_rejects_gatekeeper_mode_without_finish_gatekeeper(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/loops",
        json={
            "name": "Invalid Gate Loop",
            "spec_path": str(sample_spec_file),
            "workdir": str(sample_workdir),
            "executor_kind": "codex",
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
            "completion_mode": "gatekeeper",
            "max_iters": 2,
            "max_role_retries": 1,
            "delta_threshold": 0.005,
            "trigger_window": 2,
            "regression_window": 2,
            "workflow": {
                "version": 1,
                "roles": [
                    {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
                ],
                "steps": [
                    {"id": "builder_step", "role_id": "builder"},
                ],
            },
            "start_immediately": False,
        },
    )

    assert response.status_code == 400
    assert "gatekeeper completion mode" in response.json()["error"]

def test_api_rejects_duplicate_workflow_step_ids(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/loops",
        json={
            "name": "Duplicate Step Loop",
            "spec_path": str(sample_spec_file),
            "workdir": str(sample_workdir),
            "executor_kind": "codex",
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
            "completion_mode": "rounds",
            "max_iters": 2,
            "max_role_retries": 1,
            "delta_threshold": 0.005,
            "trigger_window": 2,
            "regression_window": 2,
            "workflow": {
                "version": 1,
                "roles": [
                    {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
                    {"id": "inspector", "name": "Inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
                ],
                "steps": [
                    {"id": "shared_step", "role_id": "builder"},
                    {"id": "shared_step", "role_id": "inspector"},
                ],
            },
            "start_immediately": False,
        },
    )

    assert response.status_code == 400
    assert "duplicate workflow step id" in response.json()["error"]

def test_api_normalizes_boolean_like_workflow_step_session_flags(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/loops",
        json={
            "name": "Session Flag Loop",
            "spec_path": str(sample_spec_file),
            "workdir": str(sample_workdir),
            "executor_kind": "codex",
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
            "completion_mode": "rounds",
            "max_iters": 2,
            "max_role_retries": 1,
            "delta_threshold": 0.005,
            "trigger_window": 2,
            "regression_window": 2,
            "workflow": {
                "version": 1,
                "roles": [
                    {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
                    {"id": "inspector", "name": "Inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
                ],
                "steps": [
                    {"id": "builder_step", "role_id": "builder", "inherit_session": "false"},
                    {"id": "inspector_step", "role_id": "inspector", "inherit_session": "true"},
                ],
            },
            "start_immediately": False,
        },
    )

    assert response.status_code == 201
    steps = response.json()["loop"]["workflow_json"]["steps"]
    assert steps[0]["inherit_session"] is False
    assert steps[1]["inherit_session"] is True

def test_api_rejects_invalid_workflow_step_session_flag(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/loops",
        json={
            "name": "Invalid Session Flag Loop",
            "spec_path": str(sample_spec_file),
            "workdir": str(sample_workdir),
            "executor_kind": "codex",
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
            "completion_mode": "rounds",
            "max_iters": 2,
            "max_role_retries": 1,
            "delta_threshold": 0.005,
            "trigger_window": 2,
            "regression_window": 2,
            "workflow": {
                "version": 1,
                "roles": [
                    {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
                ],
                "steps": [
                    {"id": "builder_step", "role_id": "builder", "inherit_session": "sometimes"},
                ],
            },
            "start_immediately": False,
        },
    )

    assert response.status_code == 400
    assert "inherit_session must be a boolean" in response.json()["error"]

def test_api_rejects_finish_run_for_non_gatekeeper_steps(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/loops",
        json={
            "name": "Invalid On Pass Loop",
            "spec_path": str(sample_spec_file),
            "workdir": str(sample_workdir),
            "executor_kind": "codex",
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
            "completion_mode": "rounds",
            "max_iters": 2,
            "max_role_retries": 1,
            "delta_threshold": 0.005,
            "trigger_window": 2,
            "regression_window": 2,
            "workflow": {
                "version": 1,
                "roles": [
                    {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
                ],
                "steps": [
                    {"id": "builder_step", "role_id": "builder", "on_pass": "finish_run"},
                ],
            },
            "start_immediately": False,
        },
    )

    assert response.status_code == 400
    assert "non-gatekeeper steps only support on_pass=continue" in response.json()["error"]

def test_api_role_definition_crud(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    create_response = client.post(
        "/api/role-definitions",
        json={
            "name": "Release Builder",
            "description": "Ship focused release changes.",
            "posture_notes": "Prefer maintainability evidence before calling this ready.",
            "archetype": "builder",
            "prompt_markdown": """---
version: 1
archetype: builder
---

Focus on scoped release work.
""",
            "executor_kind": "claude",
            "executor_mode": "preset",
            "model": "",
            "reasoning_effort": "high",
        },
    )
    assert create_response.status_code == 201
    role_definition = create_response.json()["role_definition"]
    assert role_definition["name"] == "Release Builder"
    assert role_definition["archetype"] == "builder"
    assert role_definition["executor_kind"] == "claude"
    assert role_definition["reasoning_effort"] == "high"
    assert role_definition["posture_notes"] == "Prefer maintainability evidence before calling this ready."
    assert role_definition["prompt_ref"].endswith(".md")
    generated_prompt_ref = role_definition["prompt_ref"]

    list_response = client.get("/api/role-definitions")
    assert list_response.status_code == 200
    assert any(item["id"] == role_definition["id"] for item in list_response.json())

    update_response = client.put(
        f"/api/role-definitions/{role_definition['id']}",
        json={
            "name": "Release Builder v2",
            "description": "Updated role definition.",
            "posture_notes": "Tighten the evidence bar for refactors.",
            "archetype": "builder",
            "prompt_markdown": """---
version: 1
archetype: builder
---

Focus on scoped release work with tighter release constraints.
""",
            "executor_kind": "codex",
            "executor_mode": "command",
            "command_cli": "codex",
            "command_args_text": "\n".join(
                [
                    "exec",
                    "--json",
                    "--cd",
                    "{workdir}",
                    "--output-schema",
                    "{schema_path}",
                    "--output-last-message",
                    "{output_path}",
                    "{prompt}",
                ]
            ),
            "model": "gpt-5.4",
            "reasoning_effort": "",
        },
    )
    assert update_response.status_code == 200
    updated_role_definition = update_response.json()["role_definition"]
    assert updated_role_definition["name"] == "Release Builder v2"
    assert updated_role_definition["executor_mode"] == "command"
    assert updated_role_definition["model"] == "gpt-5.4"
    assert updated_role_definition["posture_notes"] == "Tighten the evidence bar for refactors."
    assert updated_role_definition["prompt_ref"] == generated_prompt_ref

    invalid_update_response = client.put(
        f"/api/role-definitions/{role_definition['id']}",
        json={
            "name": "Release Inspector",
            "description": "Should fail.",
            "archetype": "inspector",
            "prompt_markdown": """---
version: 1
archetype: inspector
---

Inspect release work instead.
""",
            "executor_kind": "codex",
            "executor_mode": "preset",
            "model": "",
            "reasoning_effort": "medium",
        },
    )
    assert invalid_update_response.status_code == 400
    assert "saved role definitions cannot change archetype" in invalid_update_response.json()["error"]

    delete_response = client.delete(f"/api/role-definitions/{role_definition['id']}")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True
