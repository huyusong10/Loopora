from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from bundle_derive_test_support import create_manual_loop


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
    loop = create_manual_loop(
        service,
        spec_path=sample_spec_file,
        workdir=sample_workdir,
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
