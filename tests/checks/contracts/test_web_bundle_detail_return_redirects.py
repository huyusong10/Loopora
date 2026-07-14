from __future__ import annotations

import json
from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

from fastapi.testclient import TestClient

from loopora.web import build_app
from loopora.web_url_utils import with_query_params

from web_bundle_detail_test_support import create_bundle_detail_loop, import_derived_bundle


def _role_form_payload(role_definition: dict, *, name: str, prompt_ref: str) -> dict:
    return {
        "name": name,
        "description": role_definition.get("description", ""),
        "archetype": role_definition["archetype"],
        "prompt_ref": prompt_ref,
        "prompt_markdown": role_definition["prompt_markdown"],
        "posture_notes": role_definition.get("posture_notes", ""),
        "executor_kind": role_definition.get("executor_kind", "codex"),
        "executor_mode": role_definition.get("executor_mode", "preset"),
        "command_cli": role_definition.get("command_cli", ""),
        "command_args_text": role_definition.get("command_args_text", ""),
        "model": role_definition.get("model", ""),
        "reasoning_effort": role_definition.get("reasoning_effort", ""),
    }


def _assert_returned_to_bundle_surface(
    location: str,
    *,
    bundle_id: str,
    expected_surface_prefix: str,
    workdir: Path | None = None,
) -> None:
    parts = urlsplit(location)
    assert parts.path == f"/bundles/{bundle_id}"
    query = parse_qs(parts.query)
    if workdir is not None:
        assert query.get("workdir") == [str(workdir.resolve())]
    surface_updated = query.get("surface_updated", [""])[0]
    assert surface_updated.startswith(expected_surface_prefix)


def _assert_saved_editor_location(location: str, *, path_prefix: str, workdir: Path) -> None:
    parts = urlsplit(location)
    assert parts.path.startswith(path_prefix)
    assert parts.path.endswith("/edit")
    query = parse_qs(parts.query)
    assert query.get("workdir") == [str(workdir.resolve())]
    assert query.get("saved") == ["1"]


