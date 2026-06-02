from __future__ import annotations

from types import SimpleNamespace

from loopora.engine import (
    RunnerStepCursorFromEventsRequest,
    RunnerStepSelectionRequest,
    runner_step_index_from_events,
    select_next_runner_step,
)


def test_advance_policy_selects_strategy_step_by_cursor() -> None:
    selection = select_next_runner_step(
        RunnerStepSelectionRequest(
            strategy_steps=[
                {"id": "builder", "role_id": "builder"},
                {"id": "gatekeeper", "role_id": "gatekeeper"},
            ],
            step_index=1,
        )
    )

    assert selection is not None
    assert selection.step_order == 1
    assert selection.step["id"] == "gatekeeper"


def test_advance_policy_returns_none_after_strategy_steps_are_exhausted() -> None:
    selection = select_next_runner_step(
        RunnerStepSelectionRequest(
            strategy_steps=[{"id": "builder", "role_id": "builder"}],
            step_index=1,
        )
    )

    assert selection is None


def test_advance_policy_rejects_bool_cursor_values() -> None:
    selection = select_next_runner_step(
        RunnerStepSelectionRequest(
            strategy_steps=[
                {"id": "builder", "role_id": "builder"},
                {"id": "gatekeeper", "role_id": "gatekeeper"},
            ],
            step_index=True,
        )
    )
    step_index = runner_step_index_from_events(
        RunnerStepCursorFromEventsRequest(
            strategy_steps=[{"id": "builder", "role_id": "builder"}],
            events=[],
            iteration=0,
            fallback_step_index=True,
        )
    )

    assert selection is not None
    assert selection.step_order == 0
    assert selection.step["id"] == "builder"
    assert step_index == 0


def test_advance_policy_preserves_parallel_group_signal() -> None:
    selection = select_next_runner_step(
        RunnerStepSelectionRequest(
            strategy_steps=[{"id": "inspect_a", "role_id": "inspector", "parallel_group": "review"}],
            step_index=0,
        )
    )

    assert selection is not None
    assert selection.parallel_group == "review"


def test_advance_policy_derives_cursor_from_committed_step_events() -> None:
    step_index = runner_step_index_from_events(
        RunnerStepCursorFromEventsRequest(
            strategy_steps=[
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
    step_index = runner_step_index_from_events(
        RunnerStepCursorFromEventsRequest(
            strategy_steps=[
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
