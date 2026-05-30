from __future__ import annotations

from loopora.bundles import normalize_bundle
from loopora.projections import LoopfileExportProjectionInput, build_loopfile_export_projection


def test_loopfile_export_projection_builds_valid_loopfile_from_loop_snapshot(tmp_path) -> None:
    loop = {
        "id": "loop_export",
        "name": "Export Loop",
        "workdir": str(tmp_path),
        "completion_mode": "gatekeeper",
        "executor_kind": "codex",
        "executor_mode": "preset",
        "max_iters": 3,
        "max_role_retries": 1,
        "spec_markdown": """
# Task

Export Loopfile from the Loop snapshot.

# Done When

- The exported Loopfile remains importable.
""",
    }
    workflow = {
        "version": 1,
        "collaboration_intent": "Build then judge from evidence.",
        "roles": [
            {
                "id": "builder",
                "name": "Builder Runtime Snapshot",
                "archetype": "builder",
                "prompt_ref": "builder.md",
                "role_definition_id": "role_builder",
            },
            {
                "id": "gatekeeper",
                "name": "GateKeeper Runtime Snapshot",
                "archetype": "gatekeeper",
                "prompt_ref": "gatekeeper.md",
                "role_definition_id": "role_gatekeeper",
            },
        ],
        "steps": [
            {
                "id": "builder_step",
                "role_id": "builder",
                "on_pass": "continue",
                "action_policy": {"workspace": "workspace_write", "can_block": False, "can_finish_run": False},
            },
            {
                "id": "gatekeeper_step",
                "role_id": "gatekeeper",
                "on_pass": "finish_run",
                "action_policy": {"workspace": "read_only", "can_block": True, "can_finish_run": True},
            },
        ],
    }
    role_definition_by_id = {
        "role_builder": {
            "description": "Builds the export proof.",
            "prompt_markdown": _prompt_markdown("builder", "Build with evidence."),
            "posture_notes": "Prefer importable Loopfile proof.",
        },
        "role_gatekeeper": {
            "description": "Judges the export proof.",
            "prompt_markdown": _prompt_markdown("gatekeeper", "Pass only with evidence."),
            "posture_notes": "Fail closed on invalid Loopfile output.",
        },
    }

    bundle = normalize_bundle(
        build_loopfile_export_projection(
            LoopfileExportProjectionInput(
                loop=loop,
                loop_id="loop_export",
                workflow=workflow,
                prompt_files={},
                role_definition_by_id=role_definition_by_id,
                name="Exported Loopfile",
                collaboration_summary="Treat Loopfile as an import/export projection.",
            )
        )
    )

    assert bundle["metadata"]["name"] == "Exported Loopfile"
    assert bundle["loop"]["name"] == "Export Loop"
    assert bundle["role_definitions"][0]["key"] == "builder"
    assert bundle["role_definitions"][0]["name"] == "Builder Runtime Snapshot"
    assert bundle["role_definitions"][0]["description"] == "Builds the export proof."
    assert bundle["workflow"]["roles"][1]["role_definition_key"] == "gatekeeper"
    assert bundle["workflow"]["steps"][1]["action_policy"]["can_finish_run"] is True


def _prompt_markdown(archetype: str, body: str) -> str:
    return f"""---
version: 1
archetype: {archetype}
---

{body}
"""