def test_bundle_owned_surface_edit_redirects_back_to_bundle_detail(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_bundle_detail_loop(
        service,
        sample_spec_file=sample_spec_file,
        sample_workdir=sample_workdir,
        name="Bundle Redirect Source",
    )
    imported = import_derived_bundle(
        service,
        loop["id"],
        name="Redirect Bundle",
        description="Bundle redirect test.",
        collaboration_summary="Return to the bundle detail after local surface edits.",
    )
    orchestration = imported["orchestration"]
    role_definition = imported["role_definitions"][0]
    client = TestClient(build_app(service=service))
    encoded_workdir = quote(str(sample_workdir.resolve()), safe="")

    return_to = quote(f"/bundles/{imported['id']}?token=secret-token&tab=workflow#surface", safe="")
    catalog_return_to = quote(f"/bundles/{imported['id']}?access_token=secret-token&tab=workflow", safe="")
    clean_catalog_return_to = with_query_params(
        f"/bundles/{imported['id']}?tab=workflow",
        workdir=str(sample_workdir.resolve()),
    )
    bundle_detail_page = client.get(f"/bundles/{imported['id']}")
    role_catalog_page = client.get(f"/roles?return_to={catalog_return_to}")
    role_editor_page = client.get(f"/roles/{role_definition['id']}/edit?return_to=/bundles/{imported['id']}")
    orchestration_catalog_page = client.get(f"/orchestrations?return_to=/bundles/{imported['id']}")
    orchestration_editor_page = client.get(f"/orchestrations/{orchestration['id']}/edit?return_to=/bundles/{imported['id']}")

    assert bundle_detail_page.status_code == HTTPStatus.OK
    assert role_catalog_page.status_code == HTTPStatus.OK
    assert role_editor_page.status_code == HTTPStatus.OK
    assert orchestration_catalog_page.status_code == HTTPStatus.OK
    assert orchestration_editor_page.status_code == HTTPStatus.OK
    bundle_detail_return_to = with_query_params(
        f"/bundles/{imported['id']}",
        workdir=str(sample_workdir.resolve()),
    )
    expected_orchestration_href = with_query_params(
        f"/orchestrations/{orchestration['id']}/edit",
        workdir=str(sample_workdir.resolve()),
        return_to=bundle_detail_return_to,
    ).replace("&", "&amp;")
    expected_role_href = with_query_params(
        f"/roles/{role_definition['id']}/edit",
        workdir=str(sample_workdir.resolve()),
        return_to=bundle_detail_return_to,
    ).replace("&", "&amp;")
    assert f'href="{expected_orchestration_href}"' in bundle_detail_page.text
    assert f'href="{expected_role_href}"' in bundle_detail_page.text
    assert "secret-token" not in role_catalog_page.text
    expected_create_role_href = with_query_params(
        "/roles/new",
        workdir=str(sample_workdir.resolve()),
        return_to=clean_catalog_return_to,
    ).replace("&", "&amp;")
    expected_role_action = with_query_params(
        f"/roles/{role_definition['id']}/edit",
        workdir=str(sample_workdir.resolve()),
        return_to=bundle_detail_return_to,
    ).replace("&", "&amp;")
    assert f'href="{expected_create_role_href}"' in role_catalog_page.text
    assert f'action="{expected_role_action}"' in role_editor_page.text
    assert f'data-api-action="/api/role-definitions/{role_definition["id"]}?workdir={encoded_workdir}"' in role_editor_page.text
    assert (
        f'<a class="ghost-button" href="{bundle_detail_return_to.replace("&", "&amp;")}" '
        'data-testid="role-definition-cancel-link" data-workdir-context-link="workdir">'
        in role_editor_page.text
    )
    expected_create_orchestration_href = with_query_params(
        "/orchestrations/new",
        workdir=str(sample_workdir.resolve()),
        return_to=bundle_detail_return_to,
    ).replace("&", "&amp;")
    expected_orchestration_action = with_query_params(
        f"/orchestrations/{orchestration['id']}/edit",
        workdir=str(sample_workdir.resolve()),
        return_to=bundle_detail_return_to,
    ).replace("&", "&amp;")
    assert f'href="{expected_create_orchestration_href}"' in orchestration_catalog_page.text
    assert f'action="{expected_orchestration_action}"' in orchestration_editor_page.text
    assert f'data-api-action="/api/orchestrations/{orchestration["id"]}?workdir={encoded_workdir}"' in orchestration_editor_page.text
    assert (
        f'<a class="ghost-button" href="{bundle_detail_return_to.replace("&", "&amp;")}" '
        'data-testid="orchestration-cancel-link" data-workdir-context-link="workdir">'
        in orchestration_editor_page.text
    )

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
    assert orchestration_response.status_code == HTTPStatus.SEE_OTHER
    _assert_returned_to_bundle_surface(
        orchestration_response.headers["location"],
        bundle_id=imported["id"],
        expected_surface_prefix="workflow",
        workdir=sample_workdir,
    )
    assert urlsplit(orchestration_response.headers["location"]).fragment == "surface"

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
    assert role_response.status_code == HTTPStatus.SEE_OTHER
    _assert_returned_to_bundle_surface(
        role_response.headers["location"],
        bundle_id=imported["id"],
        expected_surface_prefix="role:",
        workdir=sample_workdir,
    )


def test_bundle_owned_surface_create_and_template_derivation_redirect_back_to_bundle_detail(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_bundle_detail_loop(
        service,
        sample_spec_file=sample_spec_file,
        sample_workdir=sample_workdir,
        name="Bundle Create Redirect Source",
    )
    imported = import_derived_bundle(
        service,
        loop["id"],
        name="Create Redirect Bundle",
        description="Bundle create redirect test.",
        collaboration_summary="Return to the bundle detail after creating local surfaces.",
    )
    source_role_definition = imported["role_definitions"][0]
    source_orchestration = imported["orchestration"]
    builtin_role_definition = next(item for item in service.list_role_definitions() if item.get("source") == "builtin")
    client = TestClient(build_app(service=service))

    created_role_response = client.post(
        f"/roles/new?return_to=/bundles/{imported['id']}?token=secret-token",
        data=_role_form_payload(
            source_role_definition,
            name="Bundle Return Created Role",
            prompt_ref="bundle_return_created_role",
        ),
        follow_redirects=False,
    )
    assert created_role_response.status_code == HTTPStatus.SEE_OTHER
    assert "secret-token" not in created_role_response.headers["location"]
    _assert_returned_to_bundle_surface(
        created_role_response.headers["location"],
        bundle_id=imported["id"],
        expected_surface_prefix="role:",
        workdir=sample_workdir,
    )

    derived_role_response = client.post(
        f"/roles/{builtin_role_definition['id']}/edit?return_to=/bundles/{imported['id']}",
        data=_role_form_payload(
            builtin_role_definition,
            name="Bundle Return Derived Role",
            prompt_ref="bundle_return_derived_role",
        ),
        follow_redirects=False,
    )
    assert derived_role_response.status_code == HTTPStatus.SEE_OTHER
    _assert_returned_to_bundle_surface(
        derived_role_response.headers["location"],
        bundle_id=imported["id"],
        expected_surface_prefix="role:",
        workdir=sample_workdir,
    )

    created_orchestration_response = client.post(
        f"/orchestrations/new?return_to=/bundles/{imported['id']}?token=secret-token",
        data={
            "name": "Bundle Return Created Flow",
            "description": "Created from the bundle detail flow.",
            "workflow_json": json.dumps(source_orchestration["workflow_json"], ensure_ascii=False, indent=2),
            "prompt_files_json": json.dumps(source_orchestration["prompt_files_json"], ensure_ascii=False, indent=2),
        },
        follow_redirects=False,
    )
    assert created_orchestration_response.status_code == HTTPStatus.SEE_OTHER
    assert "secret-token" not in created_orchestration_response.headers["location"]
    _assert_returned_to_bundle_surface(
        created_orchestration_response.headers["location"],
        bundle_id=imported["id"],
        expected_surface_prefix="workflow",
        workdir=sample_workdir,
    )


def test_asset_editor_success_redirects_preserve_workdir_context(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    encoded_workdir = quote(str(sample_workdir.resolve()), safe="")
    builtin_role_definition = next(item for item in service.list_role_definitions() if item.get("source") == "builtin")
    builtin_orchestration = service.get_orchestration("builtin:build_first")

    role_response = client.post(
        f"/roles/new?workdir={encoded_workdir}",
        data=_role_form_payload(
            builtin_role_definition,
            name="Workdir Context Builder",
            prompt_ref="workdir_context_builder",
        ),
        follow_redirects=False,
    )

    assert role_response.status_code == HTTPStatus.SEE_OTHER
    _assert_saved_editor_location(
        role_response.headers["location"],
        path_prefix="/roles/",
        workdir=sample_workdir,
    )

    orchestration_response = client.post(
        f"/orchestrations/new?workdir={encoded_workdir}",
        data={
            "name": "Workdir Context Flow",
            "description": "Preserve the target project after saving.",
            "workflow_json": json.dumps(builtin_orchestration["workflow_json"], ensure_ascii=False, indent=2),
            "prompt_files_json": json.dumps(builtin_orchestration["prompt_files_json"], ensure_ascii=False, indent=2),
        },
        follow_redirects=False,
    )

    assert orchestration_response.status_code == HTTPStatus.SEE_OTHER
    _assert_saved_editor_location(
        orchestration_response.headers["location"],
        path_prefix="/orchestrations/",
        workdir=sample_workdir,
    )


def test_bundle_surface_return_to_rejects_external_redirects(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_bundle_detail_loop(
        service,
        sample_spec_file=sample_spec_file,
        sample_workdir=sample_workdir,
        name="Unsafe Return Source",
    )
    imported = import_derived_bundle(
        service,
        loop["id"],
        name="Unsafe Return Bundle",
        description="Return target safety.",
        collaboration_summary="Do not redirect outside the local console.",
    )
    orchestration = imported["orchestration"]
    role_definition = imported["role_definitions"][0]
    client = TestClient(build_app(service=service))

    orchestration_page = client.get(f"/orchestrations/{orchestration['id']}/edit?return_to=https://evil.example/phish")
    assert orchestration_page.status_code == HTTPStatus.OK
    assert "https://evil.example" not in orchestration_page.text
    assert (
        '<a class="ghost-button" href="/orchestrations" data-testid="orchestration-cancel-link" '
        'data-workdir-context-link="workdir">'
    ) in orchestration_page.text

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
    assert orchestration_response.status_code == HTTPStatus.SEE_OTHER
    assert orchestration_response.headers["location"] == f"/orchestrations/{orchestration['id']}/edit?saved=1"

    role_page = client.get(f"/roles/{role_definition['id']}/edit?return_to=//evil.example/phish")
    assert role_page.status_code == HTTPStatus.OK
    assert "evil.example" not in role_page.text
    assert (
        '<a class="ghost-button" href="/roles" data-testid="role-definition-cancel-link" '
        'data-workdir-context-link="workdir">'
    ) in role_page.text

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
    assert role_response.status_code == HTTPStatus.SEE_OTHER
    assert role_response.headers["location"] == f"/roles/{role_definition['id']}/edit?saved=1"
