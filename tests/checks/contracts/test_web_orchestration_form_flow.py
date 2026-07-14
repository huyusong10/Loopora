from __future__ import annotations

import json
from http import HTTPStatus

from fastapi.testclient import TestClient

from loopora.web import build_app


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

    assert response.status_code == HTTPStatus.OK
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

    assert response.status_code == HTTPStatus.OK
    assert "workflow requires at least one role" in response.text
    _assert_form_field_recovery(response.text, "strategy_json", id_prefix="orchestration-field-recovery")
    custom_records = [item for item in service.list_orchestrations() if item["source"] == "custom"]
    assert custom_records == []


def test_orchestration_form_save_redacts_low_level_storage_errors(service_factory, monkeypatch, tmp_path) -> None:
    service = service_factory(scenario="success")
    local_path = tmp_path / "loopora.sqlite"

    def fail_create_orchestration(*_args, **_kwargs):
        raise OSError(f"permission denied: {local_path}")

    monkeypatch.setattr(service, "create_orchestration", fail_create_orchestration)
    client = TestClient(build_app(service=service))

    response = client.post(
        "/orchestrations/new",
        data={
            "name": "Custom Inspect First",
            "description": "Inspector before Builder.",
            "strategy_json": json.dumps({"version": 1, "preset": "inspect_first"}, ensure_ascii=False),
            "prompt_files_json": json.dumps({}, ensure_ascii=False),
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert "orchestration could not be saved" in response.text
    assert "Custom Inspect First" in response.text
    assert str(local_path) not in response.text
    assert "permission denied" not in response.text
    assert "data-asset-field-recovery" not in response.text


def test_role_definition_form_validation_renders_field_recovery(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/roles/new",
        data={
            "name": " ",
            "description": "Ship focused release work.",
            "posture_notes": "Prefer maintainability evidence.",
            "archetype": "builder",
            "prompt_markdown": "---\nversion: 1\narchetype: builder\n---\n\nFocus on safe release work.\n",
            "executor_kind": "codex",
            "executor_mode": "preset",
            "model": "gpt-5.4-mini",
            "reasoning_effort": "medium",
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert "name is required" in response.text
    _assert_form_field_recovery(response.text, "name", id_prefix="role-definition-field-recovery")


def test_role_definition_form_submits_custom_command_mode_without_browser_enhancement(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/roles/new",
        data={
            "name": "Custom Shell Reviewer",
            "description": "Run a local wrapper as a role.",
            "posture_notes": "Keep the wrapper result structured.",
            "archetype": "custom",
            "prompt_markdown": "---\nversion: 1\narchetype: custom\n---\n\nReview with a local command.\n",
            "executor_kind": "custom",
            "executor_mode": "command",
            "command_cli": "local-wrapper",
            "command_args_text": "--output\n{output_path}\n{prompt}\n",
            "model": "",
            "reasoning_effort": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == HTTPStatus.SEE_OTHER
    created = [
        item
        for item in service.list_role_definitions()
        if item.get("source") == "custom" and item.get("name") == "Custom Shell Reviewer"
    ]
    assert len(created) == 1
    assert created[0]["executor_kind"] == "custom"
    assert created[0]["executor_mode"] == "command"
    assert created[0]["command_cli"] == "local-wrapper"
    assert "{output_path}" in created[0]["command_args_text"]


def test_role_definition_form_custom_preset_error_recovers_mode_control(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/roles/new",
        data={
            "name": "Custom Preset Reviewer",
            "description": "Should recover at the mode control.",
            "posture_notes": "Keep the wrapper result structured.",
            "archetype": "custom",
            "prompt_markdown": "---\nversion: 1\narchetype: custom\n---\n\nReview with a local command.\n",
            "executor_kind": "custom",
            "executor_mode": "preset",
            "command_cli": "local-wrapper",
            "command_args_text": "--output\n{output_path}\n{prompt}\n",
            "model": "",
            "reasoning_effort": "",
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert "only supports command mode" in response.text
    assert 'name="executor_mode"' in response.text
    assert 'data-testid="role-definition-mode-command-input"' in response.text
    _assert_form_field_recovery(response.text, "executor_mode", id_prefix="role-definition-field-recovery")


def test_role_definition_form_save_redacts_low_level_storage_errors(service_factory, monkeypatch, tmp_path) -> None:
    service = service_factory(scenario="success")
    local_path = tmp_path / "loopora.sqlite"

    def fail_create_role_definition(*_args, **_kwargs):
        raise OSError(f"permission denied: {local_path}")

    monkeypatch.setattr(service, "create_role_definition", fail_create_role_definition)
    client = TestClient(build_app(service=service))

    response = client.post(
        "/roles/new",
        data={
            "name": "Release Builder",
            "description": "Ship focused release work.",
            "posture_notes": "Prefer maintainability evidence.",
            "archetype": "builder",
            "prompt_ref": "release-builder.md",
            "prompt_markdown": "---\nversion: 1\narchetype: builder\n---\n\nFocus on safe release work.\n",
            "executor_kind": "codex",
            "executor_mode": "preset",
            "model": "gpt-5.4-mini",
            "reasoning_effort": "medium",
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert "role definition could not be saved" in response.text
    assert "Release Builder" in response.text
    assert str(local_path) not in response.text
    assert "permission denied" not in response.text
    assert "data-asset-field-recovery" not in response.text


def _assert_form_field_recovery(response_text: str, field: str, *, id_prefix: str) -> None:
    note_id = f"{id_prefix}-{field.replace('_', '-')}-0"
    assert "data-asset-field-recovery-list" in response_text
    assert f'id="{note_id}"' in response_text
    assert f'data-asset-field-recovery-for="{field}"' in response_text
    assert 'aria-invalid="true"' in response_text
    assert f'aria-describedby="{note_id}"' in response_text
