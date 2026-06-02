from __future__ import annotations

from pathlib import Path

from bundle_lifecycle_test_support import _bundle_yaml


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
