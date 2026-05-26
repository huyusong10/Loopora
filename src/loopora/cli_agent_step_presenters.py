from __future__ import annotations

import typer

from loopora.agent_native_next_step_summary import (
    agent_dispatch_unavailable_summary as _agent_dispatch_unavailable_summary,
    agent_next_step_continuation_summary as _agent_next_step_continuation_summary,
    agent_next_step_summary as _agent_next_step_summary,
)
from loopora.agent_native_task_proof import (
    AGENT_RUN_LIFECYCLE_SOURCE,
    AGENT_TASK_PROOF_SOURCE,
    PASSING_TASK_VERDICT_STATUSES,
    agent_task_proof_summary,
)
from loopora.agent_native_surface import attach_native_run_surface, agent_native_run_surface_for_result, native_surface_plain_lines
from loopora.cli_agent_current_step_output import _print_agent_current_step
from loopora.cli_agent_runtime_support import print_web_status as _print_web_status
from loopora.agent_native_v3 import agent_v3_envelope as _agent_v3_envelope
from loopora.agent_native_v3 import agent_v3_legacy_raw as _agent_v3_legacy_raw
from loopora.agent_native_v3 import agent_v3_status as _agent_v3_status
from loopora.agent_native_v3 import agent_v3_technical_handoff as _agent_v3_technical_handoff
from loopora.cli_agent_submitted_step_output import (
    _actionable_blocking_item,
    _actionable_next_action,
    _coverage_result_counts,
    _print_agent_submitted_step,
    _submitted_coverage_result_summaries,
    _submitted_step_is_blocked,
)
from loopora.cli_agent_work_panel import agent_work_panel as _agent_work_panel
from loopora.cli_agent_work_panel import print_agent_work_panel as _print_agent_work_panel
from loopora.cli_run_support import print_run_contract_summary, print_task_verdict
from loopora.cli_shared import echo_json
from loopora.cli_summary_helpers import (
    clip as _clip,
    clip_inline as _clip_inline,
    set_summary_list as _set_summary_list,
    set_summary_text as _set_summary_text,
)

def _print_agent_loop_result(result: dict, *, json_output: bool) -> None:
    if json_output:
        _attach_agent_run_summary(result)
        echo_json(result["agent_v3_envelope"])
        return
    _print_agent_work_panel(result)
    run = result.get("run") if isinstance(result.get("run"), dict) else {}
    typer.echo(f"Loopora run: {run.get('id')}")
    typer.echo(f"run_status: {run.get('run_status') or run.get('status')}")
    _print_agent_loop_start_state(result)
    _print_agent_native_run_surface(result)
    print_run_contract_summary(run)
    task_verdict = run.get("task_verdict") or run.get("task_verdict_json")
    if result.get("complete"):
        print_task_verdict(task_verdict)
        _print_terminal_task_next_action(task_verdict, result.get("task_next_action"))
        _print_agent_native_terminal_state(task_verdict)
    typer.echo(f"run_url: {result.get('run_url') or result.get('run_path')}")
    _print_web_status(result)
    next_step = result.get("next_step") if isinstance(result.get("next_step"), dict) else {}
    if next_step:
        _print_agent_current_step(next_step)


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
            "run_status": str(run.get("run_status") or run.get("status") or "").strip(),
            "started_new_run": bool(result.get("started_new_run")),
            "complete": bool(result.get("complete")),
        }
        result["agent_run_summary"] = summary
    _set_summary_text(summary, "next_step_id", next_step.get("step_id"))
    _set_summary_text(summary, "next_target_agent", role_dispatch.get("target_agent"))
    task_verdict = run.get("task_verdict") or run.get("task_verdict_json")
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
        _set_summary_text(summary, "next_capsule_path", next_step_summary.get("capsule_path"))
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


def _print_agent_loop_start_state(result: dict) -> None:
    if "started_new_run" not in result:
        return
    if result.get("started_new_run") is True:
        typer.echo("run_start: started_new_agent_native_run")
    elif result.get("complete") is True:
        typer.echo("run_start: replayed_existing_terminal_run")
    else:
        typer.echo("run_start: resumed_existing_agent_native_run")


