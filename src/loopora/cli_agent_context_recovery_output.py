from __future__ import annotations

import typer

from loopora.agent_native_surface import attach_native_run_surface
from loopora.agent_native_v3 import agent_v3_envelope
from loopora.agent_native_v3 import agent_v3_legacy_raw
from loopora.agent_native_v3 import agent_v3_technical_handoff
from loopora.cli_agent_plan_repair_hints import validation_repair_hints as _validation_repair_hints
from loopora.cli_summary_helpers import (
    clip_inline as _clip_inline,
    non_bool_int as _non_bool_int,
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
        _set_summary_text(summary, "task_message_template", result.get("task_message_template"))
        _set_summary_text(summary, "first_task_message_example", result.get("first_task_message_example"))
        _set_summary_text(summary, "debug_cli_example_command", result.get("debug_cli_example_command"))
        _set_summary_text(summary, "next", result.get("next"))
        _set_summary_text(summary, "check_command", result.get("check_command"))
        _set_summary_text(summary, "context_card_error", result.get("context_card_error") or result.get("binding_error"))
        _set_summary_text(summary, "preview_url", result.get("preview_url") or result.get("preview_path"))
        _set_summary_text(summary, "validation_error", result.get("validation_error") or _agent_gen_error_summary(result))
        _set_summary_list(summary, "repair_focus", result.get("repair_focus"))
        _set_summary_text(summary, "repair_task_message", result.get("repair_task_message"))
        _set_summary_text(summary, "plan_file_to_repair", result.get("plan_file_to_repair"))
        _set_summary_text(summary, "preview_plan_copy", result.get("preview_plan_copy"))
        _set_summary_text(summary, "next_review_step", result.get("next_review_step"))
        _set_summary_text(summary, "review_status", result.get("review_status"))
        _set_summary_text(summary, "task_anchor_status", result.get("task_anchor_status"))
        _set_summary_text(summary, "task_anchor_preview", result.get("task_anchor_preview"))
        _set_summary_text(summary, "review_scope", result.get("review_scope"))
        _set_summary_text(summary, "next_repair_step", result.get("next_repair_step"))
        _set_summary_text(summary, "after_review_slash_command", result.get("after_review_slash_command"))
        _set_summary_text(summary, "after_review_cli_command", result.get("after_review_cli_command"))
    return {key: value for key, value in summary.items() if value not in ("", [], {})}


def _visible_loop_recovery(loop_recovery: str) -> str:
    if loop_recovery == "repair_agent_binding":
        return "repair_context_card"
    return loop_recovery


def _attach_recoverable_context_summary(summary: dict[str, object], result: dict) -> None:
    resolution = result.get("context_resolution") if isinstance(result.get("context_resolution"), dict) else {}
    choices = [choice for choice in resolution.get("choices") or [] if isinstance(choice, dict)]
    _set_summary_text(summary, "confidence", resolution.get("confidence"))
    _set_summary_text(summary, "message", result.get("message"))
    _set_summary_text(summary, "next_active_run_command", result.get("next_active_run_command"))
    summary["choice_count"] = _non_bool_int(resolution.get("choice_count")) or len(choices)
    summary["runnable_choice_count"] = _non_bool_int(resolution.get("runnable_choice_count")) or sum(
        1 for choice in choices if choice.get("runnable") is not False
    )
    summary["non_runnable_choice_count"] = _non_bool_int(resolution.get("non_runnable_choice_count")) or max(
        0, len(choices) - int(summary["runnable_choice_count"])
    )
    selection_hint = str(resolution.get("selection_hint") or "").strip() or _recoverable_context_selection_hint(choices)
    _set_summary_text(summary, "selection_hint", selection_hint)
    _set_summary_text(summary, "next", _recoverable_context_next_instruction(choices))
    displayed = _display_recoverable_context_choices(choices, limit=5)
    _set_summary_choices(summary, displayed)
    omitted = max(0, len(choices) - len(displayed))
    if omitted:
        summary["omitted_choice_count"] = omitted


def _set_summary_choices(summary: dict[str, object], choices: list[dict]) -> None:
    compact = [_recoverable_context_choice_summary(choice) for choice in choices]
    compact = [choice for choice in compact if choice]
    if compact:
        summary["choices"] = compact


def _recoverable_context_choice_summary(choice: dict) -> dict:
    option_id = str(choice.get("option_id") or "").strip()
    runnable = choice.get("runnable") is not False
    fallback_slash = f"/loopora-run option:{option_id}" if runnable and option_id else ""
    summary: dict[str, object] = {
        "option_id": option_id,
        "action": str(choice.get("action") or "").strip(),
        "label": str(choice.get("label_en") or choice.get("label_zh") or choice.get("alignment_session_id") or "").strip(),
        "choice_status": str(choice.get("choice_status") or "").strip(),
        "choice_hint": str(choice.get("choice_hint_en") or choice.get("choice_hint_zh") or "").strip(),
        "runnable": runnable,
    }
    _set_summary_text(summary, "alignment_status", choice.get("alignment_status"))
    _set_summary_text(summary, "linked_run_id", choice.get("linked_run_id"))
    _set_summary_text(summary, "linked_run_status", choice.get("linked_run_status"))
    _set_summary_text(summary, "task_verdict_status", choice.get("task_verdict_status"))
    _set_summary_text(summary, "task_verdict_summary", _clip_inline(str(choice.get("task_verdict_summary") or ""), 220))
    _set_summary_text(summary, "updated_at", choice.get("updated_at"))
    _set_summary_text(summary, "preview_url", choice.get("preview_url"))
    _set_summary_text(summary, "preview_path", choice.get("preview_path"))
    if runnable:
        _set_summary_text(summary, "next_loop_command", choice.get("next_slash_command") or choice.get("next_command") or fallback_slash)
        _set_summary_text(summary, "next_cli_command", choice.get("next_cli_command") or choice.get("agent_cli_command"))
        _set_summary_text(summary, "next_agent_command", choice.get("next_agent_command"))
    else:
        _set_summary_text(summary, "next_plan_command", choice.get("next_plan_command"))
        _set_summary_text(summary, "next_review_step", choice.get("next_review_step"))
        validation_error = str(choice.get("validation_error") or "").strip()
        _set_summary_text(summary, "validation_error", _clip_inline(validation_error, 220))
        _set_summary_list(summary, "repair_focus", _validation_repair_hints(validation_error)[:3])
        _set_summary_text(summary, "plan_file_to_repair", choice.get("plan_file_to_repair"))
        _set_summary_text(summary, "preview_plan_copy", choice.get("preview_plan_copy"))
        _set_summary_text(summary, "next_repair_step", choice.get("next_repair_step"))
    return {key: value for key, value in summary.items() if value not in ("", [], {})}


def _attach_active_run_conflict_summary(summary: dict[str, object], result: dict) -> None:
    active_runs = [run for run in result.get("active_runs") or [] if isinstance(run, dict)]
    summary["active_run_count"] = len(active_runs)
    compact_runs = [_active_run_conflict_run_summary(run) for run in active_runs[:5]]
    compact_runs = [run for run in compact_runs if run]
    if compact_runs:
        summary["active_runs"] = compact_runs
    _set_summary_text(summary, "message", result.get("message"))
    _set_summary_text(summary, "active_run_url", result.get("active_run_url") or result.get("active_run_path"))
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


def _print_recoverable_context_choices(resolution: dict) -> None:
    confidence = str(resolution.get("confidence") or "").strip()
    if confidence:
        typer.echo(f"context_confidence: {confidence}")
    choices = [choice for choice in resolution.get("choices") or [] if isinstance(choice, dict)]
    runnable_count = sum(1 for choice in choices if choice.get("runnable") is not False)
    non_runnable_count = max(0, len(choices) - runnable_count)
    typer.echo(f"context_choices: {len(choices)} total / {runnable_count} runnable / {non_runnable_count} non-runnable")
    typer.echo("recoverable_contexts:")
    displayed_choices = _display_recoverable_context_choices(choices, limit=5)
    for choice in displayed_choices:
        _print_recoverable_context_choice(choice)
    displayed_choice_ids = {id(choice) for choice in displayed_choices}
    omitted_choices = [choice for choice in choices if id(choice) not in displayed_choice_ids]
    if omitted_choices:
        omitted_runnable = sum(1 for choice in omitted_choices if choice.get("runnable") is not False)
        omitted_non_runnable = max(0, len(omitted_choices) - omitted_runnable)
        typer.echo(
            f"recoverable_contexts_omitted: {len(omitted_choices)} "
            f"({omitted_runnable} runnable / {omitted_non_runnable} non-runnable)"
        )
    selection_hint = str(resolution.get("selection_hint") or "").strip() or _recoverable_context_selection_hint(choices)
    if selection_hint:
        typer.echo(f"selection_hint: {selection_hint}")
    typer.echo(f"next: {_recoverable_context_next_instruction(choices)}")


def _display_recoverable_context_choices(choices: list[dict], *, limit: int) -> list[dict]:
    if len(choices) <= limit:
        return choices
    runnable = [choice for choice in choices if choice.get("runnable") is not False]
    if not runnable:
        return choices[:limit]
    displayed = runnable[:limit]
    if len(displayed) < limit:
        displayed_choice_ids = {id(choice) for choice in displayed}
        displayed.extend(
            choice for choice in choices if choice.get("runnable") is False and id(choice) not in displayed_choice_ids
        )
    return displayed[:limit]


def _recoverable_context_selection_hint(choices: list[dict]) -> str:
    runnable_count = sum(1 for choice in choices if choice.get("runnable") is not False)
    non_runnable_count = max(0, len(choices) - runnable_count)
    if runnable_count == 0 and choices:
        return "no runnable contexts are available; return to /loopora-plan or Web review for the listed previews."
    if runnable_count == 1 and non_runnable_count:
        return "one runnable context is available; non-runnable contexts need plan repair or Web review before they can run."
    if runnable_count == 1:
        return "one runnable context is available; select its option_id to continue."
    if runnable_count > 1:
        return (
            f"{runnable_count} runnable contexts are available; choose the exact option_id for the active, READY, "
            "or terminal context you mean; non-runnable contexts need plan repair or Web review."
        )
    return ""


def _recoverable_context_next_instruction(choices: list[dict]) -> str:
    runnable_count = sum(1 for choice in choices if choice.get("runnable") is not False)
    if runnable_count == 0 and choices:
        return "no runnable choice is available; return to /loopora-plan or Web review for the listed previews before running /loopora-run."
    if any(str(choice.get("next_agent_command") or "").strip() for choice in choices if choice.get("runnable") is not False):
        return (
            "for an already active run, run its next_agent_command to claim the current step; "
            "for a READY preview, paste next_loop_command back to the Agent or run next_cli_command directly."
        )
    return (
        "for a runnable choice, paste one next_loop_command back to the Agent or run one next_cli_command directly; "
        "for a non-runnable choice, return to /loopora-plan or Web review."
    )


def _print_recoverable_context_choice(choice: dict) -> None:
    option_id = str(choice.get("option_id") or "").strip()
    label = str(choice.get("label_en") or choice.get("label_zh") or choice.get("alignment_session_id") or "").strip()
    action = str(choice.get("action") or "").strip()
    runnable = choice.get("runnable") is not False
    fallback_slash = f"/loopora-run option:{option_id}" if runnable and option_id else ""
    next_slash_command = str(choice.get("next_slash_command") or choice.get("next_command") or fallback_slash).strip()
    next_cli_command = str(choice.get("next_cli_command") or choice.get("agent_cli_command") or "").strip()
    next_plan_command = str(choice.get("next_plan_command") or "").strip()
    typer.echo(f"- {action}: {label}")
    _echo_context_choice_field("choice_status", str(choice.get("choice_status") or "").strip())
    _echo_context_choice_field("choice_hint", str(choice.get("choice_hint_en") or choice.get("choice_hint_zh") or "").strip())
    typer.echo(f"  runnable: {str(runnable).lower()}")
    _echo_context_choice_field("alignment_status", str(choice.get("alignment_status") or "").strip())
    _echo_context_choice_field("linked_run_status", str(choice.get("linked_run_status") or "").strip())
    _echo_context_choice_field("task_verdict", str(choice.get("task_verdict_status") or "").strip())
    task_verdict_summary = str(choice.get("task_verdict_summary") or "").strip()
    if task_verdict_summary:
        _echo_context_choice_field("task_verdict_summary", _clip_inline(task_verdict_summary, 220))
    _echo_context_choice_field("updated_at", str(choice.get("updated_at") or "").strip())
    _echo_context_choice_field("preview_url", str(choice.get("preview_url") or "").strip())
    _echo_context_choice_field("preview_path", str(choice.get("preview_path") or "").strip())
    _echo_context_choice_field("option_id", option_id)
    _echo_context_choice_field("session_id", str(choice.get("alignment_session_id") or "").strip())
    _echo_context_choice_field("run_id", str(choice.get("linked_run_id") or "").strip())
    if runnable:
        _echo_context_choice_field("next_loop_command", next_slash_command)
        _echo_context_choice_field("next_cli_command", next_cli_command)
        _echo_context_choice_field("next_agent_command", str(choice.get("next_agent_command") or "").strip())
    else:
        _echo_context_choice_field("next_plan_command", next_plan_command)
        _echo_context_choice_field("next_review_step", str(choice.get("next_review_step") or "").strip())
        validation_error = str(choice.get("validation_error") or "").strip()
        _echo_context_choice_field("validation_error", _clip_inline(validation_error, 220))
        repair_focus = _validation_repair_hints(validation_error)
        if repair_focus:
            typer.echo("  repair_focus:")
            for item in repair_focus[:3]:
                typer.echo(f"  - {_clip_inline(item, 220)}")
        _echo_context_choice_field("plan_file_to_repair", str(choice.get("plan_file_to_repair") or "").strip())
        _echo_context_choice_field("preview_plan_copy", str(choice.get("preview_plan_copy") or "").strip())
        _echo_context_choice_field("next_repair_step", str(choice.get("next_repair_step") or "").strip())


def _echo_context_choice_field(label: str, value: str) -> None:
    if value:
        typer.echo(f"  {label}: {value}")


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
    if result.get("active_run_url") or result.get("active_run_path"):
        typer.echo(f"active_run_url: {result.get('active_run_url') or result.get('active_run_path')}")
    if result.get("next_active_run_command"):
        typer.echo(f"next_active_run_command: {result.get('next_active_run_command')}")
    if result.get("stop_active_run_command"):
        typer.echo(f"stop_active_run_command: {result.get('stop_active_run_command')}")
    typer.echo("next: continue the active run, submit its current result, or stop it before rerunning /loopora-run for this preview.")


def _agent_gen_error_summary(result: dict) -> str:
    session = result.get("session") if isinstance(result.get("session"), dict) else {}
    validation = session.get("validation") if isinstance(session.get("validation"), dict) else {}
    return str(session.get("error_message") or validation.get("error") or "").strip()
