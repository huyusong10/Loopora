from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.run_takeaways import empty_judgment_contract
from loopora import service_run_acceptance
from loopora.web import build_app

from web_api_test_support import _create_api_loop_run, _wait_for_run_success


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

    response = client.post(f"/runs/{run['id']}/accept")

    assert response.status_code == HTTPStatus.CONFLICT
    assert "cannot accept run result in status" in response.json()["error"]


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
