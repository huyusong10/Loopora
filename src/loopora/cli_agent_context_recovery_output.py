from __future__ import annotations

import typer

from loopora.agent_native_surface import attach_native_run_surface
from loopora.agent_native_v3 import agent_v3_envelope
from loopora.agent_native_v3 import agent_v3_legacy_raw
from loopora.agent_native_v3 import agent_v3_technical_handoff
from loopora import cli_agent_recoverable_context_output as _recoverable_context_output
from loopora.cli_agent_plan_repair_hints import validation_repair_hints as _plan_validation_repair_hints
from loopora.cli_agent_runtime_support import print_web_url as _print_web_url
from loopora.cli_summary_helpers import (
    set_summary_list as _set_summary_list,
    set_summary_mapping as _set_summary_mapping,
    set_summary_text as _set_summary_text,
)


def _agent_loop_recovery_json_payload(result: dict) -> dict:
    summary = _agent_loop_recovery_summary(result)
    return _agent_recovery_v3_envelope(result, summary, legacy_summary_key="agent_loop_recovery_summary")


def _agent_next_recovery_json_payload(result: dict) -> dict:
    summary = _agent_loop_recovery_summary(result)
    return _agent_recovery_v3_envelope(result, summary, legacy_summary_key="agent_next_recovery_summary")


def _agent_recovery_v3_envelope(result: dict, summary: dict, *, legacy_summary_key: str) -> dict:
    return agent_v3_envelope(
        kind="agent_recovery",
        status="blocked",
        summary=summary,
        extras={
            "technical_handoff": agent_v3_technical_handoff(summary),
            "diagnostics": {"legacy_summary_key": legacy_summary_key},
            "raw": agent_v3_legacy_raw(summary_key=legacy_summary_key, summary=summary, payload=result),
        },
    )


def _agent_loop_recovery_summary(result: dict) -> dict:
    summary: dict[str, object] = {
        "ready": bool(result.get("ready")),
        "loop_recovery": _visible_loop_recovery(str(result.get("loop_recovery") or "").strip()),
    }
    if result.get("loop_recovery") == "repair_candidate_plan_file":
        _attach_repair_candidate_summary(summary, result)
    attach_native_run_surface(summary, result)
    _set_summary_text(summary, "workdir", result.get("workdir"))
    if result.get("loop_recovery") == "choose_recoverable_context":
        _attach_recoverable_context_summary(summary, result)
    elif result.get("loop_recovery") == "active_run_conflict":
        _attach_active_run_conflict_summary(summary, result)
    else:
        _set_summary_text(summary, "message", result.get("message"))
        _set_summary_text(summary, "next_plan_command", result.get("next_plan_command"))
        _set_summary_list(summary, "required_inputs", result.get("required_inputs"))
        _set_summary_text(summary, "ask_user", result.get("ask_user"))
        _set_summary_mapping(summary, "question_action", result.get("question_action"))
        _set_summary_text(summary, "example_user_reply", result.get("example_user_reply"))
        _set_summary_text(summary, "message_source_policy", result.get("message_source_policy"))
        _set_summary_text(summary, "message_cli_command", result.get("message_cli_command"))
        _set_summary_text(summary, "next_plan_cli_command", result.get("next_plan_cli_command"))
        _set_summary_text(summary, "task_message_template", result.get("task_message_template"))
        _set_summary_text(summary, "first_task_message_example", result.get("first_task_message_example"))
        for key in ("first_task_message_example_state", "first_task_handoff_policy"):
            _set_summary_mapping(summary, key, result.get(key))
        _set_summary_text(summary, "debug_cli_example_command", result.get("debug_cli_example_command"))
        _set_summary_text(summary, "next", result.get("next"))
        _set_summary_text(summary, "check_command", result.get("check_command"))
        _set_summary_text(summary, "context_card_error", result.get("context_card_error") or result.get("binding_error"))
        _set_summary_text(summary, "preview_url", result.get("preview_url") or result.get("preview_path"))
        _set_summary_text(summary, "preview_url_status", result.get("preview_url_status"))
        _set_summary_text(summary, "preview_url_web_start_command", result.get("preview_url_web_start_command"))
        _set_summary_text(summary, "validation_error", result.get("validation_error") or _agent_gen_error_summary(result))
        _set_summary_list(summary, "repair_focus", result.get("repair_focus"))
        _set_summary_text(summary, "repair_task_message", result.get("repair_task_message"))
        _set_summary_text(summary, "plan_file_to_repair", result.get("plan_file_to_repair"))
        _set_summary_text(summary, "preview_plan_copy", result.get("preview_plan_copy"))
        _set_summary_text(summary, "next_plan_command", result.get("next_plan_command"))
        _set_summary_text(summary, "repair_slash_command", result.get("repair_slash_command"))
        _set_summary_text(summary, "repair_cli_command", result.get("repair_cli_command"))
        _set_summary_text(summary, "repair_cli_command_policy", result.get("repair_cli_command_policy"))
        _set_summary_text(summary, "repair_reference", result.get("repair_reference"))
        _set_summary_text(summary, "next_review_step", result.get("next_review_step"))
        _set_summary_text(summary, "review_status", result.get("review_status"))
        _set_summary_text(summary, "task_anchor_status", result.get("task_anchor_status"))
        _set_summary_text(summary, "task_anchor_preview", result.get("task_anchor_preview"))
        _set_summary_text(summary, "review_scope", result.get("review_scope"))
        _set_summary_text(summary, "next_repair_step", result.get("next_repair_step"))
        _set_summary_text(summary, "run_blocked_until_web_review", result.get("run_blocked_until_web_review"))
        _set_summary_text(summary, "after_review_cli_command_status", result.get("after_review_cli_command_status"))
        _set_summary_text(summary, "after_review_slash_command", result.get("after_review_slash_command"))
        _set_summary_text(summary, "after_web_review_cli_command", result.get("after_web_review_cli_command"))
        _set_summary_text(summary, "after_review_cli_command", result.get("after_review_cli_command"))
    return {key: value for key, value in summary.items() if value not in ("", [], {})}


