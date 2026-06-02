from __future__ import annotations

import pytest

from loopora.workflows import WorkflowError, normalize_workflow


@pytest.mark.parametrize(
    ("workflow", "match"),
    [
        pytest.param(
            {
                "version": 1,
                "roles": [
                    {"id": "builder_a", "archetype": "builder", "prompt_ref": "builder.md"},
                    {"id": "builder_b", "archetype": "builder", "prompt_ref": "builder.md"},
                ],
                "steps": [
                    {"id": "builder_a_step", "role_id": "builder_a", "parallel_group": "builders"},
                    {"id": "builder_b_step", "role_id": "builder_b", "parallel_group": "builders"},
                ],
            },
            "parallel_group steps must be read-only",
            id="write_roles_inside_parallel_groups",
        ),
        pytest.param(
            {
                "version": 1,
                "roles": [{"id": "inspector", "archetype": "inspector", "prompt_ref": "inspector.md"}],
                "steps": [
                    {
                        "id": "inspector_step",
                        "role_id": "inspector",
                        "action_policy": {"workspace": "workspace_write"},
                    },
                ],
            },
            r"only Builder steps may set action_policy\.workspace=workspace_write",
            id="non_builder_workspace_write",
        ),
        pytest.param(
            {
                "version": 1,
                "roles": [{"id": "builder", "archetype": "builder", "prompt_ref": "builder.md"}],
                "steps": [
                    {
                        "id": "builder_step",
                        "role_id": "builder",
                        "action_policy": {"workspace": False},
                    },
                ],
            },
            r"workflow step action_policy\.workspace must be read_only or workspace_write",
            id="non_string_action_policy_workspace",
        ),
        pytest.param(
            {
                "version": 1,
                "roles": [{"id": "builder", "archetype": "builder", "prompt_ref": "builder.md"}],
                "steps": [
                    {
                        "id": "builder_step",
                        "role_id": "builder",
                        "action_policy": {"workspace": "workspace_write", "can_finish_run": True},
                    },
                ],
            },
            r"only GateKeeper steps may set action_policy\.can_finish_run=true",
            id="non_gatekeeper_finish_permission",
        ),
        pytest.param(
            {
                "version": 1,
                "roles": [
                    {"id": "gatekeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
                    {"id": "inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
                ],
                "steps": [
                    {
                        "id": "gatekeeper_step",
                        "role_id": "gatekeeper",
                        "on_pass": "finish_run",
                        "parallel_group": "review_pack",
                    },
                    {"id": "inspector_step", "role_id": "inspector", "parallel_group": "review_pack"},
                ],
            },
            "parallel_group steps may not finish runs",
            id="parallel_finish_permissions",
        ),
        pytest.param(
            {
                "version": 1,
                "roles": [
                    {"id": "inspector_a", "archetype": "inspector", "prompt_ref": "inspector.md"},
                    {"id": "inspector_b", "archetype": "inspector", "prompt_ref": "inspector.md"},
                    {"id": "inspector_c", "archetype": "inspector", "prompt_ref": "inspector.md"},
                ],
                "steps": [
                    {"id": "a", "role_id": "inspector_a", "parallel_group": "pack"},
                    {"id": "b", "role_id": "inspector_b", "parallel_group": "other"},
                    {"id": "c", "role_id": "inspector_c", "parallel_group": "pack"},
                ],
            },
            "parallel_group steps must be contiguous",
            id="parallel_group_steps_not_contiguous",
        ),
        pytest.param(
            {
                "version": 1,
                "roles": [{"id": "inspector", "archetype": "inspector", "prompt_ref": "inspector.md"}],
                "steps": [{"id": "inspector_step", "role_id": "inspector", "inputs": {"hidden_context": True}}],
            },
            "workflow step inputs contains unknown keys",
            id="unknown_input_policy_keys",
        ),
    ],
)
def test_normalize_workflow_rejects_invalid_step_policy(workflow: dict, match: str) -> None:
    with pytest.raises(WorkflowError, match=match):
        normalize_workflow(workflow)
