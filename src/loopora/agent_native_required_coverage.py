from __future__ import annotations

from typing import Any

from loopora.structured_numbers import structured_non_negative_int


def agent_native_required_coverage(step_instruction_context: dict[str, Any] | None) -> dict[str, Any]:
    step_context = step_instruction_context if isinstance(step_instruction_context, dict) else {}
    iteration = step_context.get("iteration") if isinstance(step_context.get("iteration"), dict) else {}
    return {
        "status": str(iteration.get("coverage_status") or "pending"),
        "evidence_progress_mode": str(iteration.get("evidence_progress_mode") or "none"),
        "covered_check_count": structured_non_negative_int(iteration.get("covered_check_count")),
        "missing_check_count": structured_non_negative_int(iteration.get("missing_check_count")),
        "target_count": structured_non_negative_int(iteration.get("target_count")),
        "covered_target_count": structured_non_negative_int(iteration.get("covered_target_count")),
        "weak_target_count": structured_non_negative_int(iteration.get("weak_target_count")),
        "missing_target_count": structured_non_negative_int(iteration.get("missing_target_count")),
        "blocked_target_count": structured_non_negative_int(iteration.get("blocked_target_count")),
        "covered_check_ids": [str(item) for item in list(iteration.get("covered_check_ids") or []) if str(item).strip()],
        "missing_check_ids": [str(item) for item in list(iteration.get("missing_check_ids") or []) if str(item).strip()],
        "top_gaps": [dict(item) for item in list(iteration.get("coverage_top_gaps") or []) if isinstance(item, dict)][:5],
    }
