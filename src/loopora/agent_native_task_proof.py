from __future__ import annotations

from collections.abc import Callable
from typing import Any

from loopora.run_takeaway_judgment import build_judgment_contract
from loopora.run_projection_fields import run_status_from_run, task_verdict_from_run
from loopora.run_result_recording import run_result_is_lifecycle_failure, run_result_recording_blocked_reason
from loopora.service_types import TERMINAL_RUN_STATUSES
from loopora.system_prompt_assets import load_system_prompt_asset
from loopora.task_verdicts import PASSING_TASK_VERDICT_STATUSES

AGENT_TASK_PROOF_SOURCE = "run.task_verdict"
AGENT_RUN_LIFECYCLE_SOURCE = "result.complete"


def with_agent_native_judgment_contract(result: dict[str, Any]) -> dict[str, Any]:
    run = result.get("run") if isinstance(result.get("run"), dict) else {}
    result["judgment_contract"] = build_judgment_contract(run)
    task_next_action = agent_native_task_next_action(result)
    if task_next_action:
        result["task_next_action"] = task_next_action
    return result


def agent_native_task_next_action(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("complete") is not True:
        return {}
    run = result.get("run") if isinstance(result.get("run"), dict) else {}
    run_status = run_status_from_run(run)
    if run_status not in TERMINAL_RUN_STATUSES:
        return {}
    task_verdict = task_verdict_from_run(run)
    status = str(task_verdict.get("status") or "").strip() or "not_evaluated"
    summary = str(task_verdict.get("summary") or "").strip()
    if run_result_is_lifecycle_failure(run):
        return {
            "kind": "retry_lifecycle_failure",
            "reason": "run_lifecycle_failure_retry",
            "run_status": run_status,
            "task_verdict_status": status,
            "task_verdict_summary": summary,
            "next_loop_command": "/loopora-run",
            "plan_action": "retry_run_start_from_reviewed_loop",
            "recording_blocked_reason": run_result_recording_blocked_reason(run, task_verdict_status=status),
            "guidance": load_system_prompt_asset("agent_native/task-verdict-retry-lifecycle-failure.md").strip(),
        }
    if status in PASSING_TASK_VERDICT_STATUSES:
        return {
            "kind": "already_passed",
            "reason": "task_verdict_passed",
            "run_status": run_status,
            "task_verdict_status": status,
            "task_verdict_summary": summary,
            "guidance": load_system_prompt_asset("agent_native/task-verdict-already-passed.md").strip(),
        }
    return {
        "kind": "continue_evidence",
        "reason": "run_lifecycle_complete_task_not_proven",
        "run_status": run_status,
        "task_verdict_status": status,
        "task_verdict_summary": summary,
        "next_loop_command": "/loopora-run",
        "plan_action": "open_run_url_improve_with_evidence_if_loop_needs_adjustment",
        "guidance": load_system_prompt_asset("agent_native/task-verdict-continue-evidence.md").strip(),
    }


def agent_task_proof_summary(
    *,
    complete: bool,
    task_verdict_status: str,
    task_verdict_summary: str,
    task_next_action: dict[str, Any],
    normalize_next_evidence_focus: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    status = str(task_verdict_status or "").strip()
    action = task_next_action if isinstance(task_next_action, dict) else {}
    action_kind = str(action.get("kind") or "").strip()
    if not (complete or status or action_kind):
        return {}

    task_proven = status in PASSING_TASK_VERDICT_STATUSES
    summary: dict[str, Any] = {
        "task_proven": task_proven,
        "task_outcome": _agent_task_outcome(
            complete=complete,
            task_proven=task_proven,
            status=status,
            action_kind=action_kind,
        ),
        "lifecycle_vs_task": "run_lifecycle_active_task_proven" if task_proven else "run_lifecycle_active_task_not_proven",
        "task_proof_source": AGENT_TASK_PROOF_SOURCE,
        "run_lifecycle_source": AGENT_RUN_LIFECYCLE_SOURCE,
    }
    if complete:
        summary["lifecycle_vs_task"] = (
            "run_lifecycle_complete_task_proven" if task_proven else "run_lifecycle_complete_task_not_proven"
        )
    _attach_task_next_action_summary(
        summary,
        action=action,
        action_kind=action_kind,
        task_verdict_summary=task_verdict_summary,
        normalize_next_evidence_focus=normalize_next_evidence_focus,
    )
    return {key: value for key, value in summary.items() if value not in ("", [], {})}


def _agent_task_outcome(*, complete: bool, task_proven: bool, status: str, action_kind: str) -> str:
    if task_proven:
        return "already_proven_no_new_evidence" if action_kind == "already_passed" else "proven"
    if action_kind == "retry_lifecycle_failure":
        return "not_proven_retry_lifecycle_failure"
    if action_kind == "continue_evidence":
        return "not_proven_continue_evidence"
    if complete:
        return "not_proven"
    if status and status != "not_evaluated":
        return "not_proven_continue_evidence"
    return "not_yet_evaluated"


def _attach_task_next_action_summary(
    summary: dict[str, Any],
    *,
    action: dict[str, Any],
    action_kind: str,
    task_verdict_summary: str,
    normalize_next_evidence_focus: Callable[[str], str] | None,
) -> None:
    if action_kind == "retry_lifecycle_failure":
        summary["next_loop_command"] = str(action.get("next_loop_command") or "/loopora-run").strip()
        summary["next_plan_action"] = str(action.get("plan_action") or "retry_run_start_from_reviewed_loop").strip()
        blocked_reason = str(action.get("recording_blocked_reason") or "").strip()
        if blocked_reason:
            summary["recording_blocked_reason"] = blocked_reason
    elif action_kind == "continue_evidence":
        summary["next_loop_command"] = str(action.get("next_loop_command") or "/loopora-run").strip()
        summary["next_plan_action"] = str(
            action.get("plan_action") or "open_run_url_improve_with_evidence_if_loop_needs_adjustment"
        ).strip()
        next_focus = str(action.get("task_verdict_summary") or task_verdict_summary or "").strip()
        next_focus = _normalize_focus(next_focus, normalizer=normalize_next_evidence_focus)
        if next_focus:
            summary["next_evidence_focus"] = next_focus
    elif (
        summary.get("task_proven") is not True
        and summary.get("task_outcome") == "not_proven_continue_evidence"
        and task_verdict_summary
    ):
        summary["next_evidence_focus"] = _normalize_focus(
            str(task_verdict_summary),
            normalizer=normalize_next_evidence_focus,
        )


def _normalize_focus(value: str, *, normalizer: Callable[[str], str] | None) -> str:
    text = str(value or "").strip()
    return normalizer(text) if normalizer is not None else text
