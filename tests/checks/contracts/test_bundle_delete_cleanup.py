from __future__ import annotations

import logging
from pathlib import Path
from textwrap import dedent

import pytest

from bundle_lifecycle_test_support import _bundle_yaml, _has_cleanup_record
from loopora.service import LooporaError
from loopora.service_types import LooporaConflictError
from loopora.settings import configure_logging
import loopora.service_cleanup_diagnostics as cleanup_diagnostics


def test_bundle_delete_cleans_imported_group_but_keeps_unrelated_assets(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    manual_role = service.create_role_definition(
        name="Manual Builder",
        description="Unrelated role",
        archetype="builder",
        prompt_markdown=dedent(
            """\
            ---
            version: 1
            archetype: builder
            ---

            Keep going.
            """
        ),
    )
    manual_orchestration = service.create_orchestration(
        name="Manual Flow",
        workflow={"preset": "build_first"},
    )
    manual_loop = service.create_loop(
        name="Manual Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=3,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        orchestration_id=manual_orchestration["id"],
    )

    other_workdir = sample_workdir.parent / "bundle-workdir"
    other_workdir.mkdir()
    imported = service.import_bundle_text(_bundle_yaml(other_workdir))

    deleted = service.delete_bundle(imported["id"])

    assert deleted == {"id": imported["id"], "deleted": True}
    assert service.get_role_definition(manual_role["id"])["name"] == "Manual Builder"
    assert service.get_orchestration(manual_orchestration["id"])["name"] == "Manual Flow"
    assert service.get_loop(manual_loop["id"])["name"] == "Manual Loop"
    with pytest.raises(LooporaError, match="unknown bundle"):
        service.get_bundle(imported["id"])


def test_bundle_delete_logs_noncritical_managed_dir_cleanup_failure(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
    caplog,
) -> None:
    service = service_factory(scenario="success")
    configure_logging()
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    original_rmtree = cleanup_diagnostics.shutil.rmtree

    def fail_bundle_dir_rmtree(path: Path) -> None:
        if Path(path).name == imported["id"]:
            raise OSError("forced managed dir cleanup failure")
        original_rmtree(path)

    monkeypatch.setattr(cleanup_diagnostics.shutil, "rmtree", fail_bundle_dir_rmtree)
    with caplog.at_level(logging.WARNING, logger="loopora.service_bundle_assets"):
        deleted = service.delete_bundle(imported["id"])

    assert deleted["id"] == imported["id"]
    assert deleted["deleted"] is True
    assert deleted["local_cleanup"] == "partial_failed"
    assert deleted["cleanup_warnings"][0]["operation"] == "bundle_managed_dir_delete"
    assert "forced managed dir cleanup failure" in deleted["cleanup_warnings"][0]["error"]
    assert _has_cleanup_record(
        caplog,
        operation="bundle_managed_dir_delete",
        resource_type="path",
        owner_id=imported["id"],
    )


def test_bundle_delete_reports_linked_artifact_cleanup_failure(
    service_factory,
    sample_workdir: Path,
    tmp_path: Path,
    monkeypatch,
    caplog,
) -> None:
    service = service_factory(scenario="success")
    configure_logging()
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    artifact_dir = tmp_path / "artifact-copy"
    artifact_dir.mkdir()
    original_rmtree = cleanup_diagnostics.shutil.rmtree

    def fake_preflight(bundle: dict, *, links) -> list[Path]:
        assert bundle["id"] == imported["id"]
        assert links is not None
        return [artifact_dir]

    def fail_artifact_rmtree(path: Path) -> None:
        if Path(path) == artifact_dir:
            raise OSError("forced linked artifact cleanup failure")
        original_rmtree(path)

    monkeypatch.setattr(service, "_preflight_bundle_graph_delete", fake_preflight)
    monkeypatch.setattr(cleanup_diagnostics.shutil, "rmtree", fail_artifact_rmtree)
    with caplog.at_level(logging.WARNING, logger="loopora.service_bundle_assets"):
        deleted = service.delete_bundle(imported["id"])

    assert deleted["id"] == imported["id"]
    assert deleted["deleted"] is True
    assert deleted["local_cleanup"] == "partial_failed"
    assert deleted["cleanup_warnings"][0]["operation"] == "bundle_link_artifact_delete"
    assert deleted["cleanup_warnings"][0]["resource_id"] == str(artifact_dir)
    assert "forced linked artifact cleanup failure" in deleted["cleanup_warnings"][0]["error"]
    assert _has_cleanup_record(
        caplog,
        operation="bundle_link_artifact_delete",
        resource_type="path",
        owner_id=imported["id"],
    )


def test_bundle_failed_import_cleanup_logs_and_preserves_original_error(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
    caplog,
) -> None:
    service = service_factory(scenario="success")
    configure_logging()
    original_create_role_definition = service.create_role_definition

    def fail_create_role_definition(*_args, **_kwargs):
        raise LooporaError("forced role import failure")

    def fail_rmtree(path: Path) -> None:
        raise OSError(f"cannot remove {Path(path).name}")

    service.create_role_definition = fail_create_role_definition
    monkeypatch.setattr(cleanup_diagnostics.shutil, "rmtree", fail_rmtree)

    with caplog.at_level(logging.WARNING, logger="loopora.service_bundle_assets"), pytest.raises(LooporaError, match="forced role import failure"):
        service.import_bundle_text(_bundle_yaml(sample_workdir))

    service.create_role_definition = original_create_role_definition
    assert _has_cleanup_record(caplog, operation="bundle_failed_import_cleanup", resource_type="path")


def test_bundle_failed_import_cleanup_diagnostic_failure_preserves_original_error(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    original_create_role_definition = service.create_role_definition

    def fail_create_role_definition(*_args, **_kwargs):
        raise LooporaError("forced role import failure")

    def fail_rmtree(path: Path) -> None:
        raise OSError(f"cannot remove {Path(path).name}")

    def fail_log_event(*_args, **_kwargs) -> None:
        raise RuntimeError("cleanup log sink down")

    service.create_role_definition = fail_create_role_definition
    monkeypatch.setattr(cleanup_diagnostics.shutil, "rmtree", fail_rmtree)
    monkeypatch.setattr(cleanup_diagnostics, "log_event", fail_log_event)
    try:
        with pytest.raises(LooporaError, match="forced role import failure"):
            service.import_bundle_text(_bundle_yaml(sample_workdir))
    finally:
        service.create_role_definition = original_create_role_definition


def test_bundle_import_rollback_diagnostics_preserve_original_error_for_unexpected_cleanup_failure(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
    caplog,
) -> None:
    service = service_factory(scenario="success")
    configure_logging()

    def fail_after_graph_creation(*_args, **_kwargs):
        raise LooporaError("forced import failure after graph creation")

    def fail_delete_loop(*_args, **_kwargs):
        raise RuntimeError("rollback loop deletion failed")

    monkeypatch.setattr(service, "derive_bundle_from_loop", fail_after_graph_creation)
    monkeypatch.setattr(service, "delete_loop", fail_delete_loop)

    with (
        caplog.at_level(logging.WARNING, logger="loopora.service_bundle_assets"),
        pytest.raises(
            LooporaError,
            match="forced import failure after graph creation",
        ),
    ):
        service.import_bundle_text(_bundle_yaml(sample_workdir))

    assert _has_cleanup_record(caplog, operation="bundle_import_rollback", resource_type="loop")


def test_bundle_delete_keeps_managed_dir_and_records_when_graph_delete_fails(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    bundle_dir = service._bundle_dir(imported["id"])
    assert bundle_dir.exists()
    loop_id = imported["loop_id"]
    orchestration_id = imported["orchestration_id"]
    role_definition_ids = list(imported["role_definition_ids"])

    def fail_delete_bundle_graph(bundle_id: str) -> bool:
        if bundle_id == imported["id"]:
            raise LooporaError("bundle graph delete failed")
        return True

    monkeypatch.setattr(service.repository, "delete_bundle_graph", fail_delete_bundle_graph)
    with pytest.raises(LooporaError, match="bundle graph delete failed"):
        service.delete_bundle(imported["id"])

    assert bundle_dir.exists()
    assert service.repository.get_bundle(imported["id"]) is not None
    assert service.repository.get_loop(loop_id) is not None
    assert service.repository.get_orchestration(orchestration_id) is not None
    assert all(service.repository.get_role_definition(role_id) is not None for role_id in role_definition_ids)


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
