from __future__ import annotations

import json
import logging
from pathlib import Path
from textwrap import dedent

import pytest

from bundle_lifecycle_test_support import _bundle_yaml, _has_cleanup_record
from loopora.bundles import bundle_to_yaml
from loopora.service import LooporaError
from loopora.settings import app_home, configure_logging
import loopora.service_cleanup_diagnostics as cleanup_diagnostics


def test_bundle_replace_updates_plan_without_advancing_revision(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))

    revised = service.import_bundle_text(
        _bundle_yaml(
            sample_workdir,
            collaboration_summary="Prefer maintainability over shallow pass signals.",
        ),
        replace_bundle_id=imported["id"],
    )

    assert revised["id"] == imported["id"]
    assert revised["revision"] == imported["revision"]
    assert revised["source_bundle_id"] == ""
    exported = service.export_bundle(revised["id"])
    assert exported["collaboration_summary"].startswith("Prefer maintainability")


def test_bundle_replace_logs_backup_cleanup_runtime_failure_without_failing(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
    caplog,
) -> None:
    service = service_factory(scenario="success")
    configure_logging()
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    original_rmtree = cleanup_diagnostics.shutil.rmtree

    def fail_backup_rmtree(path: Path) -> None:
        target = Path(path)
        if target.name.startswith(f"{imported['id']}.backup_"):
            raise RuntimeError("backup cleanup crashed")
        original_rmtree(path)

    monkeypatch.setattr(cleanup_diagnostics.shutil, "rmtree", fail_backup_rmtree)

    with caplog.at_level(logging.WARNING, logger="loopora.service_bundle_assets"):
        revised = service.import_bundle_text(
            _bundle_yaml(
                sample_workdir,
                collaboration_summary="Prefer resilient replacement cleanup diagnostics.",
            ),
            replace_bundle_id=imported["id"],
        )

    assert revised["id"] == imported["id"]
    records = [
        {
            "event": getattr(record, "event", ""),
            "context": getattr(record, "context", {}) or {},
        }
        for record in caplog.records
    ]
    log_path = app_home() / "logs" / "service.log"
    if log_path.exists():
        records.extend(json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip())
    assert any(
        record.get("event") == "service.cleanup.failed"
        and (record.get("context") or {}).get("operation") == "bundle_backup_cleanup"
        and (record.get("context") or {}).get("resource_type") == "path"
        and (record.get("context") or {}).get("owner_id") == imported["id"]
        and (record.get("context") or {}).get("error_type") == "RuntimeError"
        for record in records
    )


