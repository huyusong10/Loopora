from __future__ import annotations

from typing import Any

from loopora.run_takeaways import build_judgment_contract
from loopora.service_agent_native_contracts import _agent_native_role_posture_list, _agent_native_string_list
from loopora.structured_numbers import structured_non_negative_int


def agent_native_step_view_judgment_contract(run: dict, step_instruction_context: object) -> dict[str, Any]:
    step_context = step_instruction_context if isinstance(step_instruction_context, dict) else {}
    contract = step_context.get("contract") if isinstance(step_context.get("contract"), dict) else {}
    if not contract:
        return build_judgment_contract(run)
    projection = build_judgment_contract(run)
    contract_role_postures = _agent_native_role_posture_list(contract.get("role_postures"))
    contract_coverage_targets = [dict(item) for item in list(contract.get("coverage_targets") or []) if isinstance(item, dict)]
    projection.update(
        {
            "contract_path": str(contract.get("path") or projection.get("contract_path") or "").strip(),
            "goal": str(contract.get("goal") or projection.get("goal") or "").strip(),
            "constraints": str(contract.get("constraints") or projection.get("constraints") or "").strip(),
            "check_mode": str(contract.get("check_mode") or projection.get("check_mode") or "").strip(),
            "check_count": structured_non_negative_int(contract.get("check_count")),
            "completion_mode": str(contract.get("completion_mode") or projection.get("completion_mode") or "").strip(),
            "collaboration_summary": str(contract.get("collaboration_summary") or projection.get("collaboration_summary") or "").strip(),
            "loop_fit_reasons": _agent_native_string_list(contract.get("loop_fit_reasons")) or projection.get("loop_fit_reasons", []),
            "strategy_preset": str(
                contract.get("strategy_preset")
                or contract.get("workflow_preset")
                or projection.get("strategy_preset")
                or projection.get("workflow_preset")
                or ""
            ).strip(),
            "strategy_collaboration_intent": str(
                contract.get("strategy_collaboration_intent")
                or contract.get("workflow_collaboration_intent")
                or projection.get("strategy_collaboration_intent")
                or projection.get("workflow_collaboration_intent")
                or ""
            ).strip(),
            "workflow_preset": str(
                contract.get("workflow_preset")
                or contract.get("strategy_preset")
                or projection.get("workflow_preset")
                or projection.get("strategy_preset")
                or ""
            ).strip(),
            "workflow_collaboration_intent": str(
                contract.get("workflow_collaboration_intent")
                or contract.get("strategy_collaboration_intent")
                or projection.get("workflow_collaboration_intent")
                or projection.get("strategy_collaboration_intent")
                or ""
            ).strip(),
            "judgment_tradeoffs": _agent_native_string_list(contract.get("judgment_tradeoffs")) or projection.get("judgment_tradeoffs", []),
            "execution_strategy": _agent_native_string_list(contract.get("execution_strategy")) or projection.get("execution_strategy", []),
            "local_governance": _agent_native_string_list(contract.get("local_governance")) or projection.get("local_governance", []),
            "role_postures": contract_role_postures or projection.get("role_postures", []),
            "coverage_targets": contract_coverage_targets or projection.get("coverage_targets", []),
            "success_surface": _agent_native_string_list(contract.get("success_surface")) or projection.get("success_surface", []),
            "fake_done_states": _agent_native_string_list(contract.get("fake_done_states")) or projection.get("fake_done_states", []),
            "evidence_preferences": _agent_native_string_list(contract.get("evidence_preferences")) or projection.get("evidence_preferences", []),
            "residual_risk": str(contract.get("residual_risk") or projection.get("residual_risk") or "").strip(),
        }
    )
    return projection
