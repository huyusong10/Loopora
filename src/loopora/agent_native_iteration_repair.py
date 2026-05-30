from __future__ import annotations

from typing import Any

from loopora.service_agent_native_contracts import (
    _agent_native_current_gap_repair_next_action,
    _agent_native_previous_blocked_handoff,
    _agent_native_repair_blockers_still_current,
    _agent_native_string_list,
    agent_native_actionable_blocking_item,
    agent_native_actionable_repair_next_action,
)
from loopora.structured_numbers import structured_non_negative_int


def agent_native_step_view_iteration_repair_context(step_instruction_context: object) -> dict[str, Any]:
    step_context = step_instruction_context if isinstance(step_instruction_context, dict) else {}
    iteration = step_context.get("iteration") if isinstance(step_context.get("iteration"), dict) else {}
    previous_summary = (
        step_context.get("upstream", {}).get("previous_iteration_summary")
        if isinstance(step_context.get("upstream"), dict)
        else None
    )
    previous_summary = previous_summary if isinstance(previous_summary, dict) else {}
    iter_index = structured_non_negative_int(iteration.get("iter_index"))
    if not previous_summary and not (iter_index and iter_index > 0):
        return {}
    blocked_handoff = _agent_native_previous_blocked_handoff(previous_summary)
    gatekeeper_verdict = previous_summary.get("gatekeeper_verdict") if isinstance(previous_summary.get("gatekeeper_verdict"), dict) else {}
    blocking_items = _agent_native_string_list(blocked_handoff.get("blocking_items"))
    if not blocking_items:
        blocking_items = _agent_native_string_list(gatekeeper_verdict.get("blocking_issues"))
    blocking_items = [agent_native_actionable_blocking_item(item) for item in blocking_items if item]
    top_gaps = [dict(item) for item in list(iteration.get("coverage_top_gaps") or []) if isinstance(item, dict)][:5]
    summary = str(blocked_handoff.get("summary") or gatekeeper_verdict.get("decision_summary") or "").strip()
    recommended_next_action = str(
        blocked_handoff.get("recommended_next_action")
        or gatekeeper_verdict.get("feedback_to_builder")
        or gatekeeper_verdict.get("feedback_to_generator")
        or ""
    ).strip()
    if not _agent_native_repair_blockers_still_current(blocking_items, top_gaps):
        blocking_items = []
        recommended_next_action = _agent_native_current_gap_repair_next_action(top_gaps)
    recommended_next_action = agent_native_actionable_repair_next_action(recommended_next_action, blocking_items)
    if not any((blocking_items, top_gaps, summary, recommended_next_action)):
        return {}
    source = blocked_handoff.get("source") if isinstance(blocked_handoff.get("source"), dict) else {}
    return {
        "active": True,
        "previous_iteration": structured_non_negative_int(previous_summary.get("iter")),
        "source_step_id": str(source.get("step_id") or "").strip(),
        "source_role": str(source.get("role_name") or source.get("role_id") or "").strip(),
        "status": str(blocked_handoff.get("status") or "").strip(),
        "summary": summary,
        "blocking_items": blocking_items[:8],
        "recommended_next_action": recommended_next_action,
        "evidence_refs": _agent_native_string_list(blocked_handoff.get("evidence_refs"))[:8],
        "top_gaps": top_gaps,
    }
