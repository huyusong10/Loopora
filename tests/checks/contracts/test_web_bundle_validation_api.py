from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from loopora.bundles import bundle_to_yaml
from loopora.web import build_app


def test_api_bundle_file_inputs_reject_invalid_utf8(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    bundle_path = tmp_path / "broken-bundle.yaml"
    bundle_path.write_bytes(b"\xff")
    client = TestClient(build_app(service=service))

    preview_response = client.post("/api/bundles/preview", json={"bundle_path": str(bundle_path)})
    assert preview_response.status_code == HTTPStatus.OK
    preview_payload = preview_response.json()
    assert preview_payload["ok"] is False
    assert "UTF-8 encoded YAML" in preview_payload["error"]

    import_response = client.post("/api/bundles/import", json={"bundle_path": str(bundle_path)})
    assert import_response.status_code == HTTPStatus.BAD_REQUEST
    assert "UTF-8 encoded YAML" in import_response.json()["error"]


def test_api_bundle_preview_and_import_report_invalid_version_without_500(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    invalid_yaml = "version: not-a-number\nmetadata:\n  name: Broken Bundle\n"

    preview_response = client.post("/api/bundles/preview", json={"bundle_yaml": invalid_yaml})
    assert preview_response.status_code == HTTPStatus.OK
    assert preview_response.json() == {"ok": False, "error": "bundle version must be an integer"}

    import_response = client.post("/api/bundles/import", json={"bundle_yaml": invalid_yaml})
    assert import_response.status_code == HTTPStatus.BAD_REQUEST
    assert import_response.json()["error"] == "bundle version must be an integer"


@pytest.mark.parametrize(
    ("replace_bundle_id", "expected_error"),
    [
        (False, "bundle replace_bundle_id must be a string"),
        ("../escape", "bundle replace_bundle_id must use letters, numbers, dot, underscore, or dash"),
    ],
)
def test_api_bundle_import_rejects_invalid_replace_bundle_id(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    replace_bundle_id: object,
    expected_error: str,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Bundle Replace Source",
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
            name="Replacement Bundle",
            description="Bundle import with invalid replace id.",
            collaboration_summary="Keep replace targets explicit.",
        )
    )
    client = TestClient(build_app(service=service))

    import_response = client.post(
        "/api/bundles/import",
        json={"bundle_yaml": bundle_yaml, "replace_bundle_id": replace_bundle_id},
    )

    assert import_response.status_code == HTTPStatus.BAD_REQUEST
    assert import_response.json()["error"] == expected_error
