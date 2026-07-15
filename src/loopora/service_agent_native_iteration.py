from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.agent_native_controls import (
    AgentNativeControlQueueRequest,
    agent_native_build_control_queue,
    agent_native_control_queue_index,
    agent_native_control_queue_iter_matches,
    agent_native_control_queue_step_order,
)
from loopora.agent_native_runtime_context import agent_native_iteration_state
from loopora.agent_native_state import write_agent_native_state
from loopora.engine.runner_context import RunnerIterationState, RunnerRunContext, runner_step_claim_request
from loopora.runner_run_requests import RunnerExhaustionRequest, RunnerIterationCheckpointRequest
from loopora.runner_summary_projection import RunnerSummaryRequest
from loopora.runners import agent_runner_actor
from loopora.service_agent_native_requests import AgentNativeRuntimeClaimRequest, AgentNativeStepClaimRequest
from loopora.service_types import normalize_completion_mode
from loopora.utils import coerced_non_negative_int

from dataclasses import dataclass


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


class ServiceAgentNativeIterationMixin:
    def _agent_native_finish_iteration_or_advance(
        self,
        adapter: str,
        run: dict,
        state: dict[str, Any],
        context: RunnerRunContext,
    ) -> dict[str, Any]:
        layout = context.layout
        iteration = agent_native_iteration_state(state)
        control_claim = self._agent_native_claim_pending_control_step(adapter, run, state, context, iteration)
        if control_claim is not None:
            return control_claim
        checkpoint = self._checkpoint_runner_iteration_state(
            RunnerIterationCheckpointRequest(
                layout=layout,
                iter_id=iteration.iter_id,
                step_results=iteration.step_results,
                current_outputs_by_step=iteration.current_outputs_by_step,
                current_outputs_by_role=iteration.current_outputs_by_role,
                current_outputs_by_archetype=iteration.current_outputs_by_archetype,
                current_session_refs_by_step=iteration.current_session_refs_by_step,
                stagnation=iteration.stagnation,
                previous_composite=iteration.previous_composite,
                run_id=run["id"],
            )
        )
        (
            previous_outputs_by_step,
            previous_outputs_by_role,
            previous_outputs_by_archetype,
            previous_handoffs_by_step,
            previous_handoffs_by_role,
            _previous_handoffs_by_archetype,
            previous_iteration_summary,
        ) = checkpoint
        summary = self._build_runner_summary(
            RunnerSummaryRequest(
                run=run,
                strategy_source=context.strategy_source,
                compiled_spec=context.compiled_spec,
                iter_id=iteration.iter_id,
                step_results=iteration.step_results,
                stagnation=iteration.stagnation,
                exhausted=False,
                previous_composite=iteration.previous_composite,
            )
        )
        self._write_summary(run["id"], "awaiting_agent", summary)
        max_iters = coerced_non_negative_int(run.get("max_iters"))
        next_iter = iteration.iter_id + 1
        if max_iters > 0 and next_iter >= max_iters:
            exhausted_summary = self._build_runner_summary(
                RunnerSummaryRequest(
                    run=run,
                    strategy_source=context.strategy_source,
                    compiled_spec=context.compiled_spec,
                    iter_id=iteration.iter_id,
                    step_results=iteration.step_results,
                    stagnation=iteration.stagnation,
                    exhausted=True,
                    previous_composite=iteration.previous_composite,
                )
            )
            finished = self._handle_runner_exhaustion(
                RunnerExhaustionRequest(
                    run_id=run["id"],
                    run=run,
                    run_dir=Path(run["runs_dir"]),
                    completion_mode=normalize_completion_mode(run.get("completion_mode", "gatekeeper")),
                    last_iter_id=iteration.iter_id,
                    summary=exhausted_summary,
                )
            )
            self.repository.release_run_slot(run["id"])
            state["status"] = "complete"
            write_agent_native_state(layout, state)
            return self._with_agent_native_judgment_contract(
                {
                    "adapter": adapter,
                    "run": finished,
                    "run_path": f"/runs/{run['id']}",
                    "next_step": None,
                    "complete": True,
                }
            )

        state.update(
            agent_native_next_iteration_state_update(
                AgentNativeNextIterationStateRequest(
                    iteration=iteration,
                    next_iter=next_iter,
                    previous_outputs_by_step=previous_outputs_by_step,
                    previous_outputs_by_role=previous_outputs_by_role,
                    previous_outputs_by_archetype=previous_outputs_by_archetype,
                    previous_handoffs_by_step=previous_handoffs_by_step,
                    previous_handoffs_by_role=previous_handoffs_by_role,
                    previous_iteration_summary=previous_iteration_summary,
                )
            )
        )
        write_agent_native_state(layout, state)
        return self.claim_agent_native_step(AgentNativeStepClaimRequest(adapter=adapter, run_id=run["id"]))

    def _agent_native_claim_pending_control_step(
        self,
        adapter: str,
        run: dict,
        state: dict[str, Any],
        context: RunnerRunContext,
        iteration: RunnerIterationState,
    ) -> dict[str, Any] | None:
        if not context.strategy_controls:
            return None
        if not agent_native_control_queue_iter_matches(state.get("control_queue_iter"), iteration.iter_id):
            state["control_queue"] = agent_native_build_control_queue(
                AgentNativeControlQueueRequest(
                    run=run,
                    state=state,
                    context=context,
                    iteration=iteration,
                    append_run_event=self.append_run_event,
                )
            )
            state["control_queue_index"] = 0
            state["control_queue_iter"] = iteration.iter_id
            state["control_fire_counts"] = dict(context.control_fire_counts)
            write_agent_native_state(context.layout, state)

        queue = [item for item in list(state.get("control_queue") or []) if isinstance(item, dict)]
        index = agent_native_control_queue_index(state, queue=queue)
        if index >= len(queue):
            return None
        entry = queue[index]
        step = entry.get("step") if isinstance(entry.get("step"), dict) else {}
        step_order = agent_native_control_queue_step_order(entry)
        if not step or step_order is None:
            state["control_queue_index"] = index + 1
            write_agent_native_state(context.layout, state)
            return self._agent_native_claim_pending_control_step(adapter, run, state, context, iteration)
        return self._agent_native_claim_runtime_step(
            AgentNativeRuntimeClaimRequest(
                kind=adapter,
                run=run,
                state=state,
                context=context,
                iteration=iteration,
                step=step,
                step_order=step_order,
                claim_request=runner_step_claim_request(
                    context,
                    iteration,
                    step=step,
                    role=context.role_by_id[step["role_id"]],
                    pending_actor=agent_runner_actor(adapter),
                ),
            )
        )
