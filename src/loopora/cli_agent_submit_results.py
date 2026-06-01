from __future__ import annotations

from loopora.agent_native_guidance import actionable_blocking_item as _actionable_blocking_item
from loopora.agent_native_guidance import actionable_next_action as _actionable_next_action
from loopora.agent_native_next_step_summary import agent_next_step_summary as _agent_next_step_summary
from loopora.agent_native_surface import attach_native_run_surface
from loopora.agent_native_task_proof import agent_task_proof_summary
from loopora.agent_native_v3 import agent_v3_envelope as _agent_v3_envelope
from loopora.agent_native_v3 import agent_v3_legacy_raw as _agent_v3_legacy_raw
from loopora.agent_native_v3 import agent_v3_status as _agent_v3_status
from loopora.agent_native_v3 import agent_v3_technical_handoff as _agent_v3_technical_handoff
from loopora.cli_agent_submitted_step_output import (
    _coverage_result_counts,
    _submitted_coverage_result_summaries,
    _submitted_step_is_blocked,
)
from loopora.cli_agent_work_panel import agent_work_panel as _agent_work_panel
from loopora.cli_summary_helpers import (
    clip_inline as _clip_inline,
    set_summary_list as _set_summary_list,
    set_summary_text as _set_summary_text,
)
from loopora.run_projection_fields import run_status_from_run, task_verdict_from_run


def _agent_submit_json_payload(result: dict) -> dict:
    summary = _agent_submit_summary(result)
    return _agent_v3_envelope(
        kind="agent_submit",
        status=_agent_v3_status(complete=result.get("complete")),
        summary=summary,
        extras={
            "technical_handoff": _agent_v3_technical_handoff(summary),
            "diagnostics": {"legacy_summary_key": "agent_submit_summary"},
            "raw": _agent_v3_legacy_raw(summary_key="agent_submit_summary", summary=summary, payload=result),
        },
    )


def _agent_submit_summary(result: dict) -> dict:
    run = result.get("run") if isinstance(result.get("run"), dict) else {}
    next_step = result.get("next_step") if isinstance(result.get("next_step"), dict) else {}
    adapter = str(result.get("adapter") or next_step.get("adapter") or "").strip() or "codex"
    workdir = str(result.get("workdir") or run.get("workdir") or "").strip() or "$PWD"
    task_verdict = task_verdict_from_run(run)
    summary: dict[str, object] = {
        "schema_version": 3,
        "run_id": str(run.get("id") or "").strip(),
        "run_status": run_status_from_run(run),
        "complete": bool(result.get("complete")),
    }
    submitted_summary = _agent_submitted_step_summary(result.get("submitted_step"))
    if submitted_summary:
        summary["submitted_step"] = submitted_summary
    next_summary = _agent_next_step_summary(next_step, adapter=adapter, workdir=workdir)
    if next_summary:
        summary["next_step"] = next_summary
    attach_native_run_surface(summary, adapter=adapter)
    _set_summary_text(summary, "run_url", result.get("run_url") or result.get("run_path"))
    verdict_status = _task_verdict_status(task_verdict)
    _set_summary_text(summary, "task_verdict_status", verdict_status)
    verdict_summary = ""
    if isinstance(task_verdict, dict):
        verdict_summary = _clip_inline(str(task_verdict.get("summary") or ""), 220)
        _set_summary_text(summary, "task_verdict_summary", verdict_summary)
    task_next_action = result.get("task_next_action") if isinstance(result.get("task_next_action"), dict) else {}
    if task_next_action:
        summary["task_next_action"] = task_next_action
    if result.get("auto_repair_applied") is True:
        summary["auto_repair_applied"] = True
        actions = [str(item).strip() for item in list(result.get("auto_repair_actions") or []) if str(item).strip()]
        if actions:
            summary["auto_repair_actions"] = actions
    summary.update(
        agent_task_proof_summary(
            complete=bool(result.get("complete")),
            task_verdict_status=verdict_status,
            task_verdict_summary=verdict_summary,
            task_next_action=task_next_action,
            normalize_next_evidence_focus=_agent_task_proof_focus,
        )
    )
    summary["agent_work_panel"] = _agent_work_panel(result, summary=summary)
    return {key: value for key, value in summary.items() if value not in ("", [], {})}


def _agent_submitted_step_summary(submitted_step: object) -> dict:
    if not isinstance(submitted_step, dict) or not submitted_step:
        return {}
    summary: dict[str, object] = {}
    _set_summary_text(summary, "step_id", submitted_step.get("step_id"))
    _set_summary_text(summary, "status", submitted_step.get("status"))
    _set_summary_list(summary, "evidence_refs", submitted_step.get("evidence_refs"))
    coverage_results = _submitted_coverage_result_summaries(submitted_step.get("coverage_results"), limit=8)
    if coverage_results:
        summary["coverage_results"] = coverage_results
        summary["coverage_result_counts"] = _coverage_result_counts(submitted_step.get("coverage_results"))
        raw_coverage_results = [item for item in list(submitted_step.get("coverage_results") or []) if isinstance(item, dict)]
        if len(raw_coverage_results) > len(coverage_results):
            summary["coverage_results_omitted"] = len(raw_coverage_results) - len(coverage_results)
    raw_blocking_items = [str(item).strip() for item in list(submitted_step.get("blocking_items") or []) if str(item).strip()]
    blocking_items = [_actionable_blocking_item(item) for item in raw_blocking_items]
    _set_summary_list(summary, "blocking_items", blocking_items)
    raw_next_action = str(submitted_step.get("recommended_next_action") or "").strip()
    status = str(submitted_step.get("status") or "").strip()
    if _submitted_step_is_blocked(status):
        next_action = _actionable_next_action(raw_next_action, blocking_items)
        _set_summary_text(summary, "recommended_next_action", next_action)
    _set_summary_text(summary, "handoff_path", submitted_step.get("handoff_absolute_path") or submitted_step.get("handoff_path"))
    host_dispatch = submitted_step.get("host_dispatch") if isinstance(submitted_step.get("host_dispatch"), dict) else {}
    native_trace = host_dispatch.get("native_trace") if isinstance(host_dispatch.get("native_trace"), dict) else {}
    if native_trace:
        summary["native_trace"] = native_trace
    _set_summary_text(summary, "summary", _clip_inline(str(submitted_step.get("summary") or ""), 220))
    return summary


def _task_verdict_status(task_verdict: object) -> str:
    if isinstance(task_verdict, dict):
        return str(task_verdict.get("status") or "").strip()
    return ""


def _agent_task_proof_focus(value: str) -> str:
    return _clip_inline(value, 220)
