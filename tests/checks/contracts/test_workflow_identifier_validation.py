from __future__ import annotations

import pytest

from loopora.workflows import WorkflowError, normalize_workflow


def test_normalize_workflow_rejects_duplicate_step_ids() -> None:
    with pytest.raises(WorkflowError, match="duplicate workflow step id: shared_step"):
        normalize_workflow(
            {
                "version": 1,
                "roles": [
                    {"id": "builder", "archetype": "builder", "prompt_ref": "builder.md"},
                    {"id": "gatekeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
                ],
                "steps": [
                    {"id": "shared_step", "role_id": "builder"},
                    {"id": "shared_step", "role_id": "gatekeeper", "on_pass": "finish_run"},
                ],
            }
        )


@pytest.mark.parametrize(
    ("field_update", "message"),
    [
        ({"roles": [{"id": "builder/escape", "archetype": "builder", "prompt_ref": "builder.md"}]}, "workflow role id"),
        ({"steps": [{"id": "../escape", "role_id": "builder"}]}, "workflow step id"),
        ({"steps": [{"id": "builder_step", "role_id": "builder", "parallel_group": "pack/escape"}]}, "workflow step parallel_group"),
        (
            {
                "controls": [
                    {
                        "id": "control/escape",
                        "when": {"signal": "no_evidence_progress"},
                        "call": {"role_id": "inspector"},
                    }
                ]
            },
            "workflow control id",
        ),
    ],
)
def test_normalize_workflow_rejects_unsafe_stable_identifiers(field_update, message) -> None:
    workflow = {
        "version": 1,
        "roles": [
            {"id": "builder", "archetype": "builder", "prompt_ref": "builder.md"},
            {"id": "inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
        ],
        "steps": [
            {"id": "builder_step", "role_id": "builder"},
            {"id": "inspector_step", "role_id": "inspector"},
        ],
    }
    workflow.update(field_update)

    with pytest.raises(WorkflowError, match=message):
        normalize_workflow(workflow)


@pytest.mark.parametrize(
    ("field_update", "message"),
    [
        (
            {"roles": [{"id": True, "archetype": "builder", "prompt_ref": "builder.md"}]},
            "workflow role id must be a string",
        ),
        ({"steps": [{"id": False, "role_id": "builder"}]}, "workflow step id must be a string"),
        (
            {"steps": [{"id": "builder_step", "role_id": "builder", "parallel_group": 1}]},
            "workflow step parallel_group must be a string",
        ),
        (
            {
                "controls": [
                    {
                        "id": False,
                        "when": {"signal": "no_evidence_progress"},
                        "call": {"role_id": "inspector"},
                    }
                ]
            },
            "workflow control id must be a string",
        ),
        (
            {
                "controls": [
                    {
                        "id": "stale_check",
                        "when": {"signal": "no_evidence_progress"},
                        "call": {"role_id": True},
                    }
                ]
            },
            r"workflow control stale_check\.call\.role_id must be a string",
        ),
    ],
)
def test_normalize_workflow_rejects_non_string_stable_identifiers(field_update, message) -> None:
    workflow = {
        "version": 1,
        "roles": [
            {"id": "builder", "archetype": "builder", "prompt_ref": "builder.md"},
            {"id": "inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
        ],
        "steps": [
            {"id": "builder_step", "role_id": "builder"},
            {"id": "inspector_step", "role_id": "inspector"},
        ],
    }
    workflow.update(field_update)

    with pytest.raises(WorkflowError, match=message):
        normalize_workflow(workflow)


def test_normalize_workflow_keeps_generated_identifiers_for_missing_ids() -> None:
    workflow = normalize_workflow(
        {
            "version": 1,
            "roles": [{"archetype": "builder", "prompt_ref": "builder.md"}],
            "steps": [{"role_id": "role_001"}],
        }
    )

    assert workflow["roles"][0]["id"] == "role_001"
    assert workflow["steps"][0]["id"] == "step_001"