def _attach_repair_candidate_summary(summary: dict[str, object], result: dict) -> None:
    _set_summary_mapping(summary, "agent_work_panel", result.get("agent_work_panel"))
    _set_summary_mapping(summary, "repair_action", result.get("repair_action"))
    _set_summary_text(summary, "validation_error", result.get("validation_error") or _agent_gen_error_summary(result))
    _set_summary_list(summary, "repair_focus", result.get("repair_focus"))
    _set_summary_text(summary, "repair_task_message", result.get("repair_task_message"))
    _set_summary_text(summary, "plan_file_to_repair", result.get("plan_file_to_repair"))
    _set_summary_text(summary, "preview_plan_copy", result.get("preview_plan_copy"))
    _set_summary_text(summary, "next_plan_command", result.get("next_plan_command"))
    _set_summary_text(summary, "repair_slash_command", result.get("repair_slash_command"))
    _set_summary_text(summary, "repair_cli_command", result.get("repair_cli_command"))
    _set_summary_text(summary, "repair_cli_command_policy", result.get("repair_cli_command_policy"))
    _set_summary_text(summary, "repair_reference", result.get("repair_reference"))
    _set_summary_text(summary, "next_repair_step", result.get("next_repair_step"))


def _visible_loop_recovery(loop_recovery: str) -> str:
    if loop_recovery == "repair_agent_binding":
        return "repair_context_card"
    return loop_recovery


def _attach_recoverable_context_summary(summary: dict[str, object], result: dict) -> None:
    _recoverable_context_output.attach_recoverable_context_summary(summary, result)


def _recoverable_context_choice_summary(choice: dict) -> dict:
    return _recoverable_context_output.recoverable_context_choice_summary(choice)


def _print_recoverable_context_choices(resolution: dict) -> None:
    _recoverable_context_output.print_recoverable_context_choices(resolution)


def _display_recoverable_context_choices(choices: list[dict], *, limit: int) -> list[dict]:
    return _recoverable_context_output.display_recoverable_context_choices(choices, limit=limit)


