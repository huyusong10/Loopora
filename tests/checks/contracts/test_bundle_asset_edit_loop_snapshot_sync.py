from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from bundle_lifecycle_test_support import _bundle_yaml


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


def test_bundle_role_definition_edit_recovers_missing_managed_spec_sidecar(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    spec_path = service._bundle_spec_path(imported["id"])
    spec_path.unlink()
    role_definition = next(role for role in imported["role_definitions"] if role["archetype"] == "builder")

    service.update_role_definition(
        role_definition["id"],
        name=role_definition["name"],
        description=role_definition["description"],
        archetype=role_definition["archetype"],
        prompt_ref=role_definition["prompt_ref"],
        prompt_markdown=role_definition["prompt_markdown"] + "\nKeep recovered sidecars consistent with the runnable Loop.\n",
        posture_notes=role_definition["posture_notes"],
        executor_kind=role_definition["executor_kind"],
        executor_mode=role_definition["executor_mode"],
        command_cli=role_definition["command_cli"],
        command_args_text=role_definition["command_args_text"],
        model=role_definition["model"],
        reasoning_effort=role_definition["reasoning_effort"],
    )

    assert spec_path.exists()
    assert "Ship the requested behavior" in spec_path.read_text(encoding="utf-8")
    loop = service.get_loop(imported["loop_id"])
    assert "Keep recovered sidecars" in loop["prompt_files"][role_definition["prompt_ref"]]


def test_bundle_role_definition_edit_recovers_unreadable_managed_spec_sidecar(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    spec_path = service._bundle_spec_path(imported["id"])
    role_definition = next(role for role in imported["role_definitions"] if role["archetype"] == "builder")
    local_path = tmp_path / "private" / "spec.md"
    original_read_text = Path.read_text

    def fail_managed_spec_read(path: Path, *args: object, **kwargs: object) -> str:
        if path == spec_path:
            raise OSError(f"permission denied: {local_path}")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_managed_spec_read)

    service.update_role_definition(
        role_definition["id"],
        name=role_definition["name"],
        description=role_definition["description"],
        archetype=role_definition["archetype"],
        prompt_ref=role_definition["prompt_ref"],
        prompt_markdown=role_definition["prompt_markdown"] + "\nRecover unreadable sidecars from the runnable Loop.\n",
        posture_notes=role_definition["posture_notes"],
        executor_kind=role_definition["executor_kind"],
        executor_mode=role_definition["executor_mode"],
        command_cli=role_definition["command_cli"],
        command_args_text=role_definition["command_args_text"],
        model=role_definition["model"],
        reasoning_effort=role_definition["reasoning_effort"],
    )

    assert "Ship the requested behavior" in original_read_text(spec_path, encoding="utf-8")
    loop = service.get_loop(imported["loop_id"])
    assert "Recover unreadable sidecars" in loop["prompt_files"][role_definition["prompt_ref"]]


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
