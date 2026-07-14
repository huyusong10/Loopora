from __future__ import annotations

from loopora.agent_native_guidance import actionable_blocking_item as _actionable_blocking_item
from loopora.agent_native_guidance import actionable_next_action as _actionable_next_action
from loopora.agent_native_compact_handoff import compact_agent_next_step, compact_agent_work_panel
from loopora.agent_native_coverage_summary import (
    coverage_gap_summaries as _coverage_gap_summaries,
    required_coverage_summary as _required_coverage_summary,
)
from loopora.agent_native_experience_artifacts import write_agent_v3_experience_artifact as _write_agent_v3_experience_artifact
from loopora.agent_native_next_step_summary import agent_next_step_summary as _agent_next_step_summary
from loopora.agent_native_surface import attach_native_run_surface
from loopora.agent_native_task_proof import agent_task_proof_summary
from loopora.agent_native_v3 import AGENT_NATIVE_V3_SCHEMA_VERSION
from loopora.agent_native_v3 import agent_v3_envelope as _agent_v3_envelope
from loopora.agent_native_v3 import agent_v3_legacy_raw as _agent_v3_legacy_raw
from loopora.agent_native_v3 import agent_v3_status as _agent_v3_status
from loopora.agent_native_v3 import agent_v3_technical_handoff as _agent_v3_technical_handoff
from loopora.cli_agent_submitted_step_output import (
    _coverage_result_counts,
    _submitted_step_is_blocked,
)
from loopora.cli_agent_work_panel import agent_work_panel as _agent_work_panel
from loopora.cli_summary_helpers import (
    clip_inline as _clip_inline,
    set_summary_before as _set_summary_before,
    set_summary_list as _set_summary_list,
    set_summary_text as _set_summary_text,
)
from loopora.run_projection_fields import run_status_from_run, task_verdict_from_run
from loopora.summary_projection_helpers import non_bool_int as _non_bool_int


def _agent_submit_json_payload(result: dict, *, include_raw: bool = True) -> dict:
    summary = _agent_submit_summary(result, compact=not include_raw)
    extras = {
        "technical_handoff": _agent_v3_technical_handoff(summary),
        "diagnostics": {"legacy_summary_key": "agent_submit_summary"},
    }
    if include_raw:
        extras["raw"] = _agent_v3_legacy_raw(summary_key="agent_submit_summary", summary=summary, payload=result)
    envelope = _agent_v3_envelope(
        kind="agent_submit",
        status=_agent_v3_status(complete=result.get("complete")),
        summary=summary,
        extras=extras,
    )
    _write_agent_v3_experience_artifact(result, envelope)
    return envelope


def _agent_submit_summary(result: dict, *, compact: bool = False) -> dict:
    run = result.get("run") if isinstance(result.get("run"), dict) else {}
    next_step = result.get("next_step") if isinstance(result.get("next_step"), dict) else {}
    adapter = str(result.get("adapter") or next_step.get("adapter") or "").strip() or "codex"
    workdir = str(result.get("workdir") or run.get("workdir") or "").strip()
    task_verdict = task_verdict_from_run(run)
    summary: dict[str, object] = {
        "schema_version": AGENT_NATIVE_V3_SCHEMA_VERSION,
        "run_id": str(run.get("id") or "").strip(),
        "run_status": run_status_from_run(run),
        "complete": bool(result.get("complete")),
    }
    submitted_summary = _agent_submitted_step_summary(result.get("submitted_step"))
    if submitted_summary:
        summary["submitted_step"] = submitted_summary
    next_summary = _agent_next_step_summary(next_step, adapter=adapter, workdir=workdir, compact=compact)
    if next_summary:
        role_dispatch_message = next_summary.get("role_dispatch_message")
        displayed_next_summary = compact_agent_next_step(next_summary) if compact else next_summary
        summary["next_step"] = displayed_next_summary
        _set_summary_text(summary, "next_step_id", next_summary.get("step_id"))
        _set_summary_text(summary, "next_target_agent", next_summary.get("target_agent"))
        _set_summary_text(summary, "dispatch_next", next_summary.get("dispatch_next"))
        _set_summary_text(summary, "next_context_path", next_summary.get("context_path"))
        _set_summary_text(summary, "next_step_contract_path", next_summary.get("step_contract_path"))
        _set_summary_text(summary, "next_result_template", next_summary.get("result_template"))
        _set_summary_text(summary, "next_result_file", next_summary.get("result_file_to_write"))
        _set_summary_text(summary, "next_submit_command", next_summary.get("submit_command"))
        _set_summary_text(summary, "next_role_dispatch_message", role_dispatch_message)
    coverage_after_submit = _coverage_after_submit_summary(
        result.get("coverage_after_submit"),
        next_step=next_step,
        task_verdict=task_verdict,
    )
    if coverage_after_submit:
        summary["coverage_after_submit"] = coverage_after_submit
    attach_native_run_surface(summary, adapter=adapter, compact=compact)
    _attach_run_url_summary(summary, result)
    verdict_status = _task_verdict_status(task_verdict)
    _set_summary_text(summary, "task_verdict_status", verdict_status)
    verdict_summary = ""
    if isinstance(task_verdict, dict):
        verdict_summary = _clip_inline(str(task_verdict.get("summary") or ""), 220)
        _set_summary_text(summary, "task_verdict_summary", verdict_summary)
    task_next_action = result.get("task_next_action") if isinstance(result.get("task_next_action"), dict) else {}
    if task_next_action:
        summary["task_next_action"] = task_next_action
    _set_summary_text(summary, "host_dispatch_attestation_source", result.get("host_dispatch_attestation_source"))
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
    panel = _agent_work_panel(result, summary=summary)
    _set_summary_before(
        summary,
        "agent_work_panel",
        compact_agent_work_panel(panel) if compact else panel,
        "agent_surface",
    )
    return {key: value for key, value in summary.items() if value not in ("", [], {})}


