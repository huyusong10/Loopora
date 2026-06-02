from __future__ import annotations

import json
from http import HTTPStatus
from pathlib import Path
from urllib.parse import quote

from fastapi.testclient import TestClient

from loopora.web import build_app

from web_bundle_detail_test_support import create_bundle_detail_loop, import_derived_bundle


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
    assert orchestration_response.status_code == HTTPStatus.SEE_OTHER
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
    assert role_response.status_code == HTTPStatus.SEE_OTHER
    assert role_response.headers["location"] == f"/bundles/{imported['id']}?surface_updated=role%3A{role_definition['id']}"


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
