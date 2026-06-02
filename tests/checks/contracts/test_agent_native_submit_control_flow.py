from __future__ import annotations

from types import SimpleNamespace

from loopora.agent_native_submit_flow import (
    AgentNativeStepAdvanceRequest,
    agent_native_advance_state_after_submit,
    agent_native_record_control_completion,
)
from loopora.context_step_results import evidence_entry_id


STEP_INDEX_AFTER_CONTROL_ADVANCE = 2


def test_agent_native_submit_flow_records_control_completion_event() -> None:
    events: list[tuple] = []

    recorded = agent_native_record_control_completion(
        {"id": "run_control"},
        {
            "iter_id": 2,
            "step_order": 7,
            "step": {
                "id": "control_step",
                "control_id": "ctrl_1",
                "control": {"id": "ctrl_1", "role_id": "guide", "signal": "stalled"},
            },
            "runtime_role": "fallback-role",
            "normalized_output": {"status": "blocked"},
        },
        append_run_event=lambda *args, **kwargs: events.append((args, kwargs)),
    )

    assert recorded is True
    assert events == [
        (
            (
                "run_control",
                "control_completed",
                {
                    "id": "ctrl_1",
                    "role_id": "guide",
                    "signal": "stalled",
                    "status": "blocked",
                    "evidence_refs": [evidence_entry_id(2, 7, "control_step")],
                },
            ),
            {"role": "guide"},
        )
    ]


def test_agent_native_submit_flow_rejects_bool_control_completion_identity() -> None:
    events: list[tuple] = []

    recorded = agent_native_record_control_completion(
        {"id": "run_control_bool_identity"},
        {
            "iter_id": True,
            "step_order": True,
            "step": {
                "id": "control_step",
                "control_id": "ctrl_1",
                "control": {"id": "ctrl_1", "role_id": "guide"},
            },
            "runtime_role": "fallback-role",
            "normalized_output": {"status": "completed"},
        },
        append_run_event=lambda *args, **kwargs: events.append((args, kwargs)),
    )

    assert recorded is True
    assert events[0][0][2]["evidence_refs"] == ["ev_000_00_control_step"]


def test_agent_native_submit_flow_advances_control_queue_without_main_step_progression() -> None:
    events: list[tuple] = []
    state = {"control_queue": [{"step": {"id": "control_step"}}], "control_queue_index": 0, "step_index": 1}
    context = SimpleNamespace(strategy_steps=[{"id": "builder_step"}, {"id": "gatekeeper_step"}])

    agent_native_advance_state_after_submit(
        AgentNativeStepAdvanceRequest(
            run={"id": "run_control"},
            state=state,
            context=context,
            iter_id=0,
            step={"id": "control_step", "control_id": "ctrl_1"},
            step_order=2,
            is_control_step=True,
        ),
        append_run_event=lambda *args, **kwargs: events.append((args, kwargs)),
    )

    assert state["control_queue_index"] == 1
    assert state["step_index"] == STEP_INDEX_AFTER_CONTROL_ADVANCE
    assert events == []
