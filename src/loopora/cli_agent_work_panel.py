from __future__ import annotations

import typer

from loopora.agent_native_coverage_summary import coverage_gap_summaries
from loopora.agent_native_guidance import actionable_blocking_item as _actionable_blocking_item
from loopora.agent_native_guidance import actionable_next_action as _actionable_next_action
from loopora.agent_native_next_step_summary import agent_next_step_summary
from loopora.agent_native_task_proof import PASSING_TASK_VERDICT_STATUSES
from loopora.agent_native_v3 import AgentWorkPanelV3
from loopora.cli_summary_helpers import clip as _clip
from loopora.cli_summary_helpers import clip_inline as _clip_inline


def agent_work_panel(result: dict, *, summary: dict | None = None) -> AgentWorkPanelV3:
    run = result.get("run") if isinstance(result.get("run"), dict) else {}
    next_summary = _next_step_summary(result, summary=summary)
    task_verdict = run.get("task_verdict") if isinstance(run.get("task_verdict"), dict) else run.get("task_verdict_json")
    task_verdict = task_verdict if isinstance(task_verdict, dict) else {}
    verdict_status = str(task_verdict.get("status") or "").strip()
    task_proven = verdict_status in PASSING_TASK_VERDICT_STATUSES
    task_outcome = _task_outcome(result, task_proven=task_proven, verdict_status=verdict_status, summary=summary)
    top_gaps = _panel_top_gaps(next_summary)
    evidence_focus = _panel_evidence_focus(result, task_verdict=task_verdict, next_summary=next_summary, top_gaps=top_gaps)
    current_role = str(next_summary.get("role") or "").strip()
    current_step_id = str(next_summary.get("step_id") or "").strip()
    submitted_step = result.get("submitted_step") if isinstance(result.get("submitted_step"), dict) else {}
    if not current_role and isinstance(submitted_step.get("role"), dict):
        current_role = str(submitted_step["role"].get("name") or submitted_step["role"].get("id") or "").strip()
    if not current_step_id:
        current_step_id = str(submitted_step.get("step_id") or "").strip()
    return {
        "state": _panel_state(result, task_proven=task_proven, next_summary=next_summary),
        "run_id": str(run.get("id") or "").strip(),
        "task_proven": task_proven,
        "task_outcome": task_outcome,
        "current_role": current_role,
        "current_step_id": current_step_id,
        "next_action": _panel_next_action(result, next_summary=next_summary, task_proven=task_proven),
        "evidence_focus": evidence_focus,
        "top_gaps": top_gaps,
        "ask_user": _panel_ask_user(result),
        "todo_items": _panel_todo_items(next_summary),
        "run_url": str(result.get("run_url") or result.get("run_path") or "").strip(),
    }


def print_agent_work_panel(result: dict, *, summary: dict | None = None) -> None:
    panel = agent_work_panel(result, summary=summary)
    typer.echo("agent_work_panel:")
    for key in ("state", "run_id", "task_outcome", "current_role", "current_step_id", "next_action", "evidence_focus", "ask_user", "run_url"):
        value = panel.get(key)
        if value not in ("", [], {}, None):
            typer.echo(f"{key}: {_clip(str(value), 260)}")
    typer.echo(f"task_proven: {str(panel.get('task_proven') is True).lower()}")
    todo_items = [str(item).strip() for item in list(panel.get("todo_items") or []) if str(item).strip()]
    if todo_items:
        typer.echo("todo_items:")
        for item in todo_items[:4]:
            typer.echo(f"- {_clip(item, 180)}")
    top_gaps = [item for item in list(panel.get("top_gaps") or []) if isinstance(item, dict)]
    if top_gaps:
        typer.echo("top_gaps:")
        for item in top_gaps[:3]:
            rendered = _render_gap(item)
            if rendered:
                typer.echo(f"- {_clip(rendered, 220)}")


def _next_step_summary(result: dict, *, summary: dict | None) -> dict[str, object]:
    if isinstance(summary, dict):
        next_summary = summary.get("next_step")
        if isinstance(next_summary, dict):
            return next_summary
    next_step = result.get("next_step") if isinstance(result.get("next_step"), dict) else {}
    if not next_step:
        return {}
    run = result.get("run") if isinstance(result.get("run"), dict) else {}
    adapter = str(result.get("adapter") or next_step.get("adapter") or "").strip() or "codex"
    workdir = str(result.get("workdir") or run.get("workdir") or "").strip() or "$PWD"
    return agent_next_step_summary(next_step, adapter=adapter, workdir=workdir)


def _task_outcome(result: dict, *, task_proven: bool, verdict_status: str, summary: dict | None) -> str:
    if isinstance(summary, dict):
        value = str(summary.get("task_outcome") or "").strip()
        if value:
            return value
    if task_proven:
        return "proven"
    task_next_action = result.get("task_next_action") if isinstance(result.get("task_next_action"), dict) else {}
    if str(task_next_action.get("kind") or "").strip() == "continue_evidence":
        return "not_proven_continue_evidence"
    if result.get("complete") is True:
        return "not_proven"
    if verdict_status and verdict_status != "not_evaluated":
        return "not_proven_continue_evidence"
    return "not_yet_evaluated"


