from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.bundles import bundle_to_yaml
from loopora.web import build_app

from web_api_test_support import _assert_bundle_preview_control_summary


def test_api_bundles_import_export_and_delete(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Bundle Export Source",
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
    bundle_yaml = bundle_to_yaml(
        service.derive_bundle_from_loop(
            loop["id"],
            name="Imported Bundle",
            description="Bundle import from API.",
            collaboration_summary="Prefer evidence before declaring done.",
        )
    )

    client = TestClient(build_app(service=service))
    preview_response = client.post("/api/bundles/preview", json={"bundle_yaml": bundle_yaml})
    assert preview_response.status_code == HTTPStatus.OK
    preview = preview_response.json()
    assert preview["ok"] is True
    assert preview["metadata"]["name"] == "Imported Bundle"
    assert preview["bundle"]["loop"]["workdir"] == str(sample_workdir.resolve())
    assert preview["roles"]
    assert preview["workflow_preview"]["steps"]
    assert preview["spec_rendered_html"].strip()
    _assert_bundle_preview_control_summary(preview)

    import_response = client.post("/api/bundles/import", json={"bundle_yaml": bundle_yaml})

    assert import_response.status_code == HTTPStatus.CREATED
    bundle = import_response.json()["bundle"]
    assert bundle["name"] == "Imported Bundle"
    assert bundle["collaboration_summary"] == "Prefer evidence before declaring done."

    list_response = client.get("/api/bundles")
    assert list_response.status_code == HTTPStatus.OK
    listed_bundle = next(item for item in list_response.json() if item["id"] == bundle["id"])
    assert listed_bundle["loop_id"]
    assert "governance_summary" not in listed_bundle

    get_response = client.get(f"/api/bundles/{bundle['id']}")
    assert get_response.status_code == HTTPStatus.OK
    assert get_response.json()["id"] == bundle["id"]

    export_response = client.get(f"/api/bundles/{bundle['id']}/export")
    assert export_response.status_code == HTTPStatus.OK
    assert "Imported Bundle" in export_response.text
    assert "Prefer evidence before declaring done." in export_response.text
    assert export_response.headers["content-type"].startswith("application/yaml")

    delete_response = client.delete(f"/api/bundles/{bundle['id']}")
    assert delete_response.status_code == HTTPStatus.OK
    assert delete_response.json()["deleted"] is True

    missing_response = client.get(f"/api/bundles/{bundle['id']}")
    assert missing_response.status_code == HTTPStatus.NOT_FOUND
    assert "unknown bundle" in missing_response.json()["error"]


def test_bundle_export_sanitizes_download_filename(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Filename Source",
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
                name='Bad/Name" \r\n injected',
                description="Filename safety.",
                collaboration_summary="Export headers stay parseable.",
            )
        )
    )
    client = TestClient(build_app(service=service))

    response = client.get(f"/api/bundles/{imported['id']}/export")

    assert response.status_code == HTTPStatus.OK
    disposition = response.headers["content-disposition"]
    assert disposition == 'attachment; filename="Bad-Name-injected.yml"'
    assert "\n" not in disposition
    assert "\r" not in disposition
    assert "/" not in disposition
