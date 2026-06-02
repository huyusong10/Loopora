from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from web_orchestration_api_test_support import web_client


def test_api_can_create_orchestration_and_use_it_for_loop(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = web_client(service)

    orchestration_response = client.post(
        "/api/orchestrations",
        json={
            "name": "Custom Inspect First",
            "description": "Inspector before Builder.",
            "strategy_source": {"preset": "inspect_first"},
        },
    )
    assert orchestration_response.status_code == HTTPStatus.CREATED
    orchestration = orchestration_response.json()["orchestration"]
    assert orchestration["name"] == "Custom Inspect First"
    assert orchestration["workflow_json"]["preset"] == "inspect_first"

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
