from __future__ import annotations

from collections.abc import Mapping

from loopora.run_worker_start import BACKGROUND_WORKER_START_ERROR

RUN_RESULT_LIFECYCLE_FAILURE_ERRORS = frozenset({BACKGROUND_WORKER_START_ERROR})
RUN_RESULT_LIFECYCLE_FAILURE_BLOCKED_REASON = "cannot accept lifecycle failure as a run result"
RUN_RESULT_MISSING_TASK_VERDICT_BLOCKED_REASON = "cannot accept run result without a task verdict"
RUN_RESULT_NOT_EVALUATED_BLOCKED_REASON = "cannot accept not-evaluated task verdict as a run result"


def run_result_is_lifecycle_failure(run: Mapping[str, object]) -> bool:
    return str(run.get("error_message") or "").strip() in RUN_RESULT_LIFECYCLE_FAILURE_ERRORS


def run_result_recording_blocked_reason(run: Mapping[str, object], *, task_verdict_status: str) -> str:
    normalized_status = str(task_verdict_status or "").strip().lower()
    if run_result_is_lifecycle_failure(run):
        return RUN_RESULT_LIFECYCLE_FAILURE_BLOCKED_REASON
    if not normalized_status:
        return RUN_RESULT_MISSING_TASK_VERDICT_BLOCKED_REASON
    if normalized_status == "not_evaluated":
        return RUN_RESULT_NOT_EVALUATED_BLOCKED_REASON
    return ""
