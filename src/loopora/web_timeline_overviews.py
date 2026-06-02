from __future__ import annotations

from collections.abc import Mapping

from loopora.structured_booleans import structured_bool_is_true
from loopora.structured_numbers import structured_optional_non_negative_int
from loopora.web_timeline_run_events import format_run_finished as _format_run_finished
from loopora.web_timeline_run_events import format_run_result_accepted as _format_run_result_accepted

SIMPLE_TIMELINE_TITLES = {
    "run_started": "Run started",
    "stop_requested": "Stop requested",
    "run_result_accepted": "Evidence verdict recorded",
}

CONTROL_TIMELINE_TITLES = {
    "control_triggered": "Control triggered",
    "control_completed": "Control completed",
    "control_failed": "Control failed",
    "control_skipped": "Control skipped",
}

PARALLEL_GROUP_TIMELINE_TITLES = {
    "parallel_group_started": "Parallel review started",
    "parallel_group_finished": "Parallel review finished",
}


def format_timeline_event(event: dict) -> dict:
    payload = event.get("payload", {})
    if not isinstance(payload, Mapping):
        payload = {}
    role = payload.get("role") or event.get("role")
    formatter = TIMELINE_EVENT_FORMATTERS.get(event["event_type"])
    if formatter:
        title, detail = formatter(payload, role, event["event_type"])
    else:
        title = SIMPLE_TIMELINE_TITLES.get(event["event_type"], event["event_type"])
        detail = ""

    return {
        "id": event["id"],
        "event_type": event["event_type"],
        "created_at": event["created_at"],
        "title": title,
        "detail": detail,
        "role": event.get("role"),
        "payload": payload,
    }


def _format_checks_resolved(payload: Mapping[str, object], _role: object, _event_type: str) -> tuple[str, str]:
    source = "auto-generated" if payload.get("source") == "auto_generated" else "specified"
    count = structured_optional_non_negative_int(payload.get("count")) or 0
    return "Checks resolved", f"{count} checks, {source}"


def _format_role_request_prepared(payload: Mapping[str, object], role: object, _event_type: str) -> tuple[str, str]:
    return "Role request prepared", str(payload.get("role_name") or role or "").strip()


def _format_step_instruction_context_prepared(
    payload: Mapping[str, object],
    _role: object,
    _event_type: str,
) -> tuple[str, str]:
    return "StepInstruction context prepared", str(payload.get("step_id") or "").strip()


def _format_role_execution_summary(payload: Mapping[str, object], role: object, _event_type: str) -> tuple[str, str]:
    duration_ms = payload.get("duration_ms")
    if structured_bool_is_true(payload.get("ok")):
        return f"{role or 'role'} completed", _role_execution_success_detail(payload, duration_ms)
    return f"{role or 'role'} failed", _role_execution_failure_detail(payload, duration_ms)


def _role_execution_success_detail(payload: Mapping[str, object], duration_ms: object) -> str:
    parts = []
    attempts = structured_optional_non_negative_int(payload.get("attempts"))
    if attempts is not None and attempts > 1:
        parts.append(f"attempts={attempts}")
    if structured_bool_is_true(payload.get("degraded")):
        parts.append("degraded")
    duration = structured_optional_non_negative_int(duration_ms)
    if duration is not None:
        parts.append(f"{duration}ms")
    return ", ".join(parts) if parts else "ok"


def _role_execution_failure_detail(payload: Mapping[str, object], duration_ms: object) -> str:
    parts = [str(payload.get("error", "")).strip()]
    duration = structured_optional_non_negative_int(duration_ms)
    if duration is not None:
        parts.append(f"{duration}ms")
    return ", ".join(part for part in parts if part)


def _format_role_degraded(payload: Mapping[str, object], role: object, _event_type: str) -> tuple[str, str]:
    return f"{role or 'role'} degraded", str(payload.get("mode", "")).strip()


