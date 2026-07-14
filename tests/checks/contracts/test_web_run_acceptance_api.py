from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from loopora import service_run_acceptance
from loopora.run_result_recording import (
    RUN_RESULT_LIFECYCLE_FAILURE_BLOCKED_REASON,
    RUN_RESULT_MISSING_TASK_VERDICT_BLOCKED_REASON,
    RUN_RESULT_NOT_EVALUATED_BLOCKED_REASON,
    run_result_recording_blocked_reason,
)
from loopora.run_takeaways import empty_judgment_contract
from loopora.service_run_acceptance_evidence import (
    normalize_acceptance_coverage_target_basis,
    recorded_advisory_follow_up_available,
)
from loopora.run_worker_start import BACKGROUND_WORKER_START_ERROR
from loopora.service_types import LooporaError
from loopora.web import build_app

from web_api_test_support import _create_api_loop_run, _wait_for_run_success


EMPTY_TARGET_BASIS = {
    "required": {"total": 0, "covered": 0, "weak": 0, "unproven": 0, "blocking": 0, "open": 0},
    "advisory": {"total": 0, "covered": 0, "weak": 0, "unproven": 0, "blocking": 0, "open": 0},
}


def test_acceptance_target_basis_normalization_rejects_coerced_counts_and_preserves_status_totals() -> None:
    assert normalize_acceptance_coverage_target_basis(
        {
            "required": {"total": True, "covered": 2, "weak": "1", "unproven": -1},
            "advisory": {"total": 1, "covered": 1, "weak": 2, "blocking": False},
        }
    ) == {
        "required": {"total": 2, "covered": 2, "weak": 0, "unproven": 0, "blocking": 0, "open": 0},
        "advisory": {"total": 3, "covered": 1, "weak": 2, "unproven": 0, "blocking": 0, "open": 2},
    }


def test_advisory_follow_up_requires_recorded_passing_basis_with_required_targets_closed() -> None:
    passing_basis = {
        "required": {"total": 2, "covered": 2},
        "advisory": {"total": 3, "covered": 1, "unproven": 2},
    }
    unproven_basis = {
        "required": {"total": 2, "covered": 1, "unproven": 1},
        "advisory": {"total": 3, "covered": 1, "unproven": 2},
    }

    assert recorded_advisory_follow_up_available("passed", passing_basis) is True
    assert recorded_advisory_follow_up_available("passed_with_residual_risk", passing_basis) is True
    assert recorded_advisory_follow_up_available("insufficient_evidence", passing_basis) is False
    assert recorded_advisory_follow_up_available("passed", unproven_basis) is False


