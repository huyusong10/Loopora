from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import pytest

from bundle_lifecycle_test_support import _bundle_yaml
from loopora.service_types import LooporaConflictError
from web_api_test_support import _assert_web_delete_preview_action_projection
from web_loop_creation_api_test_support import loop_creation_role, loop_creation_step, loop_creation_workflow
from web_orchestration_api_test_support import (
    create_release_builder_role_definition,
    role_definition_snapshot_workflow,
    web_client,
)


def test_bundle_delete_refuses_unowned_linked_assets(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    bundle_dir = service._bundle_dir(imported["id"])

    with service.repository.transaction() as connection:
        connection.execute(
            "DELETE FROM bundle_asset_ownership WHERE bundle_id = ? AND asset_type = 'loop'",
            (imported["id"],),
        )

    with pytest.raises(LooporaConflictError, match="asset is unowned"):
        service.delete_bundle(imported["id"])

    assert bundle_dir.exists()
    assert service.repository.get_bundle(imported["id"]) is not None
    assert service.repository.get_loop(imported["loop_id"]) is not None


@pytest.mark.parametrize(
    ("asset_kind", "table_name", "expected_error"),
    [
        ("loop", "loop_definitions", "linked loop"),
        ("orchestration", "orchestration_definitions", "linked orchestration"),
        ("role_definition", "role_definitions", "linked role definitions"),
    ],
)
def test_bundle_delete_refuses_missing_linked_assets(
    service_factory,
    sample_workdir: Path,
    asset_kind: str,
    table_name: str,
    expected_error: str,
) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    bundle_dir = service._bundle_dir(imported["id"])
    asset_id = imported["role_definition_ids"][0] if asset_kind == "role_definition" else imported[f"{asset_kind}_id"]

    with service.repository.transaction() as connection:
        connection.execute(f"DELETE FROM {table_name} WHERE id = ?", (asset_id,))

    with pytest.raises(LooporaConflictError, match=expected_error):
        service.delete_bundle(imported["id"])

    assert bundle_dir.exists()
    assert service.repository.get_bundle(imported["id"]) is not None


def test_bundle_delete_refuses_active_linked_runs(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    bundle_dir = service._bundle_dir(imported["id"])
    run = service.start_run(imported["loop_id"])

    with pytest.raises(LooporaConflictError, match="active loop runs"):
        service.delete_bundle(imported["id"])

    assert bundle_dir.exists()
    assert service.repository.get_bundle(imported["id"]) is not None
    assert service.repository.get_run(run["id"])["status"] == "queued"


def test_bundle_delete_preview_reports_active_linked_run_blocker_without_mutating(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    run = service.start_run(imported["loop_id"])

    preview = service.preview_bundle_delete(imported["id"])

    assert preview["status"] == "dry_run"
    assert preview["delete_allowed"] is False
    assert preview["would_delete"] == {
        "bundle": imported["id"],
        "linked_loop": imported["loop_id"],
        "linked_orchestration": imported["orchestration_id"],
        "linked_role_definition_count": len(imported["role_definition_ids"]),
        "linked_role_definition_ids": imported["role_definition_ids"],
        "linked_run_count": 1,
        "linked_run_ids": [run["id"]],
    }
    assert preview["blocked_by_active_runs"] == [run["id"]]
    assert preview["blockers"] == [{"kind": "active_runs", "run_ids": [run["id"]]}]
    assert preview["does_not_delete"] == [
        "original_exported_yaml_file",
        "source_project_workdir",
        "non_bundle_owned_assets",
        "external_provider_history",
    ]
    response = web_client(service).get(f"/api/bundles/{imported['id']}/delete-preview")
    assert response.status_code == 200
    _assert_web_delete_preview_action_projection(response.json())
    assert service.repository.get_bundle(imported["id"]) is not None
    assert service.repository.get_run(run["id"])["status"] == "queued"


def test_bundle_delete_refuses_orchestration_referenced_by_external_loop(
    service_factory,
    sample_workdir: Path,
    sample_spec_file: Path,
) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    external_workdir = sample_workdir.parent / "external-loop-workdir"
    external_workdir.mkdir()
    external_loop = service.create_loop(
        name="External Loop",
        spec_path=sample_spec_file,
        workdir=external_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=3,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        orchestration_id=imported["orchestration_id"],
    )

    with pytest.raises(LooporaConflictError, match="referenced by loops"):
        service.delete_bundle(imported["id"])

    assert service.repository.get_bundle(imported["id"]) is not None
    assert service.repository.get_loop(external_loop["id"]) is not None


def test_bundle_delete_refuses_role_definitions_referenced_by_external_orchestration(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    role_definition_id = imported["role_definition_ids"][0]
    external_orchestration = service.create_orchestration(
        name="External Role Consumer",
        workflow={
            "preset": "custom",
            "roles": [{"id": "external_builder", "role_definition_id": role_definition_id}],
            "steps": [{"id": "external_step", "role_id": "external_builder"}],
        },
    )

    with pytest.raises(LooporaConflictError, match="shared role definitions"):
        service.delete_bundle(imported["id"])

    assert service.repository.get_bundle(imported["id"]) is not None
    assert service.repository.get_orchestration(external_orchestration["id"]) is not None


def test_role_definition_delete_preview_blocks_referenced_orchestrations(service_factory) -> None:
    service = service_factory(scenario="success")
    role_definition = create_release_builder_role_definition(service)
    orchestration = service.create_orchestration(
        name="Role Consumer",
        strategy_source=role_definition_snapshot_workflow(role_definition["id"]),
    )

    preview = service.preview_role_definition_delete(role_definition["id"])

    assert preview["delete_allowed"] is False
    assert preview["would_delete"] == {
        "role_definition": role_definition["id"],
        "referencing_orchestration_count": 1,
        "referencing_orchestration_ids": [orchestration["id"]],
    }
    assert preview["blockers"] == [{"kind": "referenced_by_orchestrations", "orchestration_ids": [orchestration["id"]]}]
    with pytest.raises(LooporaConflictError, match="referenced by orchestrations"):
        service.delete_role_definition(role_definition["id"])
    assert service.repository.get_role_definition(role_definition["id"]) is not None

    response = web_client(service).get(f"/api/role-definitions/{role_definition['id']}/delete-preview")
    assert response.status_code == 200
    payload = response.json()
    assert payload["delete_allowed"] is False
    _assert_web_delete_preview_action_projection(payload)


def test_orchestration_delete_preview_blocks_referenced_loops(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    orchestration = service.create_orchestration(
        name="Loop Consumer",
        strategy_source=_loop_runnable_workflow(),
    )
    loop = service.create_loop(
        name="Referenced Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=3,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        orchestration_id=orchestration["id"],
    )

    preview = service.preview_orchestration_delete(orchestration["id"])

    assert preview["delete_allowed"] is False
    assert preview["would_delete"] == {
        "orchestration": orchestration["id"],
        "referencing_loop_count": 1,
        "referencing_loop_ids": [loop["id"]],
    }
    assert preview["blockers"] == [{"kind": "referenced_by_loops", "loop_ids": [loop["id"]]}]
    with pytest.raises(LooporaConflictError, match="referenced by loops"):
        service.delete_orchestration(orchestration["id"])
    assert service.repository.get_orchestration(orchestration["id"]) is not None

    response = web_client(service).get(f"/api/orchestrations/{orchestration['id']}/delete-preview")
    assert response.status_code == 200
    payload = response.json()
    assert payload["delete_allowed"] is False
    _assert_web_delete_preview_action_projection(payload)


def test_unreferenced_role_and_orchestration_delete_previews_allow_deletion(service_factory) -> None:
    service = service_factory(scenario="success")
    role_definition = create_release_builder_role_definition(service)
    orchestration = service.create_orchestration(name="Disposable Flow", strategy_source=loop_creation_workflow())

    role_preview = service.preview_role_definition_delete(role_definition["id"])
    orchestration_preview = service.preview_orchestration_delete(orchestration["id"])
    client = web_client(service)
    role_response = client.get(f"/api/role-definitions/{role_definition['id']}/delete-preview")
    orchestration_response = client.get(f"/api/orchestrations/{orchestration['id']}/delete-preview")

    assert role_preview["delete_allowed"] is True
    assert role_preview["would_delete"]["referencing_orchestration_count"] == 0
    assert orchestration_preview["delete_allowed"] is True
    assert orchestration_preview["would_delete"]["referencing_loop_count"] == 0
    assert role_response.status_code == orchestration_response.status_code == 200
    _assert_web_delete_preview_action_projection(
        role_response.json(),
        expected_kind="delete_role_definition",
        expected_endpoint=f"/api/role-definitions/{quote(role_definition['id'], safe='')}",
    )
    _assert_web_delete_preview_action_projection(
        orchestration_response.json(),
        expected_kind="delete_orchestration",
        expected_endpoint=f"/api/orchestrations/{quote(orchestration['id'], safe='')}",
    )
    assert service.delete_role_definition(role_definition["id"])["deleted"] is True
    assert service.delete_orchestration(orchestration["id"])["id"] == orchestration["id"]


def _loop_runnable_workflow() -> dict:
    return loop_creation_workflow(
        roles=[
            loop_creation_role("builder", "Builder", "builder"),
            loop_creation_role("gatekeeper", "GateKeeper", "gatekeeper"),
        ],
        steps=[
            loop_creation_step("builder_step", "builder"),
            loop_creation_step("gatekeeper_step", "gatekeeper", on_pass="finish_run"),
        ],
    )