def _print_agent_step_result(result: dict, *, json_output: bool) -> None:
    if json_output:
        echo_json(_agent_submit_json_payload(result))
        return
    _print_agent_work_panel(result)
    if result.get("auto_repair_applied") is True:
        actions = [str(item).strip() for item in list(result.get("auto_repair_actions") or []) if str(item).strip()]
        rendered = ", ".join(actions[:4]) if actions else "safe wrapper repair"
        typer.echo(f"auto_repair: submitted result format repaired before submit ({rendered})")
    run = result.get("run") if isinstance(result.get("run"), dict) else {}
    typer.echo(f"Loopora run: {run.get('id')}")
    typer.echo(f"run_status: {run.get('run_status') or run.get('status')}")
    _print_agent_native_run_surface(result)
    _print_agent_submitted_step(result.get("submitted_step"))
    print_run_contract_summary(run)
    task_verdict = run.get("task_verdict") or run.get("task_verdict_json")
    if result.get("complete"):
        print_task_verdict(task_verdict)
        _print_terminal_task_next_action(task_verdict, result.get("task_next_action"))
    typer.echo(f"run_url: {result.get('run_url') or result.get('run_path')}")
    _print_web_status(result)
    next_step = result.get("next_step") if isinstance(result.get("next_step"), dict) else {}
    if result.get("complete"):
        _print_agent_native_terminal_state(task_verdict)
    elif next_step:
        _print_agent_current_step(next_step)


def _print_agent_next_result(result: dict, *, json_output: bool) -> None:
    if json_output:
        echo_json(_agent_next_json_payload(result))
        return
    _print_agent_step_result(result, json_output=False)


def _print_agent_native_run_surface(result: dict) -> None:
    next_step = result.get("next_step") if isinstance(result.get("next_step"), dict) else {}
    surface = agent_native_run_surface_for_result(result, next_step)
    for line in native_surface_plain_lines(surface):
        typer.echo(line)


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
    task_verdict = run.get("task_verdict") or run.get("task_verdict_json")
    summary: dict[str, object] = {
        "schema_version": 3,
        "run_id": str(run.get("id") or "").strip(),
        "run_status": str(run.get("run_status") or run.get("status") or "").strip(),
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
    task_verdict = run.get("task_verdict") or run.get("task_verdict_json")
    summary: dict[str, object] = {
        "schema_version": 3,
        "run_id": str(run.get("id") or "").strip(),
        "run_status": str(run.get("run_status") or run.get("status") or "").strip(),
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


def _print_agent_native_terminal_state(task_verdict: object) -> None:
    status = _task_verdict_status(task_verdict)
    if status in PASSING_TASK_VERDICT_STATUSES:
        typer.echo("agent_native: complete")
        _print_agent_native_terminal_sources()
        return
    if not status:
        status = "not_evaluated"
    typer.echo("agent_native: lifecycle_closed_task_unproven")
    typer.echo(f"agent_native_task_verdict: {status}")
    _print_agent_native_terminal_sources()


def _print_agent_native_terminal_sources() -> None:
    typer.echo(f"task_proof_source: {AGENT_TASK_PROOF_SOURCE}")
    typer.echo(f"run_lifecycle_source: {AGENT_RUN_LIFECYCLE_SOURCE}")


def _print_terminal_task_next_action(task_verdict: object, task_next_action: object = None) -> None:
    action = task_next_action if isinstance(task_next_action, dict) else {}
    status = _task_verdict_status(task_verdict)
    summary = ""
    if isinstance(task_verdict, dict):
        summary = str(task_verdict.get("summary") or "").strip()
    if status in PASSING_TASK_VERDICT_STATUSES:
        typer.echo("task_next_action: task verdict already passed; no new evidence pass will start unless the task scope changes")
        return
    if not status:
        status = "not_evaluated"
    guidance = str(action.get("guidance") or "").strip() if action else ""
    typer.echo(
        "task_next_action: "
        + (
            guidance
            if guidance
            else "run lifecycle is complete but the task is not proven; run /loopora-run again in this Agent session to start the next evidence pass"
        )
    )
    typer.echo(f"next_loop_command: {(action.get('next_loop_command') or '/loopora-run')!s}")
    plan_action = str(action.get("plan_action") or "").strip()
    if plan_action == "open_run_url_improve_with_evidence_if_loop_needs_adjustment":
        typer.echo("next_plan_action: open run_url and use Improve plan with evidence if the Loop itself needs adjustment")
    elif plan_action:
        typer.echo(f"next_plan_action: {plan_action}")
    else:
        typer.echo("next_plan_action: open run_url and use Improve plan with evidence if the Loop itself needs adjustment")
    action_summary = str(action.get("task_verdict_summary") or "").strip()
    if action_summary:
        summary = action_summary
    if summary:
        typer.echo(f"next_evidence_focus: {_clip(summary, 220)}")
