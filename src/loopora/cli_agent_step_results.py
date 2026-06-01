from __future__ import annotations

from loopora.agent_native_next_step_sections import (
    agent_dispatch_unavailable_summary as _agent_dispatch_unavailable_summary,
    agent_next_step_continuation_summary as _agent_next_step_continuation_summary,
)
from loopora.agent_native_next_step_summary import (
    agent_next_step_summary as _agent_next_step_summary,
)
from loopora.agent_native_surface import attach_native_run_surface
from loopora.agent_native_task_proof import agent_task_proof_summary
from loopora.agent_native_v3 import agent_v3_envelope as _agent_v3_envelope
from loopora.agent_native_v3 import agent_v3_legacy_raw as _agent_v3_legacy_raw
from loopora.agent_native_v3 import agent_v3_status as _agent_v3_status
from loopora.agent_native_v3 import agent_v3_technical_handoff as _agent_v3_technical_handoff
from loopora.cli_agent_work_panel import agent_work_panel as _agent_work_panel
from loopora.cli_summary_helpers import (
    clip_inline as _clip_inline,
    set_summary_text as _set_summary_text,
)
from loopora.run_projection_fields import run_status_from_run, task_verdict_from_run


def _attach_agent_run_summary(result: dict) -> None:
    summary = result.get("agent_run_summary") if isinstance(result.get("agent_run_summary"), dict) else {}
    next_step = result.get("next_step") if isinstance(result.get("next_step"), dict) else {}
    role_dispatch = next_step.get("role_dispatch") if isinstance(next_step.get("role_dispatch"), dict) else {}
    adapter = str(result.get("adapter") or next_step.get("adapter") or "").strip() or "codex"
    run = result.get("run") if isinstance(result.get("run"), dict) else {}
    workdir = str(result.get("workdir") or run.get("workdir") or "").strip() or "$PWD"
    if not summary:
        summary = {
            "schema_version": 3,
            "run_id": str(run.get("id") or "").strip(),
            "run_status": run_status_from_run(run),
            "started_new_run": bool(result.get("started_new_run")),
            "complete": bool(result.get("complete")),
        }
        result["agent_run_summary"] = summary
    _set_summary_text(summary, "next_step_id", next_step.get("step_id"))
    _set_summary_text(summary, "next_target_agent", role_dispatch.get("target_agent"))
    task_verdict = task_verdict_from_run(run)
    verdict_status = _task_verdict_status(task_verdict)
    _set_summary_text(summary, "task_verdict_status", verdict_status)
    verdict_summary = ""
    if isinstance(task_verdict, dict):
        verdict_summary = _clip_inline(str(task_verdict.get("summary") or ""), 220)
        _set_summary_text(summary, "task_verdict_summary", verdict_summary)
    task_next_action = result.get("task_next_action") if isinstance(result.get("task_next_action"), dict) else {}
    summary.update(
        agent_task_proof_summary(
            complete=bool(result.get("complete")),
            task_verdict_status=verdict_status,
            task_verdict_summary=verdict_summary,
            task_next_action=task_next_action,
            normalize_next_evidence_focus=_agent_task_proof_focus,
        )
    )
    attach_native_run_surface(summary, adapter=adapter)
    if not role_dispatch:
        summary["agent_work_panel"] = _agent_work_panel(result, summary=summary)
        _attach_agent_v3_run_envelope(result, summary)
        return
    target_config = str(role_dispatch.get("target_agent_config_absolute_path") or role_dispatch.get("target_agent_config_path") or "").strip()
    if target_config:
        summary["next_target_agent_config"] = target_config
    if "target_agent_config_exists" in role_dispatch:
        summary["next_target_agent_config_exists"] = role_dispatch.get("target_agent_config_exists") is True
    next_step_summary = _agent_next_step_summary(next_step, adapter=adapter, workdir=workdir)
    if next_step_summary:
        summary["next_step"] = next_step_summary
        _set_summary_text(summary, "dispatch_next", next_step_summary.get("dispatch_next"))
        _set_summary_text(summary, "next_context_path", next_step_summary.get("context_path"))
        _set_summary_text(summary, "next_step_contract_path", next_step_summary.get("step_contract_path"))
        _set_summary_text(summary, "next_result_template", next_step_summary.get("result_template"))
        _set_summary_text(summary, "next_submit_command", next_step_summary.get("submit_command"))
    dispatch_unavailable = _agent_dispatch_unavailable_summary(adapter=adapter, workdir=workdir, role_dispatch=role_dispatch)
    if dispatch_unavailable:
        summary["dispatch_unavailable"] = dispatch_unavailable
    summary.update(_agent_next_step_continuation_summary(next_step))
    summary["agent_work_panel"] = _agent_work_panel(result, summary=summary)
    _attach_agent_v3_run_envelope(result, summary)


def _attach_agent_v3_run_envelope(result: dict, summary: dict) -> None:
    result["agent_v3_envelope"] = _agent_v3_envelope(
        kind="agent_run",
        status=_agent_v3_status(complete=result.get("complete")),
        summary=summary,
        extras={
            "technical_handoff": _agent_v3_technical_handoff(summary),
            "diagnostics": {"legacy_summary_key": "agent_run_summary"},
            "raw": _agent_v3_legacy_raw(summary_key="agent_run_summary", summary=summary, payload=result),
        },
    )


def _attach_agent_run_dispatch_summary(result: dict) -> None:
    _attach_agent_run_summary(result)


def _agent_next_json_payload(result: dict) -> dict:
    summary = _agent_next_summary(result)
    return _agent_v3_envelope(
        kind="agent_next",
        status=_agent_v3_status(complete=result.get("complete")),
        summary=summary,
        extras={
            "technical_handoff": _agent_v3_technical_handoff(summary),
            "diagnostics": {"legacy_summary_key": "agent_next_summary"},
            "raw": _agent_v3_legacy_raw(summary_key="agent_next_summary", summary=summary, payload=result),
        },
    )


def _agent_next_summary(result: dict) -> dict:
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
        "handoff_kind": "current_step",
    }
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


def _task_verdict_status(task_verdict: object) -> str:
    if isinstance(task_verdict, dict):
        return str(task_verdict.get("status") or "").strip()
    return ""


def _agent_task_proof_focus(value: str) -> str:
    return _clip_inline(value, 220)
