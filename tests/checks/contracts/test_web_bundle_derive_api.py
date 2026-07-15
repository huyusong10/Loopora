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


def test_api_bundles_derive_redacts_low_level_generation_errors(
    monkeypatch,
    service_factory,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    local_path = tmp_path / "private" / "loopora.db"

    def fail_derive_bundle_from_loop(*_args, **_kwargs):
        raise OSError(f"permission denied: {local_path}")

    monkeypatch.setattr(service, "derive_bundle_from_loop", fail_derive_bundle_from_loop)
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/bundles/derive",
        json={
            "loop_id": "loop_private",
            "name": "Derived Bundle",
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()["error"] == "plan file could not be generated"
    assert "permission denied" not in response.text
    assert str(local_path) not in response.text
