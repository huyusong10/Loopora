from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.recovery import RetryConfig
from loopora.run_artifacts import INITIAL_STAGNATION_STATE
from loopora.service_types import normalize_completion_mode
from loopora.service_workflow_execution import _WorkflowIterationState, _WorkflowRunContext
from loopora.utils import read_json
from loopora.workflows import normalize_workflow


def agent_native_run_context(
    run: dict[str, Any],
    state: dict[str, Any],
    *,
    layout: object,
    executor: object,
    prompt_files: dict[str, str],
) -> _WorkflowRunContext:
    workflow = run.get("workflow_json") or read_json(layout.contract_workflow_path)
    workflow = normalize_workflow(workflow)
    role_by_id = {role["id"]: role for role in workflow.get("roles", [])}
    return _WorkflowRunContext(
        run_id=run["id"],
        run=run,
        run_dir=Path(run["runs_dir"]),
        workflow=workflow,
        executor=executor,
        compiled_spec=run["compiled_spec_json"],
        retry_config=RetryConfig(max_retries=run["max_role_retries"]),
        prompt_files=prompt_files,
        layout=layout,
        run_contract=read_json(layout.run_contract_path),
        workflow_steps=list(workflow.get("steps", [])),
        workflow_controls=list(workflow.get("controls", [])),
        control_fire_counts=dict(state.get("control_fire_counts") or {}),
        workflow_started_at=0.0,
        role_by_id=role_by_id,
        completion_mode=normalize_completion_mode(run.get("completion_mode", "gatekeeper")),
        last_gatekeeper_result=state.get("current_gatekeeper_result")
        if isinstance(state.get("current_gatekeeper_result"), dict)
        else None,
    )


def agent_native_iteration_state(state: dict[str, Any]) -> _WorkflowIterationState:
    return _WorkflowIterationState(
        iter_id=int(state.get("iter_id") or 0),
        previous_composite=state.get("previous_composite"),
        stagnation=dict(state.get("stagnation") or INITIAL_STAGNATION_STATE),
        previous_outputs_by_step=dict(state.get("previous_outputs_by_step") or {}),
        previous_outputs_by_role=dict(state.get("previous_outputs_by_role") or {}),
        previous_outputs_by_archetype=dict(state.get("previous_outputs_by_archetype") or {}),
        previous_handoffs_by_step=dict(state.get("previous_handoffs_by_step") or {}),
        previous_handoffs_by_role=dict(state.get("previous_handoffs_by_role") or {}),
        previous_iteration_summary=state.get("previous_iteration_summary")
        if isinstance(state.get("previous_iteration_summary"), dict)
        else None,
        previous_session_refs_by_step=dict(state.get("previous_session_refs_by_step") or {}),
        step_results=list(state.get("step_results") or []),
        current_outputs_by_step=dict(state.get("current_outputs_by_step") or {}),
        current_outputs_by_role=dict(state.get("current_outputs_by_role") or {}),
        current_outputs_by_archetype=dict(state.get("current_outputs_by_archetype") or {}),
        current_handoffs=list(state.get("current_handoffs") or []),
        current_session_refs_by_step=dict(state.get("current_session_refs_by_step") or {}),
        current_gatekeeper_result=state.get("current_gatekeeper_result")
        if isinstance(state.get("current_gatekeeper_result"), dict)
        else None,
        current_guide_result=state.get("current_guide_result") if isinstance(state.get("current_guide_result"), dict) else None,
    )


def agent_native_state_from_iteration(iteration: _WorkflowIterationState) -> dict[str, Any]:
    return {
        "iter_id": iteration.iter_id,
        "previous_composite": iteration.previous_composite,
        "stagnation": iteration.stagnation,
        "previous_outputs_by_step": iteration.previous_outputs_by_step,
        "previous_outputs_by_role": iteration.previous_outputs_by_role,
        "previous_outputs_by_archetype": iteration.previous_outputs_by_archetype,
        "previous_handoffs_by_step": iteration.previous_handoffs_by_step,
        "previous_handoffs_by_role": iteration.previous_handoffs_by_role,
        "previous_iteration_summary": iteration.previous_iteration_summary,
        "previous_session_refs_by_step": iteration.previous_session_refs_by_step,
        "step_results": iteration.step_results,
        "current_outputs_by_step": iteration.current_outputs_by_step,
        "current_outputs_by_role": iteration.current_outputs_by_role,
        "current_outputs_by_archetype": iteration.current_outputs_by_archetype,
        "current_handoffs": iteration.current_handoffs,
        "current_session_refs_by_step": iteration.current_session_refs_by_step,
        "current_gatekeeper_result": iteration.current_gatekeeper_result,
        "current_guide_result": iteration.current_guide_result,
    }
