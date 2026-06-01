from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from loopora.agent_native_controls import agent_native_control_queue_index
from loopora.agent_native_parallel_groups import agent_native_parallel_group_finished_payload
from loopora.agent_native_state import update_agent_native_parallel_group_snapshot_after_submit
from loopora.context_step_results import evidence_entry_id
from loopora.structured_numbers import coerced_non_negative_int


@dataclass(frozen=True)
class AgentNativeStepAdvanceRequest:
    run: dict[str, Any]
    state: dict[str, Any]
    context: Any
    iter_id: int
    step: dict
    step_order: int
    is_control_step: bool


def agent_native_record_control_completion(
    run: dict,
    result: dict,
    *,
    append_run_event: Callable[..., None],
) -> bool:
    step = result["step"]
    if not step.get("control_id"):
        return False
    control = step.get("control") if isinstance(step.get("control"), dict) else {}
    evidence_id = evidence_entry_id(
        coerced_non_negative_int(result["iter_id"]),
        coerced_non_negative_int(result["step_order"]),
        str(step["id"]),
    )
    normalized_output = result["normalized_output"]
    append_run_event(
        run["id"],
        "control_completed",
        {
            **control,
            "status": normalized_output.get("status") or normalized_output.get("mode") or "completed",
            "evidence_refs": [evidence_id],
        },
        role=str(control.get("role_id") or result["runtime_role"]),
    )
    return True


def agent_native_advance_state_after_submit(
    request: AgentNativeStepAdvanceRequest,
    *,
    append_run_event: Callable[..., None],
) -> None:
    iter_id = coerced_non_negative_int(request.iter_id)
    step_order = coerced_non_negative_int(request.step_order)
    if request.is_control_step:
        queue = [item for item in list(request.state.get("control_queue") or []) if isinstance(item, dict)]
        request.state["control_queue_index"] = agent_native_control_queue_index(request.state, queue=queue) + 1
        request.state["step_index"] = len(request.context.strategy_steps)
        return
    parallel_finished = agent_native_parallel_group_finished_payload(
        request.context.strategy_steps,
        iter_id,
        request.step,
        step_order,
    )
    if parallel_finished is not None:
        append_run_event(request.run["id"], "parallel_group_finished", parallel_finished)
    request.state["step_index"] = step_order + 1
    update_agent_native_parallel_group_snapshot_after_submit(
        request.state,
        strategy_steps=request.context.strategy_steps,
        step=request.step,
        step_order=step_order,
    )
