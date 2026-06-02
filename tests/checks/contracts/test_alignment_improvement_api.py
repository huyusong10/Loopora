from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.bundles import bundle_to_yaml
from loopora.web import build_app


def test_alignment_api_creates_improvement_sessions_from_bundle_and_run(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="API Improvement Source Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    source = service.import_bundle_text(
        bundle_to_yaml(
            service.derive_bundle_from_loop(
                loop["id"],
                name="API Improvement Source Bundle",
                description="API improvement source.",
                collaboration_summary="Keep the source posture visible.",
            )
        )
    )
    run = service.rerun(source["loop_id"])
    client = TestClient(build_app(service=service))

    bundle_response = client.post(f"/api/bundles/{source['id']}/revise", json={"start_immediately": False})
    assert bundle_response.status_code == HTTPStatus.CREATED
    bundle_payload = bundle_response.json()
    assert bundle_payload["redirect_url"] == f"/loops/new/bundle?alignment_session_id={bundle_payload['session']['id']}"
    assert bundle_payload["session"]["working_agreement"]["mode"] == "improvement"
    assert bundle_payload["session"]["working_agreement"]["source"]["source_type"] == "bundle"
    assert bundle_payload["session"]["working_agreement"]["source"]["source_bundle_id"] == source["id"]

    run_response = client.post(f"/api/runs/{run['id']}/revise", json={"start_immediately": False})
    assert run_response.status_code == HTTPStatus.CREATED
    run_payload = run_response.json()
    assert run_payload["redirect_url"] == f"/loops/new/bundle?alignment_session_id={run_payload['session']['id']}"
    assert run_payload["session"]["working_agreement"]["mode"] == "improvement"
    assert run_payload["session"]["working_agreement"]["source"]["source_type"] == "run"
    assert run_payload["session"]["working_agreement"]["source"]["source_run_id"] == run["id"]