def test_run_accept_result_rejects_active_run(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Active Accept Loop",
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
    run = service.start_run(loop["id"])
    client = TestClient(build_app(service=service))

    response = client.post(f"/runs/{run['id']}/accept", headers={"accept": "application/json"})

    assert response.status_code == HTTPStatus.CONFLICT
    assert "cannot accept run result in status" in response.json()["error"]


def test_run_reopen_recorded_result_rejects_active_run(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Active Reopen Loop",
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
    run = service.start_run(loop["id"])
    client = TestClient(build_app(service=service))

    response = client.post(f"/runs/{run['id']}/reopen-result", headers={"accept": "application/json"})

    assert response.status_code == HTTPStatus.CONFLICT
    assert "cannot reopen recorded run result in status" in response.json()["error"]


def test_run_accept_form_routes_active_run_back_to_visible_page_error(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Active Accept Form Loop",
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
    run = service.start_run(loop["id"])
    client = TestClient(build_app(service=service))

    response = client.post(
        f"/runs/{run['id']}/accept",
        headers={"accept": "text/html"},
        follow_redirects=False,
    )

    assert response.status_code == HTTPStatus.SEE_OTHER
    redirect_parts = urlsplit(response.headers["location"])
    assert redirect_parts.path == f"/runs/{run['id']}"
    redirect_query = parse_qs(redirect_parts.query)
    assert redirect_query["run_action_error"]
    assert redirect_query["workdir"] == [str(sample_workdir)]
    error_page = client.get(response.headers["location"])
    assert error_page.status_code == HTTPStatus.OK
    assert 'data-testid="run-action-error"' in error_page.text
    assert "cannot accept run result in status" in error_page.text


def test_run_accept_result_rejects_lifecycle_failure_run_even_with_not_evaluated_verdict(
    monkeypatch,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="No Task Verdict Accept Loop",
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
    private_path = tmp_path / "private" / "thread-start"

    class FailingRunThread:
        name = "run-start-failure"

        def start(self) -> None:
            raise OSError(f"permission denied: {private_path}")

    monkeypatch.setattr(service, "_build_run_thread", lambda _run_id: FailingRunThread())
    run = service.start_run(loop["id"])
    with pytest.raises(LooporaError, match=BACKGROUND_WORKER_START_ERROR):
        service.start_run_async(run["id"])
    failed_run = service.get_run(run["id"])
    assert failed_run["status"] == "failed"
    assert failed_run["task_verdict"]["status"] == "not_evaluated"
    assert failed_run["task_verdict"]["source"] == "run_status"
    acceptance_state = service.run_result_acceptance_state(run["id"])
    assert acceptance_state["recordable"] is False
    assert acceptance_state["recording_blocked_reason"] == RUN_RESULT_LIFECYCLE_FAILURE_BLOCKED_REASON
    client = TestClient(build_app(service=service))

    response = client.post(f"/runs/{run['id']}/accept", headers={"accept": "application/json"})

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()["error"] == RUN_RESULT_LIFECYCLE_FAILURE_BLOCKED_REASON
    assert service.recent_run_events(run["id"], event_types={"run_result_accepted"}) == []


def test_run_result_recording_prefers_lifecycle_failure_over_missing_task_verdict() -> None:
    assert (
        run_result_recording_blocked_reason(
            {"status": "failed", "error_message": BACKGROUND_WORKER_START_ERROR},
            task_verdict_status="",
        )
        == RUN_RESULT_LIFECYCLE_FAILURE_BLOCKED_REASON
    )
    assert (
        run_result_recording_blocked_reason({"status": "failed"}, task_verdict_status="")
        == RUN_RESULT_MISSING_TASK_VERDICT_BLOCKED_REASON
    )


def test_run_accept_result_rejects_not_evaluated_terminal_run_without_lifecycle_failure(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Not Evaluated Accept Loop",
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
    acceptance_state = service.run_result_acceptance_state(run["id"])
    assert acceptance_state["recordable"] is False
    assert acceptance_state["recording_blocked_reason"] == RUN_RESULT_NOT_EVALUATED_BLOCKED_REASON
    client = TestClient(build_app(service=service))

    response = client.post(f"/runs/{run['id']}/accept", headers={"accept": "application/json"})

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()["error"] == RUN_RESULT_NOT_EVALUATED_BLOCKED_REASON
    assert service.recent_run_events(run["id"], event_types={"run_result_accepted"}) == []


def test_run_reopen_recorded_result_is_append_only_and_idempotent(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    run_id = _create_api_loop_run(client, sample_spec_file, sample_workdir)
    _wait_for_run_success(client, run_id)
    accept_response = client.post(f"/runs/{run_id}/accept", follow_redirects=False)
    assert accept_response.status_code == HTTPStatus.SEE_OTHER
    accepted_event = service.recent_run_events(run_id, event_types={"run_result_accepted"})[-1]
    accepted_state = service.run_result_acceptance_state(run_id)
    assert accepted_state["accepted"] is True
    assert accepted_state["event_id"] == accepted_event["id"]
    assert accepted_state["recorded_coverage_target_basis"] == accepted_event["payload"]["coverage_target_basis"]
    assert accepted_state["recorded_advisory_follow_up_available"] is True

    reopen_response = client.post(f"/runs/{run_id}/reopen-result", follow_redirects=False)

    assert reopen_response.status_code == HTTPStatus.SEE_OTHER
    reopen_parts = urlsplit(reopen_response.headers["location"])
    assert reopen_parts.path == f"/runs/{run_id}"
    assert parse_qs(reopen_parts.query)["workdir"] == [str(sample_workdir)]
    reopened_events = service.recent_run_events(run_id, event_types={"run_result_acceptance_reopened"})
    assert len(reopened_events) == 1
    reopened_payload = reopened_events[-1]["payload"]
    assert reopened_payload["recorded_event_id"] == accepted_event["id"]
    assert reopened_payload["evidence_source_event_id"] == accepted_state["evidence_source_event_id"]
    reopened_state = service.run_result_acceptance_state(run_id)
    assert reopened_state["accepted"] is False
    assert reopened_state["event_id"] == reopened_events[-1]["id"]
    assert reopened_state["state_event_type"] == "run_result_acceptance_reopened"
    assert reopened_state["recorded_coverage_target_basis"] == EMPTY_TARGET_BASIS
    assert reopened_state["recorded_advisory_follow_up_available"] is False
    duplicate_reopen_response = client.post(f"/runs/{run_id}/reopen-result", follow_redirects=False)
    assert duplicate_reopen_response.status_code == HTTPStatus.SEE_OTHER
    assert service.recent_run_events(run_id, event_types={"run_result_acceptance_reopened"}) == reopened_events

    second_accept_response = client.post(f"/runs/{run_id}/accept", follow_redirects=False)

    assert second_accept_response.status_code == HTTPStatus.SEE_OTHER
    accepted_events = service.recent_run_events(run_id, event_types={"run_result_accepted"})
    assert len(accepted_events) == 2
    assert accepted_events[0]["id"] == accepted_event["id"]
    assert accepted_events[-1]["id"] > reopened_events[-1]["id"]
    assert service.run_result_acceptance_state(run_id)["accepted"] is True


def test_run_accept_result_keeps_audit_shape_when_evidence_summary_is_unavailable(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    run_id = _create_api_loop_run(client, sample_spec_file, sample_workdir)
    _wait_for_run_success(client, run_id)

    def fail_takeaways(_run: dict) -> dict:
        raise RuntimeError("raw artifact read failed")

    monkeypatch.setattr(service_run_acceptance, "build_run_key_takeaways", fail_takeaways)

    response = client.post(f"/runs/{run_id}/accept", follow_redirects=False)

    assert response.status_code == HTTPStatus.SEE_OTHER
    accepted_event = service.recent_run_events(run_id, event_types={"run_result_accepted"})[-1]
    payload = accepted_event["payload"]
    assert payload["evidence_source_event_id"] < accepted_event["id"]
    assert payload["evidence_available"] is False
    assert payload["evidence_error"] == "acceptance_evidence_unavailable"
    assert payload["judgment_contract"] == empty_judgment_contract()
    assert payload["run_contract_path"] == ""
    assert payload["judgment_contract_summary"] == ""
    assert payload["check_mode"] == ""
    assert payload["check_count"] == 0
    assert payload["completion_mode"] == ""
    assert "workflow_preset" not in payload
    assert payload["coverage_targets"] == []
    assert payload["loop_fit_reasons"] == []
    assert payload["execution_strategy"] == []
    assert payload["local_governance"] == []
    assert payload["role_postures"] == []
    assert payload["judgment_tradeoffs"] == []
    assert payload["success_surface"] == []
    assert payload["fake_done_states"] == []
    assert payload["evidence_preferences"] == []
    assert payload["residual_risk"] == ""
    assert payload["task_verdict_path"] == ""
    assert payload["coverage_path"] == ""
    assert payload["manifest_path"] == ""
    assert payload["evidence_count"] == 0
    assert payload["evidence_bucket_counts"] == {
        "proven": 0,
        "weak": 0,
        "unproven": 0,
        "blocking": 0,
        "residual_risk": 0,
    }
    assert payload["coverage_target_basis"] == EMPTY_TARGET_BASIS
    assert service.run_result_acceptance_state(run_id)["recorded_coverage_target_basis"] == EMPTY_TARGET_BASIS
