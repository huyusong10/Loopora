from __future__ import annotations

from pathlib import Path

import pytest

from bundle_lifecycle_test_support import _bundle_yaml
from loopora.service_types import LooporaConflictError


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
