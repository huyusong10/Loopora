from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.bundles import bundle_to_yaml
from loopora.settings import app_home
from loopora.web import build_app


def test_bundle_form_import_and_edit_flow(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Bundle Form Source",
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
            name="Form Bundle",
            description="Imported through the HTML form.",
            collaboration_summary="Prefer compact but convincing evidence.",
        )
    )

    client = TestClient(build_app(service=service))
    import_response = client.post("/bundles/import", data={"bundle_yaml": bundle_yaml}, follow_redirects=False)

    assert import_response.status_code == HTTPStatus.SEE_OTHER
    bundle_location = import_response.headers["location"]
    bundle_id = bundle_location.rsplit("/", 1)[-1]
    bundle = service.get_bundle(bundle_id)
    assert bundle["name"] == "Form Bundle"

    edit_response = client.post(
        f"/bundles/{bundle_id}/edit",
        data={
            "description": "Updated bundle description.",
            "collaboration_summary": "Take fake done seriously.",
            "spec_markdown": "# Task\n\nShip the update.\n\n# Done When\n- It works.\n",
        },
        follow_redirects=False,
    )

    assert edit_response.status_code == HTTPStatus.SEE_OTHER
    updated_bundle = service.get_bundle(bundle_id)
    assert updated_bundle["description"] == "Updated bundle description."
    assert updated_bundle["collaboration_summary"] == "Take fake done seriously."
    spec_path = app_home() / "bundles" / bundle_id / "spec.md"
    assert spec_path.read_text(encoding="utf-8").startswith("# Task")


def test_bundle_derive_form_encodes_query_values(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

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


def test_create_loop_page_imports_bundle_as_loop_creation_flow(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    source_loop = service.create_loop(
        name="Create Page Bundle Source",
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
            source_loop["id"],
            name="Create Page Bundle",
            description="Imported from the unified create loop page.",
            collaboration_summary="Create loop and bundle import share one entry.",
        )
    )

    client = TestClient(build_app(service=service))
    import_response = client.post(
        "/loops/new/import-bundle",
        data={"bundle_yaml": bundle_yaml, "start_immediately": ""},
        follow_redirects=False,
    )

    assert import_response.status_code == HTTPStatus.SEE_OTHER
    assert import_response.headers["location"].startswith("/loops/")
    imported_bundle = next(bundle for bundle in service.list_bundles() if bundle["name"] == "Create Page Bundle")
    assert import_response.headers["location"] == f"/loops/{imported_bundle['loop_id']}"
    assert service.get_loop(imported_bundle["loop_id"])["name"] == "Create Page Bundle Source"
