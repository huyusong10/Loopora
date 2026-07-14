from __future__ import annotations

import shutil
import time
from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

from fastapi.testclient import TestClient

from loopora.run_worker_start import BACKGROUND_WORKER_START_ERROR
from loopora.utils import read_json, write_json
from loopora.web import build_app

from web_api_test_support import (
    _assert_recovery_summary_actions,
    _assert_web_delete_preview_action_projection,
    _create_api_loop_run,
    _start_agent_first_loop,
    _wait_for_run_success,
)


def _assert_embedded_failed_run_retry_ready(payload: dict) -> None:
    run = payload["run"]
    assert run["next_actions"] == payload["next_actions"]
    assert run["next_action_kinds"] == run["next_action_ready_now_kinds"] == ["retry_web_run_start"]
    assert run["next_action_ready_after_actions"] == {}


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
    assert str(sample_workdir.resolve()) not in conflict_response.json()["error"]
    delete_preview_response = client.get(f"/api/loops/{loop['id']}/delete-preview")
    assert delete_preview_response.status_code == HTTPStatus.OK
    assert delete_preview_response.json()["delete_allowed"] is False
    _assert_web_delete_preview_action_projection(delete_preview_response.json())


def test_api_loop_delete_preview_projects_follow_up_action(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Preview Delete Loop",
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
    client = TestClient(build_app(service=service))

    response = client.get(f"/api/loops/{loop['id']}/delete-preview")

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["delete_allowed"] is True
    assert payload["would_delete"]["loop"] == loop["id"]
    _assert_web_delete_preview_action_projection(
        payload,
        expected_kind="delete_loop",
        expected_endpoint=f"/api/loops/{quote(loop['id'], safe='')}",
    )


def test_loop_api_and_detail_project_cross_run_evidence_progress(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    previous_run_id = _create_api_loop_run(client, sample_spec_file, sample_workdir)
    _wait_for_run_success(client, previous_run_id)
    previous_run = service.get_run(previous_run_id)
    coverage_path = Path(previous_run["runs_dir"]) / "evidence" / "coverage.json"
    previous_coverage = read_json(coverage_path)
    target = previous_coverage["targets"][0]
    target["status"] = "missing"
    target["reason"] = "Previous run did not prove this target."
    target["evidence_refs"] = []
    write_json(coverage_path, previous_coverage)

    started = client.post(f"/api/loops/{previous_run['loop_id']}/runs")
    assert started.status_code == HTTPStatus.CREATED
    latest_run_id = started.json()["id"]
    _wait_for_run_success(client, latest_run_id)

    api_loop = client.get(f"/api/loops/{previous_run['loop_id']}")
    loop_page = client.get(f"/loops/{previous_run['loop_id']}")
    status_kind, status_loop = service.get_status(previous_run["loop_id"])

    assert api_loop.status_code == loop_page.status_code == HTTPStatus.OK
    progress = api_loop.json()["run_progress"]
    assert (progress["status"], progress["comparable"]) == ("progressed", True)
    assert (progress["latest_run_id"], progress["previous_run_id"]) == (latest_run_id, previous_run_id)
    assert progress["improved_target_count"] >= 1
    assert progress["closed_gap_count"] >= 1
    assert status_kind == "loop"
    assert status_loop["run_progress"] == progress
    assert 'data-run-progress-status="progressed"' in loop_page.text
    assert 'data-testid="loop-run-progress-targets"' in loop_page.text
    assert loop_page.text.index('data-testid="loop-detail-history-panel"') < loop_page.text.index(
        'data-testid="loop-detail-summary-panel"'
    ) < loop_page.text.index('data-testid="loop-detail-config-panel"') < loop_page.text.index(
        'data-testid="loop-detail-spec-panel"'
    )


def test_api_run_lifecycle_rejects_web_headless_start_for_agent_native_loop(
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
    assert "Agent-native Loop runs" in payload["error"]
    assert "same host Agent" in payload["error"]
    assert payload["agent_entry_start"]["slash_command"] == "/loopora-run"
    assert payload["agent_entry_start"]["execution_plane"] == "agent_native"
    assert payload["agent_entry_start"]["linked_run_id"] == started["run"]["id"]
    assert payload["agent_entry_start"]["host_context_id"] == "web-api-agent-first"
    assert "loopora agent codex run" in payload["agent_entry_start"]["loop_command"]
    assert "--context-id web-api-agent-first" in payload["agent_entry_start"]["loop_command"]
    assert "--json" in payload["agent_entry_start"]["loop_command"]
    assert len(service.get_loop(started["run"]["loop_id"])["runs"]) == 1


def test_api_start_run_explains_missing_saved_workdir_without_recreating_project(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Missing Workdir API Start Loop",
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
    shutil.rmtree(sample_workdir)
    client = TestClient(build_app(service=service))

    response = client.post(f"/api/loops/{loop['id']}/runs")

    assert response.status_code == HTTPStatus.BAD_REQUEST
    payload = response.json()
    assert payload["loop_recovery"] == "target_workdir_unavailable"
    assert payload["status"] == "blocked_by_workdir"
    assert payload["surface"] == "web_loop_start"
    assert payload["loop_id"] == loop["id"]
    assert payload["web_workdir_recovery_summary"]["next_action_kinds"] == [item["kind"] for item in payload["next_actions"]]
    assert payload["web_workdir_recovery_summary"]["workdir_state_status"] == "missing"
    assert payload["next_actions"][0]["kind"] == "create_workdir"
    assert payload["next_actions"][-1]["kind"] == "retry_web_run_start"
    assert payload["next_action_ready_after_actions"] == {
        "confirm_readiness": "create_workdir",
        "retry_web_run_start": "confirm_readiness",
    }
    assert not sample_workdir.exists()
    assert service.get_loop(loop["id"])["runs"] == []


def test_api_start_run_reports_blank_saved_workdir_as_required_recovery(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Blank Workdir API Loop",
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
    with service.repository.transaction() as connection:
        connection.execute("UPDATE loop_definitions SET workdir = ? WHERE id = ?", ("", loop["id"]))
    client = TestClient(build_app(service=service))

    response = client.post(f"/api/loops/{loop['id']}/runs")

    assert response.status_code == HTTPStatus.BAD_REQUEST
    payload = response.json()
    assert payload["loop_recovery"] == "target_workdir_unavailable"
    assert payload["status"] == "blocked_by_workdir"
    assert payload["workdir"] == ""
    assert payload["workdir_state"]["status"] == "required"
    assert payload["workdir_state"]["error"] == "workdir is required"
    _assert_recovery_summary_actions(
        payload,
        summary_key="web_workdir_recovery_summary",
        state_key="workdir_state_status",
        state="required",
        expected=["choose_workdir", "confirm_readiness", "retry_web_run_start"],
    )
    assert "command" not in payload["next_actions"][0]
    assert "command" not in payload["next_actions"][1]
    assert str(Path.cwd()) not in response.text
    assert service.get_loop(loop["id"])["runs"] == []


def test_api_start_run_explains_uninspectable_saved_workdir_without_os_error(
    monkeypatch,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Uninspectable Workdir API Start Loop",
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
    private_path = tmp_path / "private" / "blocked"
    sample_workdir_resolved = sample_workdir.resolve(strict=False)
    original_exists = Path.exists

    def fail_exists(path: Path) -> bool:
        if path == sample_workdir_resolved:
            raise OSError(f"permission denied: {private_path}")
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", fail_exists)
    client = TestClient(build_app(service=service))

    response = client.post(f"/api/loops/{loop['id']}/runs")

    assert response.status_code == HTTPStatus.BAD_REQUEST
    payload = response.json()
    assert payload["loop_recovery"] == "target_workdir_unavailable"
    assert payload["status"] == "blocked_by_workdir"
    assert payload["workdir_state"]["status"] == "unavailable"
    assert payload["workdir_state"]["error"] == "workdir could not be inspected"
    encoded = response.text
    assert "permission denied" not in encoded
    assert str(private_path) not in encoded

    assert service.get_loop(loop["id"])["runs"] == []


def test_api_start_run_marks_failed_when_worker_cannot_start_without_os_error(
    monkeypatch,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Worker Dispatch Failure API Loop",
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
    private_path = tmp_path / "private" / "thread-start"

    class FailingRunThread:
        name = "run-start-failure"

        def start(self) -> None:
            raise OSError(f"permission denied: {private_path}")

    monkeypatch.setattr(service, "_build_run_thread", lambda _run_id: FailingRunThread())
    client = TestClient(build_app(service=service))

    response = client.post(f"/api/loops/{loop['id']}/runs")

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    payload = response.json()
    assert next(iter(payload)) == "web_run_start_recovery_summary"
    assert payload["error"] == BACKGROUND_WORKER_START_ERROR
    assert payload["run_start_error"] == BACKGROUND_WORKER_START_ERROR
    assert payload["run_recovery"] == "retry_run_start"
    summary = payload["web_run_start_recovery_summary"]
    assert payload["next_actions"] == [
        {
            "kind": "retry_web_run_start",
            "target": "web_loop_start",
            "action": "start_run",
            "loop_id": loop["id"],
        }
    ]
    assert summary["run_recovery"] == payload["run_recovery"]
    assert summary["run_start_error"] == payload["run_start_error"]
    assert summary["loop_id"] == loop["id"]
    assert summary["next_action_kinds"] == ["retry_web_run_start"]
    assert summary["next_action_ready_now_kinds"] == ["retry_web_run_start"]
    assert summary["next_action_ready_after_actions"] == {}
    assert payload["next_action_ready_now_kinds"] == ["retry_web_run_start"]
    assert payload["run"]["status"] == "failed"
    assert payload["run"]["status_label"] == "run_start_failed"
    assert payload["run"]["run_recovery"] == "retry_run_start"
    _assert_embedded_failed_run_retry_ready(payload)
    assert payload["run"]["error_message"] == BACKGROUND_WORKER_START_ERROR
    assert BACKGROUND_WORKER_START_ERROR in payload["run"]["summary_md"]
    run_id = payload["run"]["id"]
    assert summary["run_id"] == run_id
    assert payload["redirect_url"].startswith(f"/runs/{run_id}?")
    assert summary["redirect_url"] == payload["redirect_url"]
    redirect_parts = urlsplit(payload["redirect_url"])
    assert parse_qs(redirect_parts.query)["run_action_error"] == [BACKGROUND_WORKER_START_ERROR]
    assert parse_qs(redirect_parts.query).get("workdir") == [str(sample_workdir.resolve())]
    stored = service.get_run(run_id)
    assert stored["status"] == "failed"
    assert any(
        event["event_type"] == "run_aborted" and event["payload"]["error"] == BACKGROUND_WORKER_START_ERROR for event in service.stream_events(run_id, limit=50)
    )
    retry_response = client.post(f"/api/loops/{loop['id']}/runs")
    retry_run_id = retry_response.json()["run"]["id"]
    continuation = service.run_continuation_state(retry_run_id)
    assert continuation["reason"] == "previous_lifecycle_failure_retry"
    assert continuation["previous_run_id"] == run_id
    assert continuation["action_mode"] == "retry_lifecycle"
    encoded = response.text
    assert "permission denied" not in encoded
    assert str(private_path) not in encoded


def test_api_loop_create_start_failure_returns_failed_run_redirect_for_browser_enhancement(
    monkeypatch,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    private_path = tmp_path / "private" / "thread-start"

    class FailingRunThread:
        name = "run-start-failure"

        def start(self) -> None:
            raise OSError(f"permission denied: {private_path}")

    monkeypatch.setattr(service, "_build_run_thread", lambda _run_id: FailingRunThread())
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/loops",
        json={
            "name": "API Create And Start Failure",
            "workdir": str(sample_workdir),
            "spec_path": str(sample_spec_file),
            "max_iters": 3,
            "max_role_retries": 1,
            "delta_threshold": 0.005,
            "trigger_window": 2,
            "regression_window": 2,
            "start_immediately": True,
        },
    )

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    payload = response.json()
    assert payload["web_run_start_recovery_summary"]["next_action_kinds"] == ["retry_web_run_start"]
    assert payload["web_run_start_recovery_summary"]["next_action_ready_now_kinds"] == ["retry_web_run_start"]
    assert payload["next_action_ready_after_actions"] == {}
    assert payload["run_recovery"] == "retry_run_start"
    assert payload["run"]["status"] == "failed"
    _assert_embedded_failed_run_retry_ready(payload)
    assert payload["redirect_url"].startswith(f"/runs/{payload['run']['id']}?")
    redirect_parts = urlsplit(payload["redirect_url"])
    assert parse_qs(redirect_parts.query)["run_action_error"] == [BACKGROUND_WORKER_START_ERROR]
    assert parse_qs(redirect_parts.query).get("workdir") == [str(sample_workdir.resolve())]
    assert "permission denied" not in response.text
    assert str(private_path) not in response.text


def test_loop_create_form_redirects_to_failed_run_when_worker_cannot_start(
    monkeypatch,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    private_path = tmp_path / "private" / "thread-start"

    class FailingRunThread:
        name = "run-start-failure"

        def start(self) -> None:
            raise OSError(f"permission denied: {private_path}")

    monkeypatch.setattr(service, "_build_run_thread", lambda _run_id: FailingRunThread())
    client = TestClient(build_app(service=service))

    response = client.post(
        "/loops/new",
        data={
            "name": "Create Form Worker Dispatch Failure",
            "workdir": str(sample_workdir),
            "spec_path": str(sample_spec_file),
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
            "max_iters": "3",
            "max_role_retries": "1",
            "delta_threshold": "0.005",
            "trigger_window": "2",
            "regression_window": "2",
            "start_immediately": "1",
        },
        follow_redirects=False,
    )

    assert response.status_code == HTTPStatus.SEE_OTHER
    location = response.headers["location"]
    parts = urlsplit(location)
    assert parts.path.startswith("/runs/")
    assert parse_qs(parts.query)["run_action_error"] == [BACKGROUND_WORKER_START_ERROR]
    run_id = parts.path.removeprefix("/runs/")
    stored = service.get_run(run_id)
    assert stored["status"] == "failed"
    assert stored["error_message"] == BACKGROUND_WORKER_START_ERROR
    assert "permission denied" not in location
    assert str(private_path) not in location
    page_response = client.get(location)
    assert page_response.status_code == HTTPStatus.OK
    assert 'data-testid="run-action-recovery"' in page_response.text
    assert 'data-recovery-action-kind="retry_web_run_start"' in page_response.text
    assert 'data-testid="run-result-recovery-notice"' in page_response.text
    assert 'data-testid="run-rerun-button"' in page_response.text
    assert 'data-testid="run-accept-result-button"' not in page_response.text
    assert 'data-testid="run-improve-chat-button"' not in page_response.text
    assert 'data-testid="run-evidence-improve-button"' not in page_response.text
    loop_page = client.get(f"/loops/{stored['loop_id']}")
    assert loop_page.status_code == HTTPStatus.OK
    assert 'data-testid="loop-run-recovery-notice"' in loop_page.text
    assert 'data-testid="loop-retry-run-button"' in loop_page.text
    assert 'data-testid="loop-open-recovery-run"' in loop_page.text
    assert 'data-testid="loop-improve-latest-run-button"' not in loop_page.text
    assert 'data-testid="loop-start-next-evidence-run-button"' not in loop_page.text
    home_page = client.get("/")
    assert home_page.status_code == HTTPStatus.OK
    assert 'data-attention-reason-kind="run_recovery"' in home_page.text
    assert 'data-attention-action-kind="retry_run"' in home_page.text
    assert "Review result" not in home_page.text


def test_loop_create_form_redirect_uses_created_loop_workdir_over_current_query(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    stale_workdir = tmp_path / "stale-project"
    stale_workdir.mkdir()
    client = TestClient(build_app(service=service))

    response = client.post(
        f"/loops/new/manual?workdir={quote(str(stale_workdir), safe='')}",
        data={
            "name": "Resource Context Form Loop",
            "workdir": str(sample_workdir),
            "spec_path": str(sample_spec_file),
            "start_immediately": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == HTTPStatus.SEE_OTHER
    redirect_parts = urlsplit(response.headers["location"])
    loop_id = redirect_parts.path.removeprefix("/loops/")
    assert service.get_loop(loop_id)["workdir"] == str(sample_workdir.resolve())
    assert parse_qs(redirect_parts.query).get("workdir") == [str(sample_workdir.resolve())]


def test_terminal_not_evaluated_run_pages_offer_evidence_continuation_not_lifecycle_recovery(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Not Evaluated Evidence Loop",
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
    service.repository.update_run(
        run["id"],
        status="succeeded",
        summary_md="# Loopora Run Summary\n\nNo evidence verdict was produced.",
        task_verdict={
            "status": "not_evaluated",
            "source": "run_status",
            "summary": "No evidence-based verdict is available.",
        },
    )
    client = TestClient(build_app(service=service))

    page_response = client.get(f"/runs/{run['id']}")
    assert page_response.status_code == HTTPStatus.OK
    assert 'data-testid="run-result-not-evaluated-notice"' in page_response.text
    assert 'data-testid="run-result-recovery-notice"' not in page_response.text
    assert 'data-testid="run-accept-result-button"' not in page_response.text
    assert 'data-testid="run-improve-chat-button"' in page_response.text
    assert 'data-testid="run-rerun-button"' in page_response.text
    assert 'data-testid="run-result-decision"' in page_response.text
    assert page_response.text.count('data-testid="run-improve-chat-button"') == 1
    assert 'data-testid="run-evidence-improve-button"' not in page_response.text

    loop_page = client.get(f"/loops/{loop['id']}")
    assert loop_page.status_code == HTTPStatus.OK
    assert 'data-testid="loop-run-recovery-notice"' not in loop_page.text
    assert 'data-testid="loop-retry-run-button"' not in loop_page.text
    assert 'data-testid="loop-improve-latest-run-button"' in loop_page.text
    assert 'data-testid="loop-start-next-evidence-run-button"' in loop_page.text

    home_page = client.get("/")
    assert home_page.status_code == HTTPStatus.OK
    assert 'data-attention-reason-kind="not_evaluated"' in home_page.text
    assert 'data-attention-action-kind="review_unvalidated_verdict"' in home_page.text
    assert 'data-attention-reason-kind="run_recovery"' not in home_page.text


def test_loop_page_start_run_explains_missing_saved_workdir(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Missing Workdir Page Start Loop",
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
    shutil.rmtree(sample_workdir)
    client = TestClient(build_app(service=service))

    response = client.post(f"/loops/{loop['id']}/runs", follow_redirects=True)

    assert response.status_code == HTTPStatus.OK
    assert 'data-testid="loop-start-run-error" data-return-feedback-param="run_start_error" aria-live="polite"' in response.text
    assert 'data-testid="loop-start-run-recovery"' in response.text
    assert 'data-recovery-action-kind="create_workdir"' in response.text
    assert 'data-recovery-action-kind="confirm_readiness"' in response.text
    assert 'data-recovery-action-kind="retry_web_run_start"' in response.text
    assert "data-recovery-action-form" in response.text
    assert 'form="loop-start-run-retry-form"' in response.text
    assert f'formaction="/loops/{loop["id"]}/runs' in response.text
    assert 'formmethod="post"' in response.text
    assert "mkdir -p" in response.text
    assert "loopora doctor --workdir" in response.text
    assert "workdir does not exist:" not in response.text
    assert not sample_workdir.exists()
    assert service.get_loop(loop["id"])["runs"] == []


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

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
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


def test_api_stop_run_finishes_unclaimed_queued_run(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Queued Stop API Loop",
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
    client = TestClient(build_app(service=service))

    response = client.post(f"/api/runs/{run['id']}/stop")

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["status"] == "stopped"
    assert service.get_run(run["id"])["status"] == "stopped"

    restart_response = client.post(f"/api/loops/{loop['id']}/runs")
    assert restart_response.status_code == HTTPStatus.CREATED
    assert restart_response.json()["status"] == "queued"


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
    payload = response.json()
    assert "cannot stop run in status" in payload["error"]
    assert payload["run_action_recovery"] == "refresh_run_detail"
    assert payload["run"] == {
        "id": run["id"],
        "status": run["status"],
        "loop_id": loop["id"],
    }
    redirect_url = payload["redirect_url"]
    redirect_parts = urlsplit(redirect_url)
    assert redirect_parts.path == f"/runs/{run['id']}"
    assert parse_qs(redirect_parts.query).get("workdir") == [str(sample_workdir.resolve())]
    assert payload["next_actions"] == [
        {
            "kind": "refresh_run_detail",
            "target": "web_run_detail",
            "run_id": run["id"],
            "redirect_url": redirect_url,
        }
    ]
    assert (
        payload["next_action_kinds"],
        payload["next_action_ready_now_kinds"],
        payload["next_action_ready_after_actions"],
        payload["next_action_blocked_kinds"],
        payload["next_action_command_blockers"],
    ) == (["refresh_run_detail"], ["refresh_run_detail"], {}, [], {})
