from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loopora.agent_native_evidence_contracts import (
    agent_native_active_step_is_stale,
    agent_native_active_step_view,
    agent_native_active_step_view_fields,
    agent_native_active_step_view_payload,
)
from loopora.agent_native_step_view_refresh import refresh_agent_native_step_view_with_judgment_contract
from loopora.step_instruction_context import STEP_INSTRUCTION_CONTEXT_KEY, step_instruction_context_from_mapping


def agent_native_step_instruction_context_with_coverage(
    step_instruction_context: object,
    coverage: dict[str, Any],
) -> object:
    if not isinstance(step_instruction_context, dict):
        return step_instruction_context
    iteration = (
        dict(step_instruction_context.get("iteration") or {})
        if isinstance(step_instruction_context.get("iteration"), dict)
        else {}
    )
    refreshed_iteration = {
        **iteration,
        "coverage_status": coverage["status"],
        "covered_check_count": coverage["covered_check_count"],
        "missing_check_count": coverage["missing_check_count"],
        "covered_check_ids": list(coverage["covered_check_ids"]),
        "missing_check_ids": list(coverage["missing_check_ids"]),
        "target_count": coverage["target_count"],
        "covered_target_count": coverage["covered_target_count"],
        "weak_target_count": coverage["weak_target_count"],
        "missing_target_count": coverage["missing_target_count"],
        "blocked_target_count": coverage["blocked_target_count"],
        "coverage_top_gaps": [dict(item) for item in list(coverage["top_gaps"]) if isinstance(item, dict)],
    }
    refreshed_context = dict(step_instruction_context)
    refreshed_context["iteration"] = refreshed_iteration
    return refreshed_context


@dataclass(frozen=True, slots=True)
class AgentNativeActiveStepRefreshRequest:
    run: dict[str, Any]
    state: dict[str, Any]
    coverage_context: dict[str, Any]
    current_step_projection: object


@dataclass(frozen=True, slots=True)
class AgentNativeActiveStepRefreshResult:
    active_step: dict[str, Any]
    step_view: dict[str, Any] | None
    state_changed: bool


def refresh_agent_native_claimed_active_step(
    request: AgentNativeActiveStepRefreshRequest,
) -> AgentNativeActiveStepRefreshResult:
    active = _active_step_from_state(request.state)
    active_step_payload = agent_native_active_step_view_payload(active)
    active_step_view = agent_native_active_step_view(active)
    if active and active_step_payload and agent_native_active_step_is_stale(active, request.current_step_projection):
        return AgentNativeActiveStepRefreshResult(active_step={}, step_view=None, state_changed=True)
    if not active or not active_step_payload:
        return AgentNativeActiveStepRefreshResult(active_step=active, step_view=None, state_changed=False)

    step_instruction_context = step_instruction_context_from_mapping(active)
    refreshed_step_instruction_context = agent_native_step_instruction_context_with_coverage(
        step_instruction_context,
        request.coverage_context,
    )
    context_fields = {STEP_INSTRUCTION_CONTEXT_KEY: refreshed_step_instruction_context}
    context_changed = any(active.get(key) != value for key, value in context_fields.items())
    if context_changed:
        active.update(context_fields)
    step_view = refresh_agent_native_step_view_with_judgment_contract(
        request.run,
        active_step_payload,
        step_instruction_context=refreshed_step_instruction_context,
    )
    view_changed = step_view != active_step_view
    if view_changed:
        active.update(agent_native_active_step_view_fields(step_view))
    return AgentNativeActiveStepRefreshResult(
        active_step=active,
        step_view=step_view,
        state_changed=context_changed or view_changed,
    )


def _active_step_from_state(state: dict[str, Any]) -> dict[str, Any]:
    active = state.get("active_step")
    if not isinstance(active, dict):
        return {}
    return dict(active)