def test_legacy_bundle_lineage_metadata_imports_but_new_exports_omit_lineage(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    source = service.import_bundle_text(_bundle_yaml(sample_workdir))
    legacy_yaml = (
        _bundle_yaml(
            sample_workdir,
            collaboration_summary="Prefer stronger evidence coverage before revising again.",
        )
        .replace(
            'metadata:\n  name: "Guided Inspect First"\n  description: "Bundle created from task-scoped alignment."',
            "metadata:\n"
            '  name: "Guided Inspect First Revision"\n'
            '  description: "Bundle revision with tighter evidence language."\n'
            f'  source_bundle_id: "{source["id"]}"\n'
            f"  revision: {source['revision'] + 1}",
        )
        .replace(
            "- The implementation stays maintainable for the next round.",
            "- The implementation stays maintainable for the next round.\n            - Evidence coverage is visible before another revision starts.",
        )
    )
    imported = service.import_bundle_text(legacy_yaml)
    exported_yaml = bundle_to_yaml(service.export_bundle(imported["id"]))
    summary = service.get_bundle_revision_summary(imported["id"])

    assert imported["source_bundle_id"] == ""
    assert imported["revision"] == 1
    assert "source_bundle_id" not in exported_yaml
    assert "revision:" not in exported_yaml
    assert summary["lineage_state"] == "not_tracked"
    assert summary["source_bundle_id"] == ""
    assert summary["can_compare"] is False
    assert summary["surface_deltas"] == []


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

    with pytest.raises(LooporaError, match="workdir does not exist"):
        service.import_bundle_text(
            _bundle_yaml(
                missing_workdir,
                collaboration_summary="This replacement should not destroy the old bundle.",
            ),
            replace_bundle_id=imported["id"],
        )

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


def test_bundle_owned_assets_cannot_be_deleted_individually(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    role_definition = imported["role_definitions"][0]
    orchestration = imported["orchestration"]

    with pytest.raises(LooporaError, match=f"bundle {imported['id']}"):
        service.delete_loop(imported["loop_id"])
    with pytest.raises(LooporaError, match=f"bundle {imported['id']}"):
        service.delete_orchestration(orchestration["id"])
    with pytest.raises(LooporaError, match=f"bundle {imported['id']}"):
        service.delete_role_definition(role_definition["id"])


def test_imported_role_definition_changes_update_bundle_without_revision_bump(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    role_definition = imported["role_definitions"][0]

    updated_role = service.update_role_definition(
        role_definition["id"],
        name=role_definition["name"],
        description=role_definition["description"],
        archetype=role_definition["archetype"],
        prompt_ref=role_definition["prompt_ref"],
        prompt_markdown=role_definition["prompt_markdown"],
        posture_notes="Raise the refactor bar before passing this work.",
        executor_kind=role_definition["executor_kind"],
        executor_mode=role_definition["executor_mode"],
        command_cli=role_definition["command_cli"],
        command_args_text=role_definition["command_args_text"],
        model=role_definition["model"],
        reasoning_effort=role_definition["reasoning_effort"],
    )

    refreshed = service.get_bundle(imported["id"])
    exported = service.export_bundle(imported["id"])
    exported_role = next(item for item in exported["role_definitions"] if item["name"] == updated_role["name"])

    assert updated_role["posture_notes"] == "Raise the refactor bar before passing this work."
    assert refreshed["revision"] == imported["revision"]
    assert "Raise the refactor bar" in exported_role["posture_notes"]


def test_imported_orchestration_changes_update_bundle_without_revision_bump(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    orchestration = imported["orchestration"]
    workflow = dict(orchestration["workflow_json"])
    workflow["collaboration_intent"] = "Inspect first, then only ship maintainable changes."

    updated_orchestration = service.update_orchestration(
        orchestration["id"],
        name=orchestration["name"],
        description=orchestration["description"],
        workflow=workflow,
        prompt_files=orchestration["prompt_files_json"],
        role_models=orchestration.get("role_models_json"),
    )

    refreshed = service.get_bundle(imported["id"])
    exported = service.export_bundle(imported["id"])

    assert updated_orchestration["workflow_json"]["collaboration_intent"].startswith("Inspect first")
    assert refreshed["revision"] == imported["revision"]
    assert exported["workflow"]["collaboration_intent"].startswith("Inspect first")


def test_bundle_spec_edit_updates_runnable_loop_snapshot(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    revised_spec = dedent(
        """\
        # Task

        Ship the requested behavior and explicitly remove nearby duplication.

        # Done When

        - The primary experience completes successfully.
        - The refactor-sensitive path is covered by reproducible evidence.

        # Guardrails

        - Keep changes focused.
        """
    )

    service.update_bundle_spec_markdown(imported["id"], revised_spec)

    loop = service.get_loop(imported["loop_id"])
    assert "explicitly remove nearby duplication" in loop["spec_markdown"]
    run = service.start_run(imported["loop_id"])
    assert "explicitly remove nearby duplication" in run["spec_markdown"]


def test_bundle_role_definition_edit_updates_runnable_loop_snapshot(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    role_definition = next(role for role in imported["role_definitions"] if role["archetype"] == "builder")
    revised_prompt = role_definition["prompt_markdown"] + "\nRefuse shallow fixes that dodge refactoring evidence.\n"

    service.update_role_definition(
        role_definition["id"],
        name=role_definition["name"],
        description=role_definition["description"],
        archetype=role_definition["archetype"],
        prompt_ref=role_definition["prompt_ref"],
        prompt_markdown=revised_prompt,
        posture_notes="Raise the refactor bar before passing this work.",
        executor_kind=role_definition["executor_kind"],
        executor_mode=role_definition["executor_mode"],
        command_cli=role_definition["command_cli"],
        command_args_text=role_definition["command_args_text"],
        model=role_definition["model"],
        reasoning_effort=role_definition["reasoning_effort"],
    )

    loop = service.get_loop(imported["loop_id"])
    builder_role = next(role for role in loop["workflow_json"]["roles"] if role["role_definition_id"] == role_definition["id"])
    assert builder_role["posture_notes"] == "Raise the refactor bar before passing this work."
    assert "Refuse shallow fixes" in loop["prompt_files"][role_definition["prompt_ref"]]
    run = service.start_run(imported["loop_id"])
    assert "Refuse shallow fixes" in run["prompt_files"][role_definition["prompt_ref"]]


def test_bundle_orchestration_edit_updates_runnable_loop_snapshot(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    orchestration = imported["orchestration"]
    workflow = dict(orchestration["workflow_json"])
    workflow["collaboration_intent"] = "Inspect refactor risk before allowing implementation to pass."

    service.update_orchestration(
        orchestration["id"],
        name=orchestration["name"],
        description=orchestration["description"],
        workflow=workflow,
        prompt_files=orchestration["prompt_files_json"],
        role_models=orchestration.get("role_models_json"),
    )

    loop = service.get_loop(imported["loop_id"])
    assert loop["workflow_json"]["collaboration_intent"].startswith("Inspect refactor risk")
    run = service.start_run(imported["loop_id"])
    assert run["workflow_json"]["collaboration_intent"].startswith("Inspect refactor risk")


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
    assert _has_cleanup_record(
        caplog,
        operation="bundle_asset_update_rollback",
        resource_type="loop",
        owner_id=imported["id"],
    )


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
    assert _has_cleanup_record(
        caplog,
        operation="bundle_asset_update_rollback",
        resource_type="loop",
        owner_id=imported["id"],
    )


def test_derive_bundle_uses_saved_loop_spec_snapshot(
    service_factory,
    sample_spec_file: Path,
    sample_spec_text: str,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
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
        orchestration_id="builtin:build_first",
    )
    sample_spec_file.write_text(
        "# Task\n\nThis external source file changed after loop creation.\n",
        encoding="utf-8",
    )

    derived = service.derive_bundle_from_loop(loop["id"], name="Derived From Saved Snapshot")

    assert derived["spec"]["markdown"] == sample_spec_text.strip()


def test_derive_bundle_normalizes_saved_loop_workflow_before_projection(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
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
        orchestration_id="builtin:build_first",
    )
    workflow = json.loads(json.dumps(loop["workflow_json"]))
    workflow["steps"][0]["inherit_session"] = "false"
    with service.repository.transaction() as connection:
        connection.execute(
            "UPDATE loop_definitions SET workflow_json = ? WHERE id = ?",
            (json.dumps(workflow, ensure_ascii=False), loop["id"]),
        )

    derived = service.derive_bundle_from_loop(loop["id"], name="Derived From Saved Snapshot")

    assert derived["workflow"]["steps"][0]["inherit_session"] is False


def test_derive_bundle_keeps_role_definition_keys_consistent(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Parallel Review Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=3,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        orchestration_id="builtin:build_then_parallel_review",
    )

    derived = service.derive_bundle_from_loop(loop["id"], name="Derived Parallel Review")

    role_definition_keys = {role["key"] for role in derived["role_definitions"]}
    workflow_keys = {role["role_definition_key"] for role in derived["workflow"]["roles"]}
    assert workflow_keys <= role_definition_keys
    assert "contract-inspector" in role_definition_keys
    assert "evidence-inspector" in role_definition_keys


def test_derive_bundle_uses_saved_loop_workflow_and_prompt_snapshot(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    builder_prompt = dedent(
        """\
        ---
        version: 1
        archetype: builder
        ---

        Original builder prompt.
        """
    )
    gatekeeper_prompt = dedent(
        """\
        ---
        version: 1
        archetype: gatekeeper
        ---

        Original gatekeeper prompt.
        """
    )
    builder = service.create_role_definition(
        name="Manual Builder",
        description="Original builder role.",
        archetype="builder",
        prompt_markdown=builder_prompt,
    )
    gatekeeper = service.create_role_definition(
        name="Manual GateKeeper",
        description="Original gatekeeper role.",
        archetype="gatekeeper",
        prompt_markdown=gatekeeper_prompt,
    )
    orchestration = service.create_orchestration(
        name="Manual Flow",
        workflow={
            "version": 1,
            "collaboration_intent": "Original collaboration intent.",
            "roles": [
                {"id": "builder", "role_definition_id": builder["id"]},
                {"id": "gatekeeper", "role_definition_id": gatekeeper["id"]},
            ],
            "steps": [
                {"id": "build", "role_id": "builder"},
                {"id": "gate", "role_id": "gatekeeper", "on_pass": "finish_run"},
            ],
        },
    )
    loop = service.create_loop(
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
        orchestration_id=orchestration["id"],
    )
    changed_workflow = dict(orchestration["workflow_json"])
    changed_workflow["collaboration_intent"] = "Changed live orchestration intent."
    service.update_orchestration(
        orchestration["id"],
        name=orchestration["name"],
        description=orchestration["description"],
        workflow=changed_workflow,
        prompt_files=orchestration["prompt_files_json"],
    )
    service.update_role_definition(
        builder["id"],
        name=builder["name"],
        description=builder["description"],
        archetype=builder["archetype"],
        prompt_ref=builder["prompt_ref"],
        prompt_markdown=builder_prompt.replace("Original", "Changed live"),
        posture_notes=builder["posture_notes"],
        executor_kind=builder["executor_kind"],
        executor_mode=builder["executor_mode"],
        command_cli=builder["command_cli"],
        command_args_text=builder["command_args_text"],
        model=builder["model"],
        reasoning_effort=builder["reasoning_effort"],
    )

    derived = service.derive_bundle_from_loop(loop["id"], name="Derived From Saved Snapshot")
    derived_builder = next(role for role in derived["role_definitions"] if role["key"] == "builder")

    assert derived["workflow"]["collaboration_intent"] == "Original collaboration intent."
    assert "Original builder prompt." in derived_builder["prompt_markdown"]
    assert "Changed live" not in derived_builder["prompt_markdown"]
