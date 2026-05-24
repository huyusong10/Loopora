from __future__ import annotations

from collections.abc import Callable
from typing import Any

from loopora.run_takeaways import build_judgment_contract
from loopora.service_types import TERMINAL_RUN_STATUSES
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
    run_status = str(run.get("run_status") or run.get("status") or "").strip()
    if run_status not in TERMINAL_RUN_STATUSES:
        return {}
    task_verdict = run.get("task_verdict") if isinstance(run.get("task_verdict"), dict) else run.get("task_verdict_json")
    task_verdict = task_verdict if isinstance(task_verdict, dict) else {}
    status = str(task_verdict.get("status") or "").strip() or "not_evaluated"
    summary = str(task_verdict.get("summary") or "").strip()
    if status in PASSING_TASK_VERDICT_STATUSES:
        return {
            "kind": "already_passed",
            "reason": "task_verdict_passed",
            "run_status": run_status,
            "task_verdict_status": status,
            "task_verdict_summary": summary,
            "guidance": "Task verdict already passed; no new evidence pass will start unless the task scope changes.",
        }
    return {
        "kind": "continue_evidence",
        "reason": "run_lifecycle_complete_task_not_proven",
        "run_status": run_status,
        "task_verdict_status": status,
        "task_verdict_summary": summary,
        "next_loop_command": "/loopora-run",
        "plan_action": "open_run_url_improve_with_evidence_if_loop_needs_adjustment",
        "guidance": (
            "Run lifecycle is complete, but the task is not proven. Run /loopora-run again in the same "
            "Agent session to start the next evidence pass from this verdict."
        ),
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
    if task_proven:
        task_outcome = "already_proven_no_new_evidence" if action_kind == "already_passed" else "proven"
    elif action_kind == "continue_evidence":
        task_outcome = "not_proven_continue_evidence"
    elif complete:
        task_outcome = "not_proven"
    elif status and status != "not_evaluated":
        task_outcome = "not_proven_continue_evidence"
    else:
        task_outcome = "not_yet_evaluated"

    summary: dict[str, Any] = {
        "task_proven": task_proven,
        "task_outcome": task_outcome,
        "lifecycle_vs_task": "run_lifecycle_active_task_proven" if task_proven else "run_lifecycle_active_task_not_proven",
        "task_proof_source": AGENT_TASK_PROOF_SOURCE,
        "run_lifecycle_source": AGENT_RUN_LIFECYCLE_SOURCE,
    }
    if complete:
        summary["lifecycle_vs_task"] = (
            "run_lifecycle_complete_task_proven" if task_proven else "run_lifecycle_complete_task_not_proven"
        )
    if action_kind == "continue_evidence":
        summary["next_loop_command"] = str(action.get("next_loop_command") or "/loopora-run").strip()
        summary["next_plan_action"] = str(
            action.get("plan_action") or "open_run_url_improve_with_evidence_if_loop_needs_adjustment"
        ).strip()
        next_focus = str(action.get("task_verdict_summary") or task_verdict_summary or "").strip()
        next_focus = _normalize_focus(next_focus, normalizer=normalize_next_evidence_focus)
        if next_focus:
            summary["next_evidence_focus"] = next_focus
    elif not task_proven and task_outcome == "not_proven_continue_evidence" and task_verdict_summary:
        summary["next_evidence_focus"] = _normalize_focus(
            str(task_verdict_summary),
            normalizer=normalize_next_evidence_focus,
        )
    return {key: value for key, value in summary.items() if value not in ("", [], {})}


def _normalize_focus(value: str, *, normalizer: Callable[[str], str] | None) -> str:
    text = str(value or "").strip()
    return normalizer(text) if normalizer is not None else text