def _agent_submitted_step_summary(submitted_step: object) -> dict:
    if not isinstance(submitted_step, dict) or not submitted_step:
        return {}
    summary: dict[str, object] = {}
    _set_summary_text(summary, "step_id", submitted_step.get("step_id"))
    _set_summary_text(summary, "status", submitted_step.get("status"))
    _set_summary_list(summary, "evidence_refs", submitted_step.get("evidence_refs"))
    raw_coverage_results = _submitted_coverage_result_items(submitted_step.get("coverage_results"))
    if raw_coverage_results:
        _set_summary_text(summary, "coverage_result_scope", _coverage_result_scope(submitted_step))
        summary["coverage_result_counts"] = _coverage_result_counts(raw_coverage_results)
        coverage_preview = _submitted_coverage_result_preview(raw_coverage_results, limit=3)
        if coverage_preview:
            summary["coverage_results_preview"] = coverage_preview
        if len(raw_coverage_results) > len(coverage_preview):
            summary["coverage_results_omitted"] = len(raw_coverage_results) - len(coverage_preview)
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


def _attach_run_url_summary(summary: dict[str, object], result: dict) -> None:
    _set_summary_text(summary, "run_url", result.get("run_url") or result.get("run_path"))
    _set_summary_text(summary, "run_url_status", result.get("run_url_status"))
    _set_summary_text(summary, "run_url_web_start_command", result.get("run_url_web_start_command"))


def _agent_task_proof_focus(value: str) -> str:
    return _clip_inline(value, 220)


def _submitted_coverage_result_items(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _submitted_coverage_result_preview(value: object, *, limit: int) -> list[dict[str, object]]:
    previews: list[dict[str, object]] = []
    for item in _submitted_coverage_result_items(value):
        target_id = str(item.get("target_id") or "").strip()
        status = str(item.get("status") or "").strip()
        if not target_id or not status:
            continue
        preview: dict[str, object] = {"target_id": target_id, "status": status}
        evidence_refs = [str(ref).strip() for ref in list(item.get("evidence_refs") or []) if str(ref).strip()]
        if evidence_refs:
            preview["evidence_refs"] = evidence_refs[:3]
        previews.append(preview)
        if len(previews) >= limit:
            break
    return previews


def _coverage_result_scope(submitted_step: dict) -> str:
    scope = str(submitted_step.get("coverage_result_scope") or submitted_step.get("coverage_results_scope") or "").strip()
    return scope or "submitted_role_raw_classifications_not_aggregated_coverage"


def _coverage_after_submit_summary(value: object, *, next_step: dict, task_verdict: object) -> dict[str, object]:
    if isinstance(value, dict) and value:
        return _coverage_projection_summary(value, source=str(value.get("source") or "coverage_after_submit").strip())
    required_coverage = next_step.get("required_coverage") if isinstance(next_step.get("required_coverage"), dict) else {}
    if required_coverage:
        return _coverage_projection_summary(required_coverage, source="next_step.required_coverage")
    if isinstance(task_verdict, dict):
        summary: dict[str, object] = {"source": "run.task_verdict"}
        _set_summary_text(summary, "status", task_verdict.get("status"))
        _set_summary_text(summary, "summary", _clip_inline(str(task_verdict.get("summary") or ""), 220))
        return summary
    return {}


def _coverage_projection_summary(value: dict, *, source: str) -> dict[str, object]:
    summary: dict[str, object] = {}
    _set_summary_text(summary, "source", source)
    _set_summary_text(summary, "status", value.get("status"))
    _set_summary_text(summary, "required_coverage", _required_coverage_summary(value))
    raw_summary = value.get("summary") if isinstance(value.get("summary"), dict) else {}
    reason = str(value.get("summary") if isinstance(value.get("summary"), str) else raw_summary.get("reason") or "").strip()
    if reason:
        _set_summary_text(summary, "summary", _clip_inline(reason, 220))
    for key in (
        "target_count",
        "covered_target_count",
        "weak_target_count",
        "missing_target_count",
        "blocked_target_count",
        "check_count",
        "covered_check_count",
        "missing_check_count",
        "residual_risk_count",
    ):
        count = _non_bool_int(value.get(key))
        if count is not None:
            summary[key] = count
    missing_check_ids = [str(item).strip() for item in list(value.get("missing_check_ids") or []) if str(item).strip()]
    if missing_check_ids:
        summary["missing_check_ids"] = missing_check_ids[:8]
        if len(missing_check_ids) > 8:
            summary["missing_check_ids_omitted"] = len(missing_check_ids) - 8
    top_gaps = _coverage_gap_summaries(value.get("top_gaps"), limit=3)
    if top_gaps:
        summary["top_gaps"] = top_gaps
    return {key: item for key, item in summary.items() if item not in ("", [], {})}
