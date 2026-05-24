from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentNativeNextIterationStateRequest:
    iteration: Any
    next_iter: int
    previous_outputs_by_step: dict[str, dict]
    previous_outputs_by_role: dict[str, dict]
    previous_outputs_by_archetype: dict[str, dict]
    previous_handoffs_by_step: dict[str, dict]
    previous_handoffs_by_role: dict[str, dict]
    previous_iteration_summary: dict | None


def agent_native_next_iteration_state_update(request: AgentNativeNextIterationStateRequest) -> dict[str, Any]:
    return {
        "iter_id": request.next_iter,
        "step_index": 0,
        "previous_composite": _agent_native_previous_composite(request.iteration),
        "previous_outputs_by_step": request.previous_outputs_by_step,
        "previous_outputs_by_role": request.previous_outputs_by_role,
        "previous_outputs_by_archetype": request.previous_outputs_by_archetype,
        "previous_handoffs_by_step": request.previous_handoffs_by_step,
        "previous_handoffs_by_role": request.previous_handoffs_by_role,
        "previous_iteration_summary": request.previous_iteration_summary,
        "previous_session_refs_by_step": dict(request.iteration.current_session_refs_by_step),
        "current_outputs_by_step": {},
        "current_outputs_by_role": {},
        "current_outputs_by_archetype": {},
        "current_handoffs": [],
        "current_session_refs_by_step": {},
        "current_gatekeeper_result": None,
        "current_guide_result": None,
        "step_results": [],
        "control_queue": [],
        "control_queue_index": 0,
        "control_queue_iter": None,
        "parallel_group_snapshot": {},
        "active_step": {},
        "stagnation": request.iteration.stagnation,
    }


def _agent_native_previous_composite(iteration: Any) -> object:
    current_gatekeeper_result = iteration.current_gatekeeper_result
    if isinstance(current_gatekeeper_result, dict):
        return current_gatekeeper_result.get("composite_score")
    return iteration.previous_composite