def _recoverable_context_selection_hint(choices: list[dict]) -> str:
    return _recoverable_context_output.recoverable_context_selection_hint(choices)


def _recoverable_context_next_instruction(choices: list[dict]) -> str:
    return _recoverable_context_output.recoverable_context_next_instruction(choices)


def _validation_repair_hints(validation_error: str) -> list[str]:
    return _plan_validation_repair_hints(validation_error)


def _attach_active_run_conflict_summary(summary: dict[str, object], result: dict) -> None:
    active_runs = [run for run in result.get("active_runs") or [] if isinstance(run, dict)]
    summary["active_run_count"] = len(active_runs)
    compact_runs = [_active_run_conflict_run_summary(run) for run in active_runs[:5]]
    compact_runs = [run for run in compact_runs if run]
    if compact_runs:
        summary["active_runs"] = compact_runs
    _set_summary_text(summary, "message", result.get("message"))
    _set_summary_text(summary, "active_run_url", result.get("active_run_url") or result.get("active_run_path"))
    _set_summary_text(summary, "active_run_url_status", result.get("active_run_url_status"))
    _set_summary_text(summary, "active_run_url_web_start_command", result.get("active_run_url_web_start_command"))
    _set_summary_text(summary, "next_active_run_command", result.get("next_active_run_command"))
    _set_summary_text(summary, "stop_active_run_command", result.get("stop_active_run_command"))


def _active_run_conflict_run_summary(run: dict) -> dict:
    summary: dict[str, object] = {}
    _set_summary_text(summary, "id", run.get("id"))
    _set_summary_text(summary, "status", run.get("status"))
    _set_summary_text(summary, "loop_id", run.get("loop_id"))
    _set_summary_text(summary, "loop_name", run.get("loop_name"))
    _set_summary_text(summary, "active_role", run.get("active_role"))
    if run.get("current_iter") is not None:
        summary["current_iter"] = run.get("current_iter")
    _set_summary_text(summary, "updated_at", run.get("updated_at"))
    step = run.get("current_step") if isinstance(run.get("current_step"), dict) else {}
    step_summary: dict[str, object] = {}
    _set_summary_text(step_summary, "step_id", step.get("step_id"))
    _set_summary_text(step_summary, "target_agent", step.get("target_agent"))
    _set_summary_text(step_summary, "context_path", step.get("context_path"))
    _set_summary_text(step_summary, "result_template_path", step.get("result_template_path"))
    if step_summary:
        summary["current_step"] = step_summary
    return summary


def _print_active_run_conflict_recovery(result: dict) -> None:
    message = str(result.get("message") or "").strip()
    if message:
        typer.echo(f"message: {message}")
    runs = [run for run in list(result.get("active_runs") or []) if isinstance(run, dict)]
    if runs:
        typer.echo("active_runs:")
    for run in runs[:5]:
        step = run.get("current_step") if isinstance(run.get("current_step"), dict) else {}
        step_bits = ""
        if step.get("step_id") or step.get("target_agent"):
            step_bits = f" step={step.get('step_id') or '-'} target={step.get('target_agent') or '-'}"
        loop = str(run.get("loop_name") or run.get("loop_id") or "").strip()
        loop_bits = f" loop={loop}" if loop else ""
        typer.echo(f"- {run.get('id')} status={run.get('status')}{loop_bits}{step_bits}")
    _print_web_url(result, path_key="active_run_path", url_key="active_run_url")
    if result.get("next_active_run_command"):
        typer.echo(f"next_active_run_command: {result.get('next_active_run_command')}")
    if result.get("stop_active_run_command"):
        typer.echo(f"stop_active_run_command: {result.get('stop_active_run_command')}")
    typer.echo("next: continue the active run, submit its current result, or stop it before rerunning /loopora-run for this preview.")


def _agent_gen_error_summary(result: dict) -> str:
    session = result.get("session") if isinstance(result.get("session"), dict) else {}
    validation = session.get("validation") if isinstance(session.get("validation"), dict) else {}
    return str(session.get("error_message") or validation.get("error") or "").strip()
