from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from loopora.run_projection_fields import task_verdict_from_run
from loopora.run_takeaway_common import clean_takeaway_text

ACTIVE_TAKEAWAY_RUN_STATUSES = {"queued", "running", "awaiting_agent", "stopping"}


def active_takeaway_run_status(run_status: object) -> bool:
    return str(run_status or "").strip().lower() in ACTIVE_TAKEAWAY_RUN_STATUSES


def terminal_task_verdict_status_for_iteration(
    run: Mapping[str, Any],
    *,
    iter_id: int,
    current_iter_id: int | None,
) -> str:
    if current_iter_id != iter_id or active_takeaway_run_status(run.get("status")):
        return ""
    verdict_status = str(task_verdict_from_run(run).get("status") or "").strip().lower()
    return {
        "failed": "failed",
        "insufficient_evidence": "blocked",
        "passed_with_residual_risk": "completed",
        "passed": "passed",
    }.get(verdict_status, "")


def terminal_task_verdict_summary_for_iteration(
    run: Mapping[str, Any],
    *,
    iter_id: int,
    current_iter_id: int | None,
) -> str:
    if current_iter_id != iter_id or active_takeaway_run_status(run.get("status")):
        return ""
    verdict = task_verdict_from_run(run)
    verdict_status = str(verdict.get("status") or "").strip().lower()
    summary = clean_takeaway_text(verdict.get("summary"), max_length=220)
    if verdict_status == "insufficient_evidence":
        return f"Task verdict insufficient evidence: {summary}" if summary else "Task verdict is still insufficient."
    if verdict_status == "failed":
        return f"Task verdict failed: {summary}" if summary else "Task verdict failed."
    if verdict_status == "passed_with_residual_risk":
        return f"Task verdict passed with residual risk: {summary}" if summary else "Task verdict passed with residual risk."
    return ""