def _format_step_handoff_written(payload: Mapping[str, object], _role: object, _event_type: str) -> tuple[str, str]:
    return "Step handoff written", str(payload.get("summary") or payload.get("step_id") or "").strip()


def _format_control_event(payload: Mapping[str, object], role: object, event_type: str) -> tuple[str, str]:
    detail = " -> ".join(
        item
        for item in [
            str(payload.get("signal") or "").strip(),
            str(payload.get("role_id") or role or "").strip(),
        ]
        if item
    )
    return CONTROL_TIMELINE_TITLES[event_type], detail


def _format_parallel_group_event(payload: Mapping[str, object], _role: object, event_type: str) -> tuple[str, str]:
    group = str(payload.get("parallel_group") or "-").strip() or "-"
    step_count = _parallel_group_step_count(payload)
    detail = f"{group}, steps={step_count}" if step_count else group
    return PARALLEL_GROUP_TIMELINE_TITLES[event_type], detail


def _parallel_group_step_count(payload: Mapping[str, object]) -> int:
    step_ids = payload.get("step_ids")
    if isinstance(step_ids, list):
        return len(step_ids)
    step_orders = payload.get("step_orders")
    if isinstance(step_orders, list):
        return len(step_orders)
    return 0


def _format_iteration_summary_written(payload: Mapping[str, object], _role: object, _event_type: str) -> tuple[str, str]:
    return "Iteration summary written", str(payload.get("composite_score", "")).strip()


def _format_challenger_done(payload: Mapping[str, object], _role: object, _event_type: str) -> tuple[str, str]:
    return "Guide suggested a new direction", str(payload.get("mode", "")).strip()


def _format_iteration_wait_started(payload: Mapping[str, object], _role: object, _event_type: str) -> tuple[str, str]:
    duration_seconds = structured_optional_non_negative_int(payload.get("duration_seconds")) or 0
    return "Waiting for the next iteration", f"{duration_seconds}s"


def _format_iteration_wait_finished(payload: Mapping[str, object], _role: object, _event_type: str) -> tuple[str, str]:
    duration_seconds = structured_optional_non_negative_int(payload.get("duration_seconds")) or 0
    return "Iteration wait finished", f"{duration_seconds}s"


def _format_run_aborted(payload: Mapping[str, object], _role: object, _event_type: str) -> tuple[str, str]:
    attempts = structured_optional_non_negative_int(payload.get("attempts"))
    return f"Run aborted in {payload.get('role', 'role')}", f"attempts={attempts}" if attempts is not None else ""


def _format_workspace_guard_triggered(payload: Mapping[str, object], _role: object, _event_type: str) -> tuple[str, str]:
    deleted_count = structured_optional_non_negative_int(payload.get("deleted_original_count")) or 0
    return "Workspace safety guard triggered", f"deleted={deleted_count}"


TIMELINE_EVENT_FORMATTERS = {
    "checks_resolved": _format_checks_resolved,
    "role_request_prepared": _format_role_request_prepared,
    "step_instruction_context_prepared": _format_step_instruction_context_prepared,
    "role_execution_summary": _format_role_execution_summary,
    "role_degraded": _format_role_degraded,
    "step_handoff_written": _format_step_handoff_written,
    "iteration_summary_written": _format_iteration_summary_written,
    "challenger_done": _format_challenger_done,
    "iteration_wait_started": _format_iteration_wait_started,
    "iteration_wait_finished": _format_iteration_wait_finished,
    "run_aborted": _format_run_aborted,
    "workspace_guard_triggered": _format_workspace_guard_triggered,
    "run_finished": _format_run_finished,
    "run_result_accepted": _format_run_result_accepted,
    **dict.fromkeys(CONTROL_TIMELINE_TITLES, _format_control_event),
    **dict.fromkeys(PARALLEL_GROUP_TIMELINE_TITLES, _format_parallel_group_event),
}
