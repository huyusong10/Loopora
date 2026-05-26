from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from loopora.bundles import bundle_to_yaml
from loopora.settings import app_home
from loopora.web import build_app

from web_api_test_support import (
    _assert_bundle_preview_control_summary,
)

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
    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["ok"] is True
    assert preview["metadata"]["name"] == "Imported Bundle"
    assert preview["bundle"]["loop"]["workdir"] == str(sample_workdir.resolve())
    assert preview["roles"]
    assert preview["workflow_preview"]["steps"]
    assert preview["spec_rendered_html"].strip()
    _assert_bundle_preview_control_summary(preview)

    import_response = client.post("/api/bundles/import", json={"bundle_yaml": bundle_yaml})

    assert import_response.status_code == 201
    bundle = import_response.json()["bundle"]
    assert bundle["name"] == "Imported Bundle"
    assert bundle["collaboration_summary"] == "Prefer evidence before declaring done."

    list_response = client.get("/api/bundles")
    assert list_response.status_code == 200
    listed_bundle = next(item for item in list_response.json() if item["id"] == bundle["id"])
    assert listed_bundle["loop_id"]
    assert "governance_summary" not in listed_bundle

    get_response = client.get(f"/api/bundles/{bundle['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == bundle["id"]

    export_response = client.get(f"/api/bundles/{bundle['id']}/export")
    assert export_response.status_code == 200
    assert "Imported Bundle" in export_response.text
    assert "Prefer evidence before declaring done." in export_response.text
    assert export_response.headers["content-type"].startswith("application/yaml")

    delete_response = client.delete(f"/api/bundles/{bundle['id']}")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True

    missing_response = client.get(f"/api/bundles/{bundle['id']}")
    assert missing_response.status_code == 404
    assert "unknown bundle" in missing_response.json()["error"]

def test_api_bundle_file_inputs_reject_invalid_utf8(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    bundle_path = tmp_path / "broken-bundle.yaml"
    bundle_path.write_bytes(b"\xff")
    client = TestClient(build_app(service=service))

    preview_response = client.post("/api/bundles/preview", json={"bundle_path": str(bundle_path)})
    assert preview_response.status_code == 200
    preview_payload = preview_response.json()
    assert preview_payload["ok"] is False
    assert "UTF-8 encoded YAML" in preview_payload["error"]

    import_response = client.post("/api/bundles/import", json={"bundle_path": str(bundle_path)})
    assert import_response.status_code == 400
    assert "UTF-8 encoded YAML" in import_response.json()["error"]

def test_api_bundle_preview_and_import_report_invalid_version_without_500(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    invalid_yaml = "version: not-a-number\nmetadata:\n  name: Broken Bundle\n"

    preview_response = client.post("/api/bundles/preview", json={"bundle_yaml": invalid_yaml})
    assert preview_response.status_code == 200
    assert preview_response.json() == {"ok": False, "error": "bundle version must be an integer"}

    import_response = client.post("/api/bundles/import", json={"bundle_yaml": invalid_yaml})
    assert import_response.status_code == 400
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

    assert import_response.status_code == 400
    assert import_response.json()["error"] == expected_error

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

    assert response.status_code == 200
    bundle = response.json()["bundle"]
    assert bundle["metadata"]["name"] == "Derived Bundle"
    assert bundle["collaboration_summary"] == "Treat fake done states as blockers."
    assert bundle["workflow"]["roles"]
    assert bundle["role_definitions"]

def test_task_alignment_skill_api_is_not_registered() -> None:
    client = TestClient(build_app())

    assert client.get("/api/skills/loopora-task-alignment").status_code == 404
    assert client.post("/api/skills/loopora-task-alignment/install", json={"target": "codex"}).status_code == 404
    assert client.get("/api/skills/loopora-task-alignment/download").status_code == 404

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

    assert import_response.status_code == 303
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

    assert edit_response.status_code == 303
    updated_bundle = service.get_bundle(bundle_id)
    assert updated_bundle["description"] == "Updated bundle description."
    assert updated_bundle["collaboration_summary"] == "Take fake done seriously."
    spec_path = app_home() / "bundles" / bundle_id / "spec.md"
    assert spec_path.read_text(encoding="utf-8").startswith("# Task")

def test_bundle_detail_stays_open_when_managed_spec_is_unreadable(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Bundle Broken Spec Source",
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
                name="Broken Spec Bundle",
                description="The managed spec file can be repaired from the detail page.",
                collaboration_summary="Keep the plan detail page usable.",
            )
        )
    )
    (app_home() / "bundles" / imported["id"] / "spec.md").write_bytes(b"\xff")

    response = TestClient(build_app(service=service)).get(f"/bundles/{imported['id']}")

    assert response.status_code == 200
    assert 'data-testid="bundle-detail-page"' in response.text
    assert 'data-testid="bundle-detail-form"' in response.text
    assert "bundle spec file could not be read" in response.text

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

    assert response.status_code == 303
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

    assert import_response.status_code == 303
    assert import_response.headers["location"].startswith("/loops/")
    imported_bundle = next(bundle for bundle in service.list_bundles() if bundle["name"] == "Create Page Bundle")
    assert import_response.headers["location"] == f"/loops/{imported_bundle['loop_id']}"
    assert service.get_loop(imported_bundle["loop_id"])["name"] == "Create Page Bundle Source"

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

    assert response.status_code == 200
    bundle = response.json()["bundle"]
    assert bundle["description"] == "After API update."
    assert bundle["collaboration_summary"] == "Updated collaboration summary."
    assert bundle["revision"] == imported["revision"]
    assert bundle["source_bundle_id"] == ""

def test_bundle_api_and_detail_hide_legacy_lineage_surfaces(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Bundle Lineage Source",
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
                name="Lineage Source Bundle",
                description="Original lineage source.",
                collaboration_summary="Original governance posture.",
            )
        )
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

    assert api_response.status_code == 200
    assert "revision_summary" not in api_response.json()
    assert api_response.json()["source_bundle_id"] == ""
    assert page_response.status_code == 200
    assert 'data-testid="bundle-revision-lineage"' not in page_response.text
    assert "Plan version" not in page_response.text
    assert 'data-testid="bundle-surface-diff"' not in page_response.text
    assert f'value="{source["id"]}"' not in page_response.text
    assert 'data-testid="bundle-revision-delta-summary"' not in page_response.text
    assert list_response.status_code == 200
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

