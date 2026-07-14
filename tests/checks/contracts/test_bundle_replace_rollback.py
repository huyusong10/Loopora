from __future__ import annotations

from pathlib import Path

import pytest

from bundle_lifecycle_test_support import _bundle_yaml
from loopora.service import LooporaError
from loopora.service_bundle_import import PLAN_FILE_IMPORT_ERROR
from loopora.service_types import LooporaWorkdirUnavailableError


def test_failed_bundle_replace_preserves_existing_bundle(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    original_loop_id = imported["loop_id"]
    original_orchestration_id = imported["orchestration_id"]
    original_role_ids = list(imported["role_definition_ids"])
    original_custom_role_count = len([role for role in service.list_role_definitions() if role["source"] == "custom"])
    original_custom_orchestration_count = len([orchestration for orchestration in service.list_orchestrations() if orchestration["source"] == "custom"])
    original_loop_count = len(service.list_loops())
    missing_workdir = sample_workdir.parent / "missing-workdir"

    with pytest.raises(LooporaWorkdirUnavailableError) as exc_info:
        service.import_bundle_text(
            _bundle_yaml(
                missing_workdir,
                collaboration_summary="This replacement should not destroy the old bundle.",
            ),
            replace_bundle_id=imported["id"],
        )
    assert exc_info.value.action == "compose"
    assert exc_info.value.workdir_state == "missing"
    assert str(missing_workdir.resolve(strict=False)) not in str(exc_info.value)

    preserved = service.get_bundle(imported["id"])
    assert preserved["loop_id"] == original_loop_id
    assert preserved["orchestration_id"] == original_orchestration_id
    assert preserved["role_definition_ids"] == original_role_ids
    assert service.get_loop(original_loop_id)["id"] == original_loop_id
    assert service.get_orchestration(original_orchestration_id)["id"] == original_orchestration_id
    assert [role["id"] for role in preserved["role_definitions"]] == original_role_ids
    assert service.export_bundle(imported["id"])["collaboration_summary"].startswith("Prefer evidence")
    assert len([role for role in service.list_role_definitions() if role["source"] == "custom"]) == original_custom_role_count
    assert len([orchestration for orchestration in service.list_orchestrations() if orchestration["source"] == "custom"]) == original_custom_orchestration_count
    assert len(service.list_loops()) == original_loop_count


def test_bundle_replace_rolls_back_when_graph_transaction_fails(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    original_loop_id = imported["loop_id"]
    original_orchestration_id = imported["orchestration_id"]
    original_role_ids = list(imported["role_definition_ids"])
    original_custom_role_count = len([role for role in service.list_role_definitions() if role["source"] == "custom"])

    def fail_replace_bundle_graph(bundle_id: str, _payload: dict) -> bool:
        if bundle_id == imported["id"]:
            raise LooporaError("forced graph transaction failure")
        return True

    service.repository.replace_bundle_graph = fail_replace_bundle_graph
    with pytest.raises(LooporaError, match="forced graph transaction failure"):
        service.import_bundle_text(
            _bundle_yaml(
                sample_workdir,
                collaboration_summary="This replacement should roll back after save.",
            ),
            replace_bundle_id=imported["id"],
        )

    preserved = service.get_bundle(imported["id"])
    assert preserved["revision"] == imported["revision"]
    assert preserved["loop_id"] == original_loop_id
    assert preserved["orchestration_id"] == original_orchestration_id
    assert preserved["role_definition_ids"] == original_role_ids
    assert service.export_bundle(imported["id"])["collaboration_summary"].startswith("Prefer evidence")
    assert len([role for role in service.list_role_definitions() if role["source"] == "custom"]) == original_custom_role_count


def test_bundle_replace_preserves_existing_plan_files_when_import_yaml_write_fails(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    yaml_path = service._bundle_yaml_path(imported["id"])
    spec_path = service._bundle_spec_path(imported["id"])
    original_yaml = yaml_path.read_text(encoding="utf-8")
    original_spec = spec_path.read_text(encoding="utf-8")
    original_loop_id = imported["loop_id"]
    original_orchestration_id = imported["orchestration_id"]
    original_role_ids = list(imported["role_definition_ids"])
    original_replace = Path.replace

    def fail_bundle_yaml_replace(path: Path, target: Path) -> Path:
        if Path(target) == yaml_path and Path(path).name.startswith(f".{yaml_path.name}.tmp."):
            raise OSError(f"permission denied: {yaml_path}")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_bundle_yaml_replace)

    with pytest.raises(LooporaError, match=PLAN_FILE_IMPORT_ERROR):
        service.import_bundle_text(
            _bundle_yaml(
                sample_workdir,
                collaboration_summary="This replacement must not damage the old Plan File.",
            ),
            replace_bundle_id=imported["id"],
        )

    preserved = service.get_bundle(imported["id"])
    assert preserved["loop_id"] == original_loop_id
    assert preserved["orchestration_id"] == original_orchestration_id
    assert preserved["role_definition_ids"] == original_role_ids
    assert yaml_path.read_text(encoding="utf-8") == original_yaml
    assert spec_path.read_text(encoding="utf-8") == original_spec
    assert not list(yaml_path.parent.glob(f".{yaml_path.name}.tmp.*"))
    assert service.export_bundle(imported["id"])["collaboration_summary"].startswith("Prefer evidence")
