from __future__ import annotations

import typer

from loopora.cli_agent_plan_repair_hints import validation_repair_hints as _validation_repair_hints
from loopora.cli_summary_helpers import (
    clip_inline as _clip_inline,
    non_bool_int as _non_bool_int,
    set_summary_list as _set_summary_list,
    set_summary_text as _set_summary_text,
)


def attach_recoverable_context_summary(summary: dict[str, object], result: dict) -> None:
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
    selection_hint = str(resolution.get("selection_hint") or "").strip() or recoverable_context_selection_hint(choices)
    _set_summary_text(summary, "selection_hint", selection_hint)
    _set_summary_text(summary, "next", recoverable_context_next_instruction(choices))
    displayed = display_recoverable_context_choices(choices, limit=5)
    _set_summary_choices(summary, displayed)
    omitted = max(0, len(choices) - len(displayed))
    if omitted:
        summary["omitted_choice_count"] = omitted


def recoverable_context_choice_summary(choice: dict) -> dict:
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
    if choice.get("linked_run_lifecycle_failure") is True:
        summary["linked_run_lifecycle_failure"] = True
    _set_summary_text(summary, "recording_blocked_reason", choice.get("recording_blocked_reason"))
    _set_summary_text(summary, "task_verdict_status", choice.get("task_verdict_status"))
    _set_summary_text(summary, "task_verdict_summary", _clip_inline(str(choice.get("task_verdict_summary") or ""), 220))
    _set_summary_text(summary, "updated_at", choice.get("updated_at"))
    _set_summary_text(summary, "preview_url", choice.get("preview_url"))
    _set_summary_text(summary, "preview_url_status", choice.get("preview_url_status"))
    _set_summary_text(summary, "preview_url_web_start_command", choice.get("preview_url_web_start_command"))
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


def print_recoverable_context_choices(resolution: dict) -> None:
    confidence = str(resolution.get("confidence") or "").strip()
    if confidence:
        typer.echo(f"context_confidence: {confidence}")
    choices = [choice for choice in resolution.get("choices") or [] if isinstance(choice, dict)]
    runnable_count = sum(1 for choice in choices if choice.get("runnable") is not False)
    non_runnable_count = max(0, len(choices) - runnable_count)
    typer.echo(f"context_choices: {len(choices)} total / {runnable_count} runnable / {non_runnable_count} non-runnable")
    typer.echo("recoverable_contexts:")
    displayed_choices = display_recoverable_context_choices(choices, limit=5)
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
    selection_hint = str(resolution.get("selection_hint") or "").strip() or recoverable_context_selection_hint(choices)
    if selection_hint:
        typer.echo(f"selection_hint: {selection_hint}")
    typer.echo(f"next: {recoverable_context_next_instruction(choices)}")


def display_recoverable_context_choices(choices: list[dict], *, limit: int) -> list[dict]:
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


def recoverable_context_selection_hint(choices: list[dict]) -> str:
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


def recoverable_context_next_instruction(choices: list[dict]) -> str:
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


def _set_summary_choices(summary: dict[str, object], choices: list[dict]) -> None:
    compact = [recoverable_context_choice_summary(choice) for choice in choices]
    compact = [choice for choice in compact if choice]
    if compact:
        summary["choices"] = compact


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
    if choice.get("linked_run_lifecycle_failure") is True:
        _echo_context_choice_field("linked_run_lifecycle_failure", "true")
    _echo_context_choice_field("recording_blocked_reason", str(choice.get("recording_blocked_reason") or "").strip())
    _echo_context_choice_field("task_verdict", str(choice.get("task_verdict_status") or "").strip())
    task_verdict_summary = str(choice.get("task_verdict_summary") or "").strip()
    if task_verdict_summary:
        _echo_context_choice_field("task_verdict_summary", _clip_inline(task_verdict_summary, 220))
    _echo_context_choice_field("updated_at", str(choice.get("updated_at") or "").strip())
    _echo_context_choice_field("preview_url", str(choice.get("preview_url") or "").strip())
    _echo_context_choice_field("preview_url_status", str(choice.get("preview_url_status") or "").strip())
    _echo_context_choice_field(
        "preview_url_web_start_command", str(choice.get("preview_url_web_start_command") or "").strip()
    )
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
