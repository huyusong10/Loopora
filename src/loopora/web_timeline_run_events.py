from __future__ import annotations

from collections.abc import Mapping

from loopora.run_takeaway_common import display_iter as _display_iter


def format_run_finished(payload: Mapping[str, object], _role: object, _event_type: str) -> tuple[str, str]:
    status = str(payload.get("status") or "finished").strip()
    title = {
        "succeeded": "Run finished",
        "failed": "Run failed",
        "stopped": "Run stopped",
    }.get(status, f"Run {status}" if status else "Run finished")
    reason = str(payload.get("reason", "")).strip()
    iter_id = payload.get("iter")
    detail_parts: list[str] = []
    if reason:
        detail_parts.append(
            {
                "max_iters_exhausted": "max iterations exhausted",
                "rounds_completed": "planned rounds completed",
            }.get(reason, reason)
        )
    elif iter_id is not None:
        display_iter = _display_iter(iter_id)
        if display_iter is not None:
            detail_parts.append(f"iter={display_iter}")
    task_status = str(payload.get("task_verdict_status") or "not_evaluated").strip() or "not_evaluated"
    detail_parts.append(f"task_verdict_status={task_status}")
    task_summary = str(payload.get("task_verdict_summary") or "").strip()
    if task_summary:
        detail_parts.append(f"task_verdict_summary={task_summary[:120]}")
    return title, ", ".join(detail_parts)


def format_run_result_accepted(payload: Mapping[str, object], _role: object, _event_type: str) -> tuple[str, str]:
    status = str(payload.get("status") or "").strip()
    task_status = str(payload.get("task_verdict_status") or "").strip()
    judgment_summary = str(payload.get("judgment_contract_summary") or "").strip()
    loop_fit_reasons = _payload_string_list(payload, "loop_fit_reasons")
    execution_strategy = _payload_string_list(payload, "execution_strategy")
    local_governance = _payload_string_list(payload, "local_governance")
    role_postures = _payload_string_list(payload, "role_postures")
    judgment_tradeoffs = _payload_string_list(payload, "judgment_tradeoffs")
    success_surface = _payload_string_list(payload, "success_surface")
    fake_done_states = _payload_string_list(payload, "fake_done_states")
    evidence_preferences = _payload_string_list(payload, "evidence_preferences")
    residual_risk = str(payload.get("residual_risk") or "").strip()
    run_contract_path = str(payload.get("run_contract_path") or "").strip()
    detail = ", ".join(
        part
        for part in (
            f"status={status}" if status else "",
            f"task_verdict_status={task_status}" if task_status else "",
            f"judgment={judgment_summary[:120]}" if judgment_summary else "",
            f"loop_fit={loop_fit_reasons[0][:120]}" if loop_fit_reasons else "",
            f"strategy={execution_strategy[0][:120]}" if execution_strategy else "",
            f"local_governance={local_governance[0][:120]}" if local_governance else "",
            f"role_posture={role_postures[0][:120]}" if role_postures else "",
            f"tradeoff={judgment_tradeoffs[0][:120]}" if judgment_tradeoffs else "",
            f"success={success_surface[0][:120]}" if success_surface else "",
            f"fake_done={fake_done_states[0][:120]}" if fake_done_states else "",
            f"evidence={evidence_preferences[0][:120]}" if evidence_preferences else "",
            f"residual_risk={residual_risk[:120]}" if residual_risk else "",
            f"run_contract={run_contract_path}" if run_contract_path and not judgment_summary else "",
        )
        if part
    )
    return recorded_verdict_title(task_status), detail


def recorded_verdict_title(task_status: str) -> str:
    return {
        "passed": "Passing evidence verdict recorded",
        "passed_with_residual_risk": "Pass-with-risk verdict recorded",
        "insufficient_evidence": "Unproven evidence verdict recorded",
        "failed": "Failed evidence verdict recorded",
        "not_evaluated": "Unevaluated evidence verdict recorded",
    }.get(str(task_status or "").strip().lower(), "Evidence verdict recorded")


def _payload_string_list(payload: Mapping[str, object], key: str) -> list[str]:
    values = payload.get(key)
    if not isinstance(values, list):
        return []
    return [item.strip() for item in values if isinstance(item, str) and item.strip()]