def _panel_state(result: dict, *, task_proven: bool, next_summary: dict[str, object]) -> str:
    if task_proven:
        return "task_proven"
    if isinstance(next_summary.get("dispatch_unavailable"), dict):
        return "dispatch_unavailable"
    submitted = result.get("submitted_step") if isinstance(result.get("submitted_step"), dict) else {}
    if str(submitted.get("status") or "").strip() == "blocked":
        return "blocked"
    if result.get("complete") is True:
        return "needs_more_evidence"
    if next_summary:
        return "awaiting_agent"
    run = result.get("run") if isinstance(result.get("run"), dict) else {}
    return str(run.get("run_status") or run.get("status") or "unknown").strip()


def _panel_next_action(result: dict, *, next_summary: dict[str, object], task_proven: bool) -> str:
    if task_proven:
        return "Task verdict passed; no new evidence pass starts unless the task scope changes."
    submitted = result.get("submitted_step") if isinstance(result.get("submitted_step"), dict) else {}
    if isinstance(next_summary.get("dispatch_unavailable"), dict) or str(submitted.get("status") or "").strip() == "blocked":
        return _panel_default_next_action(result, next_summary=next_summary, task_proven=task_proven)
    if result.get("complete") is True:
        return _panel_default_next_action(result, next_summary=next_summary, task_proven=task_proven)
    task_next_action = result.get("task_next_action") if isinstance(result.get("task_next_action"), dict) else {}
    guidance = str(task_next_action.get("guidance") or "").strip()
    if guidance:
        return guidance
    action = _panel_default_next_action(result, next_summary=next_summary, task_proven=task_proven)
    return action or "Continue the current Loopora handoff."


def _panel_default_next_action(result: dict, *, next_summary: dict[str, object], task_proven: bool) -> str:
    if task_proven:
        return "Task verdict passed; no new evidence pass starts unless the task scope changes."
    dispatch_unavailable = next_summary.get("dispatch_unavailable") if isinstance(next_summary.get("dispatch_unavailable"), dict) else {}
    if dispatch_unavailable:
        return str(dispatch_unavailable.get("next") or "Repair the managed role agent config before dispatch.").strip()
    dispatch_next = str(next_summary.get("dispatch_next") or "").strip()
    if dispatch_next:
        return dispatch_next
    submitted = result.get("submitted_step") if isinstance(result.get("submitted_step"), dict) else {}
    if str(submitted.get("status") or "").strip() == "blocked":
        raw_blockers = [str(item).strip() for item in list(submitted.get("blocking_items") or []) if str(item).strip()]
        blockers = [_actionable_blocking_item(item) for item in raw_blockers]
        action = _actionable_next_action(str(submitted.get("recommended_next_action") or "").strip(), blockers)
        return action or "Resolve the blocking item before continuing evidence."
    if result.get("complete") is True:
        return "Task proof is still missing; run /loopora-run again in this Agent session to continue evidence."
    return "Continue the current Loopora handoff."


def _panel_evidence_focus(result: dict, *, task_verdict: dict, next_summary: dict[str, object], top_gaps: list[dict]) -> str:
    task_next_action = result.get("task_next_action") if isinstance(result.get("task_next_action"), dict) else {}
    focus = str(task_next_action.get("task_verdict_summary") or "").strip()
    if focus:
        return _clip_inline(focus, 240)
    summary_focus = str(task_verdict.get("summary") or "").strip()
    if result.get("complete") is True and summary_focus:
        return _clip_inline(summary_focus, 240)
    continuation = next_summary.get("continuation") if isinstance(next_summary.get("continuation"), dict) else {}
    next_focus = continuation.get("next_focus") if isinstance(continuation.get("next_focus"), list) else []
    if next_focus:
        return _clip_inline(str(next_focus[0]), 240)
    if top_gaps:
        return _clip_inline(_render_gap(top_gaps[0]), 240)
    return ""


def _panel_top_gaps(next_summary: dict[str, object]) -> list[dict]:
    raw = next_summary.get("top_coverage_gaps")
    gaps = coverage_gap_summaries(raw, limit=3) if isinstance(raw, list) else []
    if gaps:
        return gaps
    iteration_repair = next_summary.get("iteration_repair") if isinstance(next_summary.get("iteration_repair"), dict) else {}
    raw_repair = iteration_repair.get("top_gaps")
    return coverage_gap_summaries(raw_repair, limit=3) if isinstance(raw_repair, list) else []


def _panel_todo_items(next_summary: dict[str, object]) -> list[str]:
    native_todo = next_summary.get("native_todo") if isinstance(next_summary.get("native_todo"), dict) else {}
    items = native_todo.get("items") if isinstance(native_todo.get("items"), list) else []
    return [str(item).strip() for item in items if str(item).strip()][:4]


def _panel_ask_user(result: dict) -> str:
    question_action = result.get("question_action") if isinstance(result.get("question_action"), dict) else {}
    return str(question_action.get("prompt") or result.get("ask_user") or "").strip()


def _render_gap(gap: dict) -> str:
    target = str(gap.get("target_id") or gap.get("id") or "").strip()
    status = str(gap.get("status") or "").strip()
    text = str(gap.get("text") or gap.get("reason") or gap.get("summary") or "").strip()
    pieces = []
    if target:
        pieces.append(target)
    if status:
        pieces.append(f"[{status}]")
    if text:
        pieces.append(text)
    return " ".join(pieces)
