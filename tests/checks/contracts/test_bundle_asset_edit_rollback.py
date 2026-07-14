from __future__ import annotations

import logging
from pathlib import Path

import pytest

from bundle_lifecycle_test_support import _bundle_yaml, _has_cleanup_record
from loopora.branding import state_dir_for_workdir
from loopora.service import LooporaError
from loopora.service_bundle_export import PLAN_FILE_SAVE_ERROR
from loopora.settings import configure_logging


def test_invalid_bundle_orchestration_edit_rolls_back_asset_and_bundle(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    orchestration = imported["orchestration"]
    workflow = dict(orchestration["workflow_json"])
    workflow["steps"] = [dict(step) for step in workflow["steps"]]
    workflow["steps"][-1]["on_pass"] = "continue"

    with pytest.raises(LooporaError, match=r"action_policy\.can_finish_run=true requires on_pass=finish_run"):
        service.update_orchestration(
            orchestration["id"],
            name=orchestration["name"],
            description=orchestration["description"],
            workflow=workflow,
            prompt_files=orchestration["prompt_files_json"],
            role_models=orchestration.get("role_models_json"),
        )

    preserved_bundle = service.get_bundle(imported["id"])
    preserved_orchestration = service.get_orchestration(orchestration["id"])
    preserved_loop = service.get_loop(imported["loop_id"])
    assert preserved_bundle["revision"] == imported["revision"]
    assert preserved_orchestration["workflow_json"]["steps"][-1]["on_pass"] == "finish_run"
    assert preserved_loop["workflow_json"]["steps"][-1]["on_pass"] == "finish_run"


def test_bundle_spec_update_rolls_back_runnable_loop_when_bundle_record_update_fails(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    original_loop = service.get_loop(imported["loop_id"])
    original_spec_sidecar = service._bundle_spec_path(imported["id"]).read_text(encoding="utf-8")

    def fail_update_bundle(bundle_id: str, _payload: dict) -> dict | None:
        if bundle_id == imported["id"]:
            raise LooporaError("forced bundle record update failure")
        return service.repository.get_bundle(bundle_id)

    service.repository.update_bundle = fail_update_bundle

    with pytest.raises(LooporaError, match="forced bundle record update failure"):
        service.update_bundle_spec_markdown(
            imported["id"],
            "# Task\n\nThis failed edit must not reach the runnable Loop.\n\n# Done When\n\n- It is rolled back.\n",
        )

    preserved_loop = service.get_loop(imported["loop_id"])
    assert preserved_loop["spec_markdown"] == original_loop["spec_markdown"]
    assert service._bundle_spec_path(imported["id"]).read_text(encoding="utf-8") == original_spec_sidecar
    run = service.start_run(imported["loop_id"])
    assert run["spec_markdown"] == original_loop["spec_markdown"]
    assert "failed edit" not in run["spec_markdown"]


def test_bundle_spec_update_save_failure_preserves_existing_snapshots(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    original_loop = service.get_loop(imported["loop_id"])
    bundle_spec_path = service._bundle_spec_path(imported["id"])
    loop_spec_path = state_dir_for_workdir(sample_workdir) / "loops" / imported["loop_id"] / "spec.md"
    original_bundle_spec = bundle_spec_path.read_text(encoding="utf-8")
    original_loop_spec = loop_spec_path.read_text(encoding="utf-8")
    local_path = tmp_path / "private" / "spec.md"
    original_replace = Path.replace

    def fail_bundle_spec_replace(path: Path, target: Path) -> Path:
        if Path(target) == bundle_spec_path.resolve() and Path(path).name.startswith(f".{bundle_spec_path.name}.tmp."):
            raise OSError(f"permission denied: {local_path}")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_bundle_spec_replace)

    with pytest.raises(LooporaError, match=PLAN_FILE_SAVE_ERROR) as exc_info:
        service.update_bundle_spec_markdown(
            imported["id"],
            "# Task\n\nThis failed edit must not reach persisted snapshots.\n\n# Done When\n\n- It is rolled back.\n",
        )

    assert str(exc_info.value) == PLAN_FILE_SAVE_ERROR
    assert "permission denied" not in str(exc_info.value)
    assert str(local_path) not in str(exc_info.value)
    assert bundle_spec_path.read_text(encoding="utf-8") == original_bundle_spec
    assert loop_spec_path.read_text(encoding="utf-8") == original_loop_spec
    assert service.get_loop(imported["loop_id"])["spec_markdown"] == original_loop["spec_markdown"]
    assert not list(bundle_spec_path.parent.glob(f".{bundle_spec_path.name}.tmp.*"))


def test_bundle_snapshot_save_failure_rolls_back_refreshed_orchestration(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    original_orchestration = service.get_orchestration(imported["orchestration_id"])
    role_definition = imported["role_definitions"][0]
    original_get_role_definition = service.get_role_definition
    bundle_spec_path = service._bundle_spec_path(imported["id"])
    local_path = tmp_path / "private" / "spec.md"
    original_replace = Path.replace

    def refreshed_role_definition(role_definition_id: str) -> dict:
        definition = original_get_role_definition(role_definition_id)
        if role_definition_id == role_definition["id"]:
            definition = dict(definition)
            definition["name"] = f"{definition['name']} Refreshed"
        return definition

    def fail_bundle_spec_replace(path: Path, target: Path) -> Path:
        if Path(target) == bundle_spec_path.resolve() and Path(path).name.startswith(f".{bundle_spec_path.name}.tmp."):
            raise OSError(f"permission denied: {local_path}")
        return original_replace(path, target)

    monkeypatch.setattr(service, "get_role_definition", refreshed_role_definition)
    monkeypatch.setattr(Path, "replace", fail_bundle_spec_replace)

    with pytest.raises(LooporaError, match=PLAN_FILE_SAVE_ERROR):
        service.update_bundle_spec_markdown(
            imported["id"],
            "# Task\n\nThis failed edit must roll back every related snapshot.\n\n# Done When\n\n- It is rolled back.\n",
        )

    preserved_orchestration = service.get_orchestration(imported["orchestration_id"])
    assert preserved_orchestration["workflow_json"] == original_orchestration["workflow_json"]
    assert preserved_orchestration["prompt_files_json"] == original_orchestration["prompt_files_json"]
    assert all("Refreshed" not in str(role.get("name", "")) for role in preserved_orchestration["workflow_json"]["roles"])


def test_unlinked_bundle_spec_update_failure_preserves_sidecar(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    bundle_id = "bundle_unlinked_legacy"
    original_spec = "# Task\n\nKeep the legacy Plan File intact.\n"
    service.repository.create_bundle(
        {
            "id": bundle_id,
            "name": "Unlinked Legacy Bundle",
            "description": "Legacy imported Plan File without a runnable Loop.",
            "collaboration_summary": "Preserve local sidecars when record updates fail.",
            "workdir": str(sample_workdir),
            "loop_id": "",
            "orchestration_id": "",
            "role_definition_ids": [],
            "source_bundle_id": "",
            "revision": 1,
            "imported_from_path": "",
        }
    )
    spec_path = service._bundle_spec_path(bundle_id)
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(original_spec, encoding="utf-8")

    def fail_update_bundle(changed_bundle_id: str, _payload: dict) -> dict | None:
        if changed_bundle_id == bundle_id:
            raise LooporaError("forced unlinked bundle record update failure")
        return service.repository.get_bundle(changed_bundle_id)

    monkeypatch.setattr(service.repository, "update_bundle", fail_update_bundle)

    with pytest.raises(LooporaError, match="forced unlinked bundle record update failure"):
        service.update_bundle_spec_markdown(
            bundle_id,
            "# Task\n\nThis failed edit must not overwrite the legacy sidecar.\n",
        )

    assert spec_path.read_text(encoding="utf-8") == original_spec


def test_bundle_metadata_update_rolls_back_record_when_yaml_sync_fails(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    spec_path = service._bundle_spec_path(imported["id"])
    spec_path.unlink()

    def fail_sync(bundle_id: str) -> None:
        assert bundle_id == imported["id"]
        raise LooporaError("forced bundle yaml sync failure")

    monkeypatch.setattr(service, "_sync_bundle_yaml", fail_sync)

    with pytest.raises(LooporaError, match="forced bundle yaml sync failure"):
        service.update_bundle_metadata(
            imported["id"],
            description="This failed metadata edit should roll back.",
            collaboration_summary="This failed governance edit should roll back.",
        )

    preserved = service.get_bundle(imported["id"])
    assert preserved["description"] == imported["description"]
    assert preserved["collaboration_summary"] == imported["collaboration_summary"]
    assert not spec_path.exists()


def test_bundle_metadata_sync_failure_preserves_existing_plan_file(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    yaml_path = service._bundle_yaml_path(imported["id"])
    original_yaml = yaml_path.read_text(encoding="utf-8")
    original_replace = Path.replace

    def fail_bundle_yaml_replace(path: Path, target: Path) -> Path:
        if Path(target) == yaml_path and Path(path).name.startswith(f".{yaml_path.name}.tmp."):
            raise OSError(f"permission denied: {yaml_path}")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_bundle_yaml_replace)

    with pytest.raises(LooporaError, match=PLAN_FILE_SAVE_ERROR):
        service.update_bundle_metadata(
            imported["id"],
            description="This failed metadata edit should not rewrite the Plan File.",
            collaboration_summary="This failed governance edit should not rewrite the Plan File.",
        )

    preserved = service.get_bundle(imported["id"])
    assert preserved["description"] == imported["description"]
    assert preserved["collaboration_summary"] == imported["collaboration_summary"]
    assert yaml_path.read_text(encoding="utf-8") == original_yaml
    assert not list(yaml_path.parent.glob(f".{yaml_path.name}.tmp.*"))


def test_bundle_orchestration_update_rollback_snapshot_failure_logs_and_preserves_original_error(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
    caplog,
) -> None:
    service = service_factory(scenario="success")
    configure_logging()
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    orchestration = imported["orchestration"]
    workflow = dict(orchestration["workflow_json"])
    workflow["collaboration_intent"] = "This edit should roll back after bundle touch fails."

    def fail_touch_bundle(orchestration_id: str):
        assert orchestration_id == orchestration["id"]
        raise LooporaError("forced orchestration bundle touch failure")

    def fail_snapshot_sync(bundle_id: str):
        assert bundle_id == imported["id"]
        raise RuntimeError("rollback snapshot sync failed")

    monkeypatch.setattr(service, "_touch_bundle_for_orchestration", fail_touch_bundle)
    monkeypatch.setattr(service, "_sync_bundle_loop_snapshot", fail_snapshot_sync)

    with (
        caplog.at_level(logging.WARNING, logger="loopora.service_bundle_assets"),
        pytest.raises(
            LooporaError,
            match="forced orchestration bundle touch failure",
        ),
    ):
        service.update_orchestration(
            orchestration["id"],
            name=orchestration["name"],
            description=orchestration["description"],
            workflow=workflow,
            prompt_files=orchestration["prompt_files_json"],
            role_models=orchestration.get("role_models_json"),
        )

    preserved_orchestration = service.get_orchestration(orchestration["id"])
    assert preserved_orchestration["workflow_json"]["collaboration_intent"] == orchestration["workflow_json"]["collaboration_intent"]
    _assert_bundle_asset_rollback_logged(caplog, imported["id"])


def test_bundle_role_update_rollback_snapshot_failure_logs_and_preserves_original_error(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
    caplog,
) -> None:
    service = service_factory(scenario="success")
    configure_logging()
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    role_definition = next(role for role in imported["role_definitions"] if role["archetype"] == "builder")

    def fail_touch_bundle(role_definition_id: str):
        assert role_definition_id == role_definition["id"]
        raise LooporaError("forced role bundle touch failure")

    def fail_snapshot_sync(bundle_id: str):
        assert bundle_id == imported["id"]
        raise RuntimeError("rollback snapshot sync failed")

    monkeypatch.setattr(service, "_touch_bundle_for_role_definition", fail_touch_bundle)
    monkeypatch.setattr(service, "_sync_bundle_loop_snapshot", fail_snapshot_sync)

    with caplog.at_level(logging.WARNING, logger="loopora.service_bundle_assets"), pytest.raises(LooporaError, match="forced role bundle touch failure"):
        service.update_role_definition(
            role_definition["id"],
            name=role_definition["name"],
            description=role_definition["description"],
            archetype=role_definition["archetype"],
            prompt_ref=role_definition["prompt_ref"],
            prompt_markdown=role_definition["prompt_markdown"] + "\nThis edit should roll back.\n",
            posture_notes="This posture should roll back.",
            executor_kind=role_definition["executor_kind"],
            executor_mode=role_definition["executor_mode"],
            command_cli=role_definition["command_cli"],
            command_args_text=role_definition["command_args_text"],
            model=role_definition["model"],
            reasoning_effort=role_definition["reasoning_effort"],
        )

    preserved_role = service.get_role_definition(role_definition["id"])
    assert preserved_role["prompt_markdown"] == role_definition["prompt_markdown"]
    assert preserved_role["posture_notes"] == role_definition["posture_notes"]
    _assert_bundle_asset_rollback_logged(caplog, imported["id"])


def _assert_bundle_asset_rollback_logged(caplog, bundle_id: str) -> None:
    assert _has_cleanup_record(
        caplog,
        operation="bundle_asset_update_rollback",
        resource_type="loop",
        owner_id=bundle_id,
    )
