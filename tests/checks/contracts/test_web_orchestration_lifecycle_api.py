from __future__ import annotations

from http import HTTPStatus
import json
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

from web_orchestration_api_test_support import web_client


def test_api_can_create_orchestration_and_use_it_for_loop(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = web_client(service)

    encoded_workdir = quote(str(sample_workdir), safe="")
    orchestration_response = client.post(
        f"/api/orchestrations?workdir={encoded_workdir}",
        json={
            "name": "Custom Inspect First",
            "description": "Inspector before Builder.",
            "strategy_source": {"preset": "inspect_first"},
        },
    )
    assert orchestration_response.status_code == HTTPStatus.CREATED
    orchestration_payload = orchestration_response.json()
    orchestration = orchestration_payload["orchestration"]
    assert orchestration["name"] == "Custom Inspect First"
    assert orchestration["workflow_json"]["preset"] == "inspect_first"
    redirect_parts = urlsplit(orchestration_payload["redirect_url"])
    assert redirect_parts.path == f"/orchestrations/{orchestration['id']}/edit"
    assert parse_qs(redirect_parts.query).get("workdir") == [str(sample_workdir)]

    list_response = client.get("/api/orchestrations")
    assert list_response.status_code == HTTPStatus.OK
    assert any(item["id"] == orchestration["id"] for item in list_response.json())

    update_response = client.put(
        f"/api/orchestrations/{orchestration['id']}",
        json={
            "name": "Custom Build First",
            "description": "Updated description.",
            "strategy_source": {"preset": "build_first"},
        },
    )
    assert update_response.status_code == HTTPStatus.OK
    updated_orchestration = update_response.json()["orchestration"]
    assert updated_orchestration["name"] == "Custom Build First"
    assert updated_orchestration["workflow_json"]["preset"] == "build_first"

    loop_response = client.post(
        "/api/loops",
        json={
            "name": "Uses Custom Orchestration",
            "spec_path": str(sample_spec_file),
            "workdir": str(sample_workdir),
            "orchestration_id": updated_orchestration["id"],
            "executor_kind": "codex",
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
            "max_iters": 3,
            "max_role_retries": 1,
            "delta_threshold": 0.005,
            "trigger_window": 2,
            "regression_window": 2,
            "start_immediately": False,
        },
    )
    assert loop_response.status_code == HTTPStatus.CREATED
    loop = loop_response.json()["loop"]
    assert loop["orchestration"]["id"] == updated_orchestration["id"]
    assert loop["orchestration"]["name"] == "Custom Build First"
    assert loop["strategy_source"] == loop["workflow_json"]
    assert loop["workflow_json"]["preset"] == "build_first"


def test_api_orchestration_create_redacts_low_level_storage_errors(monkeypatch, service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    client = web_client(service)
    local_path = tmp_path / "private" / "orchestrations.db"

    def fail_create_orchestration(**_kwargs):
        raise OSError(f"permission denied: {local_path}")

    monkeypatch.setattr(service, "create_orchestration", fail_create_orchestration)

    response = client.post(
        "/api/orchestrations",
        json={
            "name": "Custom Inspect First",
            "strategy_source": {"preset": "inspect_first"},
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    payload = response.json()
    assert payload["error"] == "orchestration could not be saved"
    assert "error_code" not in payload
    assert "permission denied" not in response.text
    assert str(local_path) not in response.text


def test_api_orchestration_invalid_strategy_json_returns_field_recovery(service_factory) -> None:
    service = service_factory(scenario="success")
    client = web_client(service)

    response = client.post(
        "/api/orchestrations",
        json={
            "name": "Broken JSON Flow",
            "strategy_json": '{"roles": [',
            "prompt_files_json": json.dumps({}),
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    payload = response.json()
    assert payload["error"] == "strategy_json must be valid JSON"
    _assert_orchestration_validation_recovery(payload, fields=["strategy_json"])


def _assert_orchestration_validation_recovery(payload: dict, *, fields: list[str]) -> None:
    action_kinds = ["fix_asset_fields", "retry_web_asset_save"]
    ready_after = {"retry_web_asset_save": "fix_asset_fields"}
    assert payload["error_code"] == "asset_validation_failed"
    assert payload["asset"] == "orchestration"
    assert [item["field"] for item in payload["field_errors"]] == fields
    assert [item["kind"] for item in payload["next_actions"]] == action_kinds
    assert payload["next_actions"][0]["target"] == "web_orchestration_editor"
    assert payload["next_actions"][0]["fields"] == fields
    assert (
        payload["next_action_kinds"],
        payload["next_action_ready_now_kinds"],
        payload["next_action_ready_after_actions"],
        payload["next_action_blocked_kinds"],
        payload["next_action_command_blockers"],
    ) == (action_kinds, ["fix_asset_fields"], ready_after, [], {})
    summary = payload["web_asset_validation_recovery_summary"]
    assert summary["asset"] == "orchestration"
    assert summary["fields"] == fields
    assert (
        summary["next_action_kinds"],
        summary["next_action_ready_now_kinds"],
        summary["next_action_ready_after_actions"],
    ) == (action_kinds, ["fix_asset_fields"], ready_after)
