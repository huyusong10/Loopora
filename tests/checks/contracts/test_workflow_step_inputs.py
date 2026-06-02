from __future__ import annotations

import pytest

from loopora.workflows import WorkflowError, normalize_workflow


def test_normalize_workflow_parses_boolean_like_step_session_flags() -> None:
    workflow = _normalize_steps(
        {"id": "builder_step", "role_id": "builder", "inherit_session": "false"},
        {"id": "inspector_step", "role_id": "inspector", "inherit_session": "true"},
        roles=[_role("builder"), _role("inspector", "inspector")],
    )

    assert workflow["steps"][0]["inherit_session"] is False
    assert workflow["steps"][1]["inherit_session"] is True


@pytest.mark.parametrize("limit", [True, 1.5, "12"])
def test_normalize_workflow_rejects_non_integer_evidence_query_limit(limit) -> None:
    with pytest.raises(WorkflowError, match=r"workflow step inputs\.evidence_query\.limit must be an integer"):
        _normalize_steps(
            {
                "id": "builder_step",
                "role_id": "builder",
                "inputs": {"evidence_query": {"limit": limit}},
            }
        )


def test_normalize_workflow_rejects_invalid_step_session_flag_values() -> None:
    with pytest.raises(WorkflowError, match="workflow step inherit_session must be a boolean"):
        _normalize_steps({"id": "builder_step", "role_id": "builder", "inherit_session": "sometimes"})


def test_normalize_workflow_preserves_parallel_group_and_step_inputs() -> None:
    workflow = _normalize_steps(
        {"id": "builder_step", "role_id": "builder"},
        {
            "id": "accessibility_step",
            "role_id": "accessibility_inspector",
            "parallel_group": "inspection_pack",
            "inputs": {
                "handoffs_from": ["builder_step"],
                "evidence_query": {"archetypes": ["builder"], "limit": 12},
                "iteration_memory": "summary_only",
            },
        },
        {
            "id": "contract_step",
            "role_id": "contract_inspector",
            "parallel_group": "inspection_pack",
        },
        {
            "id": "gatekeeper_step",
            "role_id": "gatekeeper",
            "on_pass": "finish_run",
            "inputs": {"handoffs_from": ["accessibility_step", "contract_step"]},
        },
        roles=[
            _role("builder"),
            _role("accessibility_inspector", "inspector"),
            _role("contract_inspector", "inspector"),
            _role("gatekeeper", "gatekeeper"),
        ],
    )

    assert workflow["steps"][1]["parallel_group"] == "inspection_pack"
    assert workflow["steps"][1]["inputs"] == {
        "handoffs_from": ["builder_step"],
        "evidence_query": {"archetypes": ["builder"], "limit": 12},
        "iteration_memory": "summary_only",
    }
    assert workflow["steps"][2]["parallel_group"] == "inspection_pack"
    assert workflow["steps"][3]["inputs"] == {"handoffs_from": ["accessibility_step", "contract_step"]}


@pytest.mark.parametrize(
    "inputs",
    [
        {"handoffs_from": ["builder_step", 123]},
        {"evidence_query": {"archetypes": ["builder", False]}},
        {"evidence_query": {"verifies": ["target:done_when.check_001:covered", {"target": "fake_done"}]}},
    ],
)
def test_normalize_workflow_rejects_non_string_step_input_list_items(inputs: dict) -> None:
    with pytest.raises(WorkflowError, match="must contain only strings"):
        _normalize_steps(
            {"id": "builder_step", "role_id": "builder"},
            {
                "id": "inspector_step",
                "role_id": "inspector",
                "inputs": inputs,
            },
            roles=[_role("builder"), _role("inspector", "inspector")],
        )


def test_normalize_workflow_rejects_non_string_iteration_memory_policy() -> None:
    with pytest.raises(
        WorkflowError,
        match=r"workflow step inputs\.iteration_memory must be default, none, same_step, same_role, or summary_only",
    ):
        _normalize_steps(
            {"id": "builder_step", "role_id": "builder"},
            {
                "id": "inspector_step",
                "role_id": "inspector",
                "inputs": {"iteration_memory": False},
            },
            roles=[_role("builder"), _role("inspector", "inspector")],
        )


def _normalize_steps(*steps: dict, roles: list[dict] | None = None) -> dict:
    return normalize_workflow({"version": 1, "roles": roles or [_role("builder")], "steps": list(steps)})


def _role(role_id: str, archetype: str = "builder") -> dict:
    return {"id": role_id, "archetype": archetype, "prompt_ref": f"{archetype}.md"}