def test_bundle_owned_surface_edit_redirects_back_to_bundle_detail(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Bundle Redirect Source",
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
                name="Redirect Bundle",
                description="Bundle redirect test.",
                collaboration_summary="Return to the bundle detail after local surface edits.",
            )
        )
    )
    orchestration = imported["orchestration"]
    role_definition = imported["role_definitions"][0]
    client = TestClient(build_app(service=service))

    return_to = quote(f"/bundles/{imported['id']}?token=secret-token&tab=workflow#surface", safe="")
    orchestration_response = client.post(
        f"/orchestrations/{orchestration['id']}/edit?return_to={return_to}",
        data={
            "name": orchestration["name"],
            "description": "Workflow tuned from bundle detail.",
            "workflow_json": json.dumps(orchestration["workflow_json"], ensure_ascii=False, indent=2),
            "prompt_files_json": json.dumps(orchestration["prompt_files_json"], ensure_ascii=False, indent=2),
        },
        follow_redirects=False,
    )
    assert orchestration_response.status_code == 303
    assert orchestration_response.headers["location"] == f"/bundles/{imported['id']}?tab=workflow&surface_updated=workflow#surface"

    role_response = client.post(
        f"/roles/{role_definition['id']}/edit?return_to=/bundles/{imported['id']}",
        data={
            "name": role_definition["name"],
            "description": role_definition["description"],
            "archetype": role_definition["archetype"],
            "prompt_ref": role_definition["prompt_ref"],
            "prompt_markdown": role_definition["prompt_markdown"],
            "posture_notes": "Tighten this role from the bundle detail flow.",
            "executor_kind": role_definition["executor_kind"],
            "executor_mode": role_definition["executor_mode"],
            "command_cli": role_definition["command_cli"],
            "command_args_text": role_definition["command_args_text"],
            "model": role_definition["model"],
            "reasoning_effort": role_definition["reasoning_effort"],
        },
        follow_redirects=False,
    )
    assert role_response.status_code == 303
    assert role_response.headers["location"] == f"/bundles/{imported['id']}?surface_updated=role%3A{role_definition['id']}"

def test_bundle_surface_return_to_rejects_external_redirects(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Unsafe Return Source",
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
                name="Unsafe Return Bundle",
                description="Return target safety.",
                collaboration_summary="Do not redirect outside the local console.",
            )
        )
    )
    orchestration = imported["orchestration"]
    role_definition = imported["role_definitions"][0]
    client = TestClient(build_app(service=service))

    orchestration_page = client.get(f"/orchestrations/{orchestration['id']}/edit?return_to=https://evil.example/phish")
    assert orchestration_page.status_code == 200
    assert "https://evil.example" not in orchestration_page.text

    orchestration_response = client.post(
        f"/orchestrations/{orchestration['id']}/edit?return_to=https://evil.example/phish",
        data={
            "name": orchestration["name"],
            "description": "Workflow tuned from an unsafe return target.",
            "workflow_json": json.dumps(orchestration["workflow_json"], ensure_ascii=False, indent=2),
            "prompt_files_json": json.dumps(orchestration["prompt_files_json"], ensure_ascii=False, indent=2),
        },
        follow_redirects=False,
    )
    assert orchestration_response.status_code == 303
    assert orchestration_response.headers["location"] == f"/orchestrations/{orchestration['id']}/edit?saved=1"

    role_page = client.get(f"/roles/{role_definition['id']}/edit?return_to=//evil.example/phish")
    assert role_page.status_code == 200
    assert "evil.example" not in role_page.text

    role_response = client.post(
        f"/roles/{role_definition['id']}/edit?return_to=//evil.example/phish",
        data={
            "name": role_definition["name"],
            "description": role_definition["description"],
            "archetype": role_definition["archetype"],
            "prompt_ref": role_definition["prompt_ref"],
            "prompt_markdown": role_definition["prompt_markdown"],
            "posture_notes": "Ignore the external return target.",
            "executor_kind": role_definition["executor_kind"],
            "executor_mode": role_definition["executor_mode"],
            "command_cli": role_definition["command_cli"],
            "command_args_text": role_definition["command_args_text"],
            "model": role_definition["model"],
            "reasoning_effort": role_definition["reasoning_effort"],
        },
        follow_redirects=False,
    )
    assert role_response.status_code == 303
    assert role_response.headers["location"] == f"/roles/{role_definition['id']}/edit?saved=1"

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

    assert response.status_code == 200
    disposition = response.headers["content-disposition"]
    assert disposition == 'attachment; filename="Bad-Name-injected.yml"'
    assert "\n" not in disposition
    assert "\r" not in disposition
    assert "/" not in disposition
