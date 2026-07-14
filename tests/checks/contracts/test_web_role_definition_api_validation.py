from __future__ import annotations

from http import HTTPStatus

from web_role_definition_api_test_support import (
    custom_executor_preset_payload,
    release_builder_payload,
    role_definition_client,
    unsafe_prompt_ref_payload,
)

from loopora.web_role_inputs import _normalize_role_definition_form


def test_role_definition_form_defaults_use_strategy_execution_settings_for_command_only_executor() -> None:
    form = _normalize_role_definition_form({"executor_kind": "custom"})

    assert form["executor_kind"] == "custom"
    assert form["executor_mode"] == "command"
    assert form["command_cli"] == ""


def test_api_role_definition_rejects_custom_executor_preset_mode(service_factory) -> None:
    client = role_definition_client(service_factory)

    response = client.post("/api/role-definitions", json=custom_executor_preset_payload())

    assert response.status_code == HTTPStatus.BAD_REQUEST
    payload = response.json()
    assert "only supports command mode" in payload["error"]
    _assert_asset_validation_recovery(payload, fields=["executor_mode"])


def test_api_role_definition_rejects_unsafe_prompt_ref(service_factory) -> None:
    client = role_definition_client(service_factory)

    response = client.post("/api/role-definitions", json=unsafe_prompt_ref_payload())

    assert response.status_code == HTTPStatus.BAD_REQUEST
    payload = response.json()
    assert "prompt_ref must be a safe relative path" in payload["error"]
    _assert_asset_validation_recovery(payload, fields=["prompt_ref"])


def test_api_role_definition_missing_name_returns_field_recovery(service_factory) -> None:
    client = role_definition_client(service_factory)
    payload = release_builder_payload()
    payload["name"] = "   "

    response = client.post("/api/role-definitions", json=payload)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    response_payload = response.json()
    assert response_payload["error"] == "name is required"
    _assert_asset_validation_recovery(response_payload, fields=["name"])


def _assert_asset_validation_recovery(payload: dict, *, fields: list[str]) -> None:
    action_kinds = ["fix_asset_fields", "retry_web_asset_save"]
    ready_after = {"retry_web_asset_save": "fix_asset_fields"}
    assert payload["error_code"] == "asset_validation_failed"
    assert payload["asset"] == "role_definition"
    assert [item["field"] for item in payload["field_errors"]] == fields
    assert [item["kind"] for item in payload["next_actions"]] == action_kinds
    assert payload["next_actions"][0]["fields"] == fields
    assert (
        payload["next_action_kinds"],
        payload["next_action_ready_now_kinds"],
        payload["next_action_ready_after_actions"],
        payload["next_action_blocked_kinds"],
        payload["next_action_command_blockers"],
    ) == (action_kinds, ["fix_asset_fields"], ready_after, [], {})
    summary = payload["web_asset_validation_recovery_summary"]
    assert summary["asset"] == "role_definition"
    assert summary["fields"] == fields
    assert (
        summary["next_action_kinds"],
        summary["next_action_ready_now_kinds"],
        summary["next_action_ready_after_actions"],
    ) == (action_kinds, ["fix_asset_fields"], ready_after)
