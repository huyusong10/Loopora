from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from loopora.web import build_app

from web_api_test_support import _create_api_loop_run, _wait_for_run_success


WEB_RUN_DETAIL_PROJECTION_SCHEMA_VERSION = 4


def test_api_run_detail_includes_v4_web_projection(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    run_id = _create_api_loop_run(client, sample_spec_file, sample_workdir)
    _wait_for_run_success(client, run_id)
    payload = client.get(f"/api/runs/{run_id}").json()
    projection = payload["web_projection"]

    assert projection["schema_version"] == WEB_RUN_DETAIL_PROJECTION_SCHEMA_VERSION
    assert projection["kind"] == "web_run_detail"
    assert projection["strategy_source"] == payload["workflow_json"]
    assert projection["progress_stages"][0] == {"key": "checks", "label": "Checks", "kind": "checks", "sequence": 1}
    assert projection["progress_stages"][-1]["kind"] == "finished"
    assert {stage["kind"] for stage in projection["progress_stages"]} >= {"strategy_step"}
    assert projection["summary"]["run_id"] == run_id
    assert projection["summary"]["run_status"] == payload["status"]
    assert projection["lifecycle"]["run_id"] == run_id
    assert projection["task_verdict"]["status"] in {
        "passed",
        "passed_with_residual_risk",
        "insufficient_evidence",
        "not_evaluated",
    }
    assert "summary_md" in projection["display"]
    assert {"queued_at", "started_at", "finished_at", "updated_at", "created_at"} <= set(projection["timing"])
    assert projection["technical_handoff"]["run_url"] == f"/runs/{run_id}"
    assert projection["diagnostics"]["source_shape"] == "projection_bundle"
    assert projection["diagnostics"]["projection_source_sequence"] >= 1
    assert "raw" not in projection
