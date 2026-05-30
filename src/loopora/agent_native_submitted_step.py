from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loopora.context_flow import evidence_entry_id
from loopora.run_artifacts import RunArtifactLayout
from loopora.service_agent_native_contracts import (
    _agent_native_output_coverage_results,
    agent_native_actionable_blocking_item,
    agent_native_actionable_repair_next_action,
)


@dataclass(frozen=True)
class AgentNativeSubmittedStepResultRequest:
    layout: RunArtifactLayout
    iter_id: int
    step: dict[str, Any]
    step_order: int
    role: dict[str, Any]
    runtime_role: str
    normalized_output: dict[str, Any]
    handoff: dict[str, Any]


def agent_native_submitted_step_result(request: AgentNativeSubmittedStepResultRequest) -> dict[str, Any]:
    step_id = str(request.step.get("id") or "").strip()
    evidence_refs = [str(item) for item in list(request.handoff.get("evidence_refs") or []) if str(item).strip()]
    if not evidence_refs and step_id:
        evidence_refs = [evidence_entry_id(request.iter_id, request.step_order, step_id)]
    handoff_path = request.layout.step_handoff_path(request.iter_id, request.step_order, step_id)
    blocking_items = [str(item).strip() for item in list(request.handoff.get("blocking_items") or []) if str(item).strip()]
    actionable_blocking_items = [agent_native_actionable_blocking_item(item) for item in blocking_items]
    recommended_next_action = agent_native_actionable_repair_next_action(
        str(request.handoff.get("recommended_next_action") or "").strip(),
        actionable_blocking_items,
    )
    submitted_step = {
        "iter": request.iter_id,
        "step_id": step_id,
        "step_order": request.step_order,
        "role": {
            "id": str(request.role.get("id") or ""),
            "name": str(request.role.get("name") or ""),
            "archetype": str(request.role.get("archetype") or ""),
        },
        "runtime_role": request.runtime_role,
        "status": str(
            request.handoff.get("status") or request.normalized_output.get("status") or request.normalized_output.get("mode") or "completed"
        ),
        "summary": str(
            request.handoff.get("summary")
            or request.normalized_output.get("summary")
            or request.normalized_output.get("decision_summary")
            or ""
        ).strip(),
        "evidence_refs": evidence_refs,
        "blocking_items": actionable_blocking_items,
        "recommended_next_action": recommended_next_action,
        "handoff_path": request.layout.relative(handoff_path),
        "handoff_absolute_path": str(handoff_path.resolve()),
    }
    coverage_results = _agent_native_output_coverage_results(request.normalized_output)
    if coverage_results:
        submitted_step["coverage_results"] = coverage_results
    return submitted_step
