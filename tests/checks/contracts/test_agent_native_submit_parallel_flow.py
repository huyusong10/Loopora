from __future__ import annotations

from types import SimpleNamespace

from loopora.agent_native_submit_flow import AgentNativeStepAdvanceRequest, agent_native_advance_state_after_submit


STEP_INDEX_AFTER_PARALLEL_GROUP = 2


def test_agent_native_submit_flow_rejects_bool_parallel_group_identity() -> None:
    events: list[tuple] = []
    state: dict = {"step_index": True}
    steps = [
        {"id": "builder_a", "parallel_group": "peer_review"},
        {"id": "builder_b", "parallel_group": "peer_review"},
    ]

    agent_native_advance_state_after_submit(
        AgentNativeStepAdvanceRequest(
            run={"id": "run_parallel_bool_identity"},
            state=state,
            context=SimpleNamespace(strategy_steps=steps),
            iter_id=True,
            step=steps[0],
            step_order=True,
            is_control_step=False,
        ),
        append_run_event=lambda *args, **kwargs: events.append((args, kwargs)),
    )

    assert state["step_index"] == 1
    assert events == []


def test_agent_native_submit_flow_records_parallel_group_finish() -> None:
    events: list[tuple] = []
    state: dict = {"step_index": 1}
    steps = [
        {"id": "builder_a", "parallel_group": "peer_review"},
        {"id": "builder_b", "parallel_group": "peer_review"},
        {"id": "gatekeeper_step"},
    ]
    context = SimpleNamespace(strategy_steps=steps)

    agent_native_advance_state_after_submit(
        AgentNativeStepAdvanceRequest(
            run={"id": "run_parallel"},
            state=state,
            context=context,
            iter_id=3,
            step=steps[1],
            step_order=1,
            is_control_step=False,
        ),
        append_run_event=lambda *args, **kwargs: events.append((args, kwargs)),
    )

    assert state["step_index"] == STEP_INDEX_AFTER_PARALLEL_GROUP
    assert events == [
        (
            (
                "run_parallel",
                "parallel_group_finished",
                {
                    "iter": 3,
                    "parallel_group": "peer_review",
                    "step_orders": [0, 1],
                    "step_ids": ["builder_a", "builder_b"],
                },
            ),
            {},
        )
    ]
