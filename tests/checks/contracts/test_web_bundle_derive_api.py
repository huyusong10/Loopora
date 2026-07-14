from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

from fastapi.testclient import TestClient

from loopora.web import build_app

from web_bundle_detail_test_support import create_bundle_detail_loop


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


def test_bundle_derive_form_encodes_query_values(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    encoded_workdir = quote(str(sample_workdir.resolve()), safe="")

    response = client.post(
        "/bundles/derive",
        data={
            "loop_id": "loop&id=shadow",
            "name": "Bundle & Review",
            "description": "Use A&B evidence.",
            "collaboration_summary": "No query leakage.",
        },
        follow_redirects=False,
    )

    assert response.status_code == HTTPStatus.SEE_OTHER
    assert response.headers["location"] == (
        "/bundles/derive/export?loop_id=loop%26id%3Dshadow&name=Bundle+%26+Review&description=Use+A%26B+evidence.&collaboration_summary=No+query+leakage."
    )

    workdir_response = client.post(
        f"/bundles/derive?workdir={encoded_workdir}",
        data={"loop_id": "loop_download", "derive_action": "download"},
        follow_redirects=False,
    )
    assert workdir_response.status_code == HTTPStatus.SEE_OTHER
    assert workdir_response.headers["location"] == f"/bundles/derive/export?loop_id=loop_download&workdir={encoded_workdir}"


def test_bundle_derive_form_can_save_managed_plan_file_copy(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_bundle_detail_loop(
        service,
        sample_spec_file=sample_spec_file,
        sample_workdir=sample_workdir,
        name="Save Plan Source",
    )
    client = TestClient(build_app(service=service))

    response = client.post(
        "/bundles/derive",
        data={
            "loop_id": loop["id"],
            "name": "Saved Managed Plan",
            "description": "Saved as a managed plan file.",
            "collaboration_summary": "Keep generated plan files manageable.",
            "derive_action": "save",
        },
        follow_redirects=False,
    )

    assert response.status_code == HTTPStatus.SEE_OTHER
    assert response.headers["location"].startswith("/bundles/")
    assert parse_qs(urlsplit(response.headers["location"]).query).get("created_from_loop") == ["1"]
    bundle_id = response.headers["location"].split("?", 1)[0].rsplit("/", 1)[-1]
    saved = service.get_bundle(bundle_id)
    assert saved["name"] == "Saved Managed Plan"
    assert saved["loop_id"] != loop["id"]
    assert service.get_loop(loop["id"])["name"] == "Save Plan Source"
    page_response = client.get(response.headers["location"])
    assert page_response.status_code == HTTPStatus.OK
    assert 'data-testid="bundle-created-from-loop-feedback"' in page_response.text
