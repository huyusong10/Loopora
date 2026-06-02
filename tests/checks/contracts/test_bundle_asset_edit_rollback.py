from __future__ import annotations

import logging
from pathlib import Path

import pytest

from bundle_lifecycle_test_support import _bundle_yaml, _has_cleanup_record
from loopora.service import LooporaError
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
