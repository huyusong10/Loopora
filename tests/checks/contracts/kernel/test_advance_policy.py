from __future__ import annotations

from types import SimpleNamespace

from loopora.engine import WorkflowCursorFromEventsRequest, WorkflowStepSelectionRequest, select_next_workflow_step, workflow_step_index_from_events


def test_advance_policy_selects_workflow_step_by_cursor() -> None:
    selection = select_next_workflow_step(
        WorkflowStepSelectionRequest(
            workflow_steps=[
                {"id": "builder", "role_id": "builder"},
                {"id": "gatekeeper", "role_id": "gatekeeper"},
            ],
            step_index=1,
        )
    )

    assert selection is not None
    assert selection.step_order == 1
    assert selection.step["id"] == "gatekeeper"


def test_advance_policy_returns_none_after_workflow_steps_are_exhausted() -> None:
    selection = select_next_workflow_step(
        WorkflowStepSelectionRequest(
            workflow_steps=[{"id": "builder", "role_id": "builder"}],
            step_index=1,
        )
    )

    assert selection is None


def test_advance_policy_preserves_parallel_group_signal() -> None:
    selection = select_next_workflow_step(
        WorkflowStepSelectionRequest(
            workflow_steps=[{"id": "inspect_a", "role_id": "inspector", "parallel_group": "review"}],
            step_index=0,
        )
    )

    assert selection is not None
    assert selection.parallel_group == "review"


def test_advance_policy_derives_cursor_from_committed_step_events() -> None:
    step_index = workflow_step_index_from_events(
        WorkflowCursorFromEventsRequest(
            workflow_steps=[
                {"id": "builder", "role_id": "builder"},
                {"id": "gatekeeper", "role_id": "gatekeeper"},
            ],
            events=[SimpleNamespace(event_type="StepCommitted", payload={"step_id": "builder", "iteration": 0})],
            iteration=0,
            fallback_step_index=0,
        )
    )

    assert step_index == 1


def test_advance_policy_prefers_claimable_current_step_projection() -> None:
    step_index = workflow_step_index_from_events(
        WorkflowCursorFromEventsRequest(
            workflow_steps=[
                {"id": "builder", "role_id": "builder"},
                {"id": "gatekeeper", "role_id": "gatekeeper"},
            ],
            events=[SimpleNamespace(event_type="StepCommitted", payload={"step_id": "builder", "iteration": 0})],
            iteration=0,
            fallback_step_index=0,
            current_step_projection={
                "source_sequence": 4,
                "claimable": True,
                "step_id": "gatekeeper",
                "iteration": 0,
            },
        )
    )

    assert step_index == 1
