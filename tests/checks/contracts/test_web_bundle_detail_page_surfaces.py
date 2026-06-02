from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.bundles import bundle_to_yaml
from loopora.settings import app_home
from loopora.web import build_app

from web_bundle_detail_test_support import create_bundle_detail_loop, import_derived_bundle


def test_bundle_detail_stays_open_when_managed_spec_is_unreadable(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_bundle_detail_loop(
        service,
        sample_spec_file=sample_spec_file,
        sample_workdir=sample_workdir,
        name="Bundle Broken Spec Source",
    )
    imported = import_derived_bundle(
        service,
        loop["id"],
        name="Broken Spec Bundle",
        description="The managed spec file can be repaired from the detail page.",
        collaboration_summary="Keep the plan detail page usable.",
    )
    (app_home() / "bundles" / imported["id"] / "spec.md").write_bytes(b"\xff")

    response = TestClient(build_app(service=service)).get(f"/bundles/{imported['id']}")

    assert response.status_code == HTTPStatus.OK
    assert 'data-testid="bundle-detail-page"' in response.text
    assert 'data-testid="bundle-detail-form"' in response.text
    assert "bundle spec file could not be read" in response.text


def test_bundle_api_and_detail_hide_legacy_lineage_surfaces(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_bundle_detail_loop(
        service,
        sample_spec_file=sample_spec_file,
        sample_workdir=sample_workdir,
        name="Bundle Lineage Source",
    )
    source = import_derived_bundle(
        service,
        loop["id"],
        name="Lineage Source Bundle",
        description="Original lineage source.",
        collaboration_summary="Original governance posture.",
    )
    legacy_yaml = bundle_to_yaml(
        service.derive_bundle_from_loop(
            loop["id"],
            name="Lineage Revision Bundle",
            description="Revision source should remain hidden.",
            collaboration_summary="Updated governance posture.",
        )
    ).replace(
        "metadata:\n  name: Lineage Revision Bundle\n  description: Revision source should remain hidden.",
        "metadata:\n"
        "  name: Lineage Revision Bundle\n"
        "  description: Revision source should remain hidden.\n"
        f"  source_bundle_id: {source['id']}\n"
        f"  revision: {source['revision'] + 1}",
    )
    imported = service.import_bundle_text(legacy_yaml)
    client = TestClient(build_app(service=service))

    api_response = client.get(f"/api/bundles/{imported['id']}")
    list_response = client.get("/bundles")
    page_response = client.get(f"/bundles/{imported['id']}")

    assert api_response.status_code == HTTPStatus.OK
    assert "revision_summary" not in api_response.json()
    assert api_response.json()["source_bundle_id"] == ""
    assert page_response.status_code == HTTPStatus.OK
    assert 'data-testid="bundle-revision-lineage"' not in page_response.text
    assert "Plan version" not in page_response.text
    assert 'data-testid="bundle-surface-diff"' not in page_response.text
    assert f'value="{source["id"]}"' not in page_response.text
    assert 'data-testid="bundle-revision-delta-summary"' not in page_response.text
    assert list_response.status_code == HTTPStatus.OK
    assert f'data-testid="bundle-exchange-item-{imported["id"]}"' in list_response.text
    assert 'data-testid="bundle-governance-failure"' not in list_response.text
    assert 'data-testid="bundle-governance-evidence"' not in list_response.text
    assert 'data-testid="bundle-governance-coverage"' not in list_response.text
    assert 'data-testid="bundle-governance-residual-risk"' not in list_response.text
    assert 'data-testid="bundle-governance-execution-strategy"' not in list_response.text
    assert 'data-testid="bundle-governance-local"' not in list_response.text
    assert 'data-testid="bundle-governance-workflow"' not in list_response.text
    assert 'data-testid="bundle-governance-gatekeeper"' not in list_response.text
    assert 'data-testid="bundle-governance-changed-surfaces"' not in list_response.text
