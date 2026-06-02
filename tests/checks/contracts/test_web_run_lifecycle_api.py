from __future__ import annotations

import time
from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.web import build_app

from web_api_test_support import _start_agent_first_loop


def test_api_run_lifecycle_reports_not_found_and_conflict_status_codes(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    missing_loop_response = client.post("/api/loops/missing-loop/runs")
    assert missing_loop_response.status_code == HTTPStatus.NOT_FOUND
    assert "unknown loop" in missing_loop_response.json()["error"]

    loop = service.create_loop(
        name="Conflict Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=3,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    service.start_run(loop["id"])

    conflict_response = client.post(f"/api/loops/{loop['id']}/runs")
    assert conflict_response.status_code == HTTPStatus.CONFLICT
    assert "active run" in conflict_response.json()["error"]


def test_api_run_lifecycle_rejects_web_headless_start_for_agent_first_loop(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    started = _start_agent_first_loop(service, tmp_path=tmp_path, workdir=sample_workdir)
    client = TestClient(build_app(service=service))

    response = client.post(f"/api/loops/{started['run']['loop_id']}/runs")

    assert response.status_code == HTTPStatus.CONFLICT
    payload = response.json()
    assert "agent-first Loop runs" in payload["error"]
    assert payload["agent_entry_start"]["slash_command"] == "/loopora-run"
    assert payload["agent_entry_start"]["execution_plane"] == "agent_native"
    assert payload["agent_entry_start"]["linked_run_id"] == started["run"]["id"]
    assert payload["agent_entry_start"]["host_context_id"] == "web-api-agent-first"
    assert "loopora agent codex run" in payload["agent_entry_start"]["loop_command"]
    assert "--context-id web-api-agent-first" in payload["agent_entry_start"]["loop_command"]
    assert "--json" in payload["agent_entry_start"]["loop_command"]
    assert len(service.get_loop(started["run"]["loop_id"])["runs"]) == 1


def test_api_runtime_activity_reports_running_runs(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success", role_delay=0.4)
    loop = service.create_loop(
        name="Runtime Activity Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=3,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.start_run(loop["id"])
    service.start_run_async(run["id"])

    deadline = time.time() + 5
    while time.time() < deadline:
        current = service.get_run(run["id"])
        if current["status"] == "running":
            break
        time.sleep(0.05)

    client = TestClient(build_app(service=service))
    response = client.get("/api/runtime/activity")

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["app_home"]
    assert payload["running_count"] >= 1
    assert payload["has_running_runs"] is True
    assert any(item["id"] == run["id"] and item["loop_name"] == "Runtime Activity Loop" for item in payload["runs"])

    service.stop_run(run["id"])


def test_api_stop_run_rejects_finished_runs(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Finished Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.rerun(loop["id"])
    client = TestClient(build_app(service=service))

    response = client.post(f"/api/runs/{run['id']}/stop")

    assert response.status_code == HTTPStatus.CONFLICT
    assert "cannot stop run in status" in response.json()["error"]
