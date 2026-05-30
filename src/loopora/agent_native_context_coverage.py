from __future__ import annotations

from typing import Any


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
