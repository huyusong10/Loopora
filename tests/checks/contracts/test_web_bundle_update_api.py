from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.bundles import bundle_to_yaml
from loopora.web import build_app


def test_api_bundle_update_updates_plan_without_bumping_revision(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Bundle Update Source",
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
    imported = service.import_bundle_text(
        bundle_to_yaml(
            service.derive_bundle_from_loop(
                loop["id"],
                name="API Update Bundle",
                description="Before API update.",
                collaboration_summary="Original collaboration summary.",
            )
        )
    )

    client = TestClient(build_app(service=service))
    response = client.put(
        f"/api/bundles/{imported['id']}",
        json={
            "description": "After API update.",
            "collaboration_summary": "Updated collaboration summary.",
            "spec_markdown": "# Task\n\nUpdated.\n\n# Done When\n- Ready.\n",
        },
    )

    assert response.status_code == HTTPStatus.OK
    bundle = response.json()["bundle"]
    assert bundle["description"] == "After API update."
    assert bundle["collaboration_summary"] == "Updated collaboration summary."
    assert bundle["revision"] == imported["revision"]
    assert bundle["source_bundle_id"] == ""
