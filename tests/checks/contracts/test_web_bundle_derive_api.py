from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.web import build_app


def test_api_bundles_derive_returns_bundle_payload(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Bundle Derive Source",
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
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/bundles/derive",
        json={
            "loop_id": loop["id"],
            "name": "Derived Bundle",
            "description": "Derived from existing assets.",
            "collaboration_summary": "Treat fake done states as blockers.",
        },
    )

    assert response.status_code == HTTPStatus.OK
    bundle = response.json()["bundle"]
    assert bundle["metadata"]["name"] == "Derived Bundle"
    assert bundle["collaboration_summary"] == "Treat fake done states as blockers."
    assert bundle["workflow"]["roles"]
    assert bundle["role_definitions"]
