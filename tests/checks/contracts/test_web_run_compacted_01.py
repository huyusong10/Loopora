from __future__ import annotations

# Merged from test_web_run_artifact_smoke_api.py
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient

from loopora.web import build_app

from web_api_test_support import (
    _assert_file_explorer_contract,
    _assert_file_preview_safety,
    _assert_run_artifact_catalog,
    _assert_run_artifact_previews,
    _assert_run_event_streaming,
    _create_api_loop_run,
    _wait_for_run_success,
)


def test_api_loop_creation_run_preview_and_stream(
    service_factory,
    sample_spec_file: Path,
    sample_spec_text: str,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    run_id = _create_api_loop_run(client, sample_spec_file, sample_workdir)
    _wait_for_run_success(client, run_id)
    _assert_file_explorer_contract(client, run_id)
    _assert_run_artifact_catalog(client, run_id)
    _assert_run_artifact_previews(client, run_id, sample_spec_text)
    _assert_file_preview_safety(client, run_id, sample_workdir)
    _assert_run_event_streaming(client, run_id)

# Merged from test_web_run_event_api_cursor_validation.py
from http import HTTPStatus


from loopora.web_streaming import MAX_EVENT_CURSOR_ID


def test_run_event_api_rejects_out_of_range_query_params(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    for path in (
        "/api/runs/run_test/events?after_id=-1",
        f"/api/runs/run_test/events?after_id={MAX_EVENT_CURSOR_ID + 1}",
        "/api/runs/run_test/events?limit=0",
        "/api/runs/run_test/events?limit=5001",
        "/api/runs/run_test/stream?after_id=-1",
        f"/api/runs/run_test/stream?after_id={MAX_EVENT_CURSOR_ID + 1}",
    ):
        response = client.get(path)
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["error"] == "request validation failed"


def test_run_event_api_rejects_cursor_beyond_current_run_events(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Cursor Boundary Loop",
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
    latest_event = service.repository.append_event(run["id"], "run_started", {"status": "running"})
    future_cursor = latest_event["id"] + 1
    client = TestClient(build_app(service=service))

    for path in (
        f"/api/runs/{run['id']}/events?after_id={future_cursor}",
        f"/api/runs/{run['id']}/stream?after_id={future_cursor}",
    ):
        response = client.get(path)
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["error"] == "event cursor is out of range"

# Merged from test_web_run_event_api_missing_run.py




def test_api_run_events_and_stream_require_a_real_run(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    events_response = client.get("/api/runs/missing-run/events")
    assert events_response.status_code == HTTPStatus.NOT_FOUND
    assert "unknown run" in events_response.json()["error"]

    snapshot_response = client.get("/api/runs/missing-run/observation-snapshot")
    assert snapshot_response.status_code == HTTPStatus.NOT_FOUND
    assert "unknown run" in snapshot_response.json()["error"]

    stream_response = client.get("/api/runs/missing-run/stream")
    assert stream_response.status_code == HTTPStatus.NOT_FOUND
    assert "unknown run" in stream_response.json()["error"]

# Merged from test_web_run_observation_snapshot_cutoff_api.py

from web_run_observation_snapshot_test_support import create_snapshot_loop, observation_client


def test_api_run_observation_snapshot_uses_consistent_event_cutoff(
    monkeypatch,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_snapshot_loop(service, sample_spec_file, sample_workdir, name="Snapshot Cutoff Loop")
    run = service.start_run(loop["id"])
    service.repository.append_event(run["id"], "run_started", {"status": "running"})
    service.repository.append_event(
        run["id"],
        "role_started",
        {"role": "generator", "step_id": "initial_step", "iter": 0},
        role="generator",
    )
    service.repository.append_event(
        run["id"],
        "codex_event",
        {"type": "stdout", "message": "visible before cutoff"},
        role="generator",
    )

    original_recent_rows = service.repository._recent_event_rows_for_connection
    captured: dict[str, int] = {}

    def recent_rows_with_concurrent_append(connection, run_id: str, **kwargs):
        captured.setdefault("cutoff", int(kwargs.get("max_event_id") or 0))
        if "late_id" not in captured:
            late_event = service.repository.append_event(
                run_id,
                "role_started",
                {"role": "generator", "step_id": "late_step", "iter": 1},
                role="generator",
            )
            captured["late_id"] = late_event["id"]
        return original_recent_rows(connection, run_id, **kwargs)

    monkeypatch.setattr(service.repository, "_recent_event_rows_for_connection", recent_rows_with_concurrent_append)
    client = observation_client(service)
    response = client.get(f"/api/runs/{run['id']}/observation-snapshot")

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["latest_event_id"] == captured["cutoff"]
    assert payload["key_takeaways"]["source_event_id"] == captured["cutoff"]
    for event in payload["timeline_events"] + payload["console_events"] + payload["progress_events"]:
        assert event["id"] <= payload["latest_event_id"]
        assert event["id"] != captured["late_id"]

    events_response = client.get(f"/api/runs/{run['id']}/events?after_id={payload['latest_event_id']}")
    assert events_response.status_code == HTTPStatus.OK
    assert any(event["id"] == captured["late_id"] for event in events_response.json())

# Merged from test_web_run_terminal_actions_api.py



from web_api_test_support import (
    _accept_run_result_and_assert_observation_event,
    _assert_run_detail_terminal_actions_page,
    _expected_recorded_verdict_page_text,
    _expected_recorded_verdict_title,
    _wait_for_run_terminal_status,
)


def test_run_detail_separates_status_verdict_and_reruns_terminal_run(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Rerun From Detail Loop",
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

    _assert_run_detail_terminal_actions_page(client, run, loop)

    _accept_run_result_and_assert_observation_event(client, service, run, loop)
    accepted_events_after_first_post = service.recent_run_events(run["id"], event_types={"run_result_accepted"})
    first_accept_event_id = accepted_events_after_first_post[-1]["id"]
    accepted_task_verdict_status = accepted_events_after_first_post[-1]["payload"]["task_verdict_status"]
    _assert_run_detail_recorded_result_state(
        client,
        service,
        run,
        first_accept_event_id=first_accept_event_id,
        accepted_task_verdict_status=accepted_task_verdict_status,
    )
    _assert_run_detail_recorded_result_can_reopen(client, service, run, recorded_event_id=first_accept_event_id)

    rerun_response = client.post(f"/runs/{run['id']}/rerun", follow_redirects=False)

    assert rerun_response.status_code == HTTPStatus.SEE_OTHER
    redirect_parts = urlsplit(rerun_response.headers["location"])
    assert redirect_parts.path.startswith("/runs/")
    assert parse_qs(redirect_parts.query)["workdir"] == [str(sample_workdir)]
    new_run_id = redirect_parts.path.removeprefix("/runs/")
    assert new_run_id
    assert new_run_id != run["id"]
    assert service.get_run(new_run_id)["loop_id"] == loop["id"]
    _wait_for_run_terminal_status(service, new_run_id)


def _assert_run_detail_recorded_result_state(
    client: TestClient,
    service,
    run: dict,
    *,
    first_accept_event_id: int,
    accepted_task_verdict_status: str,
) -> None:
    page_after_accept = client.get(f"/runs/{run['id']}")
    assert page_after_accept.status_code == HTTPStatus.OK
    assert 'data-testid="run-accepted-result-state"' in page_after_accept.text
    assert _expected_recorded_verdict_page_text(accepted_task_verdict_status) in page_after_accept.text
    assert 'data-testid="run-accept-result-button"' not in page_after_accept.text
    assert 'data-testid="run-evidence-improve-button"' not in page_after_accept.text
    duplicate_accept_response = client.post(f"/runs/{run['id']}/accept", follow_redirects=False)
    assert duplicate_accept_response.status_code == HTTPStatus.SEE_OTHER
    accepted_events_after_duplicate_post = service.recent_run_events(run["id"], event_types={"run_result_accepted"})
    assert [event["id"] for event in accepted_events_after_duplicate_post] == [first_accept_event_id]
    acceptance_state = service.run_result_acceptance_state(run["id"])
    assert acceptance_state["accepted"] is True
    assert acceptance_state["event_id"] == first_accept_event_id
    snapshot_response = client.get(f"/api/runs/{run['id']}/observation-snapshot")
    assert snapshot_response.status_code == HTTPStatus.OK
    snapshot_payload = snapshot_response.json()
    accepted_timeline_events = [
        event for event in snapshot_payload["timeline_events"] if event["event_type"] == "run_result_accepted"
    ]
    assert accepted_timeline_events
    assert accepted_timeline_events[-1]["title"] == _expected_recorded_verdict_title(accepted_task_verdict_status)
    assert snapshot_payload["key_takeaways"]["source_event_id"] <= snapshot_payload["latest_event_id"]


def _assert_run_detail_recorded_result_can_reopen(
    client: TestClient,
    service,
    run: dict,
    *,
    recorded_event_id: int,
) -> None:
    reopen_response = client.post(f"/runs/{run['id']}/reopen-result", follow_redirects=False)
    assert reopen_response.status_code == HTTPStatus.SEE_OTHER
    reopened_events = service.recent_run_events(run["id"], event_types={"run_result_acceptance_reopened"})
    assert len(reopened_events) == 1
    assert reopened_events[-1]["payload"]["recorded_event_id"] == recorded_event_id
    reopened_state = service.run_result_acceptance_state(run["id"])
    assert reopened_state["accepted"] is False
    assert reopened_state["event_id"] == reopened_events[-1]["id"]
    page_after_reopen = client.get(f"/runs/{run['id']}")
    assert page_after_reopen.status_code == HTTPStatus.OK
    assert 'data-testid="run-accept-result-button"' in page_after_reopen.text
    assert 'data-testid="run-reopen-recorded-result-button"' not in page_after_reopen.text
    assert 'data-testid="run-result-decision"' in page_after_reopen.text
    assert page_after_reopen.text.count('data-testid="run-improve-chat-button"') == 1
    assert 'data-testid="run-evidence-improve-button"' not in page_after_reopen.text
    snapshot_after_reopen = client.get(f"/api/runs/{run['id']}/observation-snapshot")
    assert snapshot_after_reopen.status_code == HTTPStatus.OK
    reopened_timeline_events = [
        event
        for event in snapshot_after_reopen.json()["timeline_events"]
        if event["event_type"] == "run_result_acceptance_reopened"
    ]
    assert reopened_timeline_events
    assert reopened_timeline_events[-1]["title"] == "Recorded evidence verdict reopened"
