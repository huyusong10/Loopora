from __future__ import annotations

import shlex

import typer

from loopora.cli_agent_plan_recovery_results import (
    REPAIR_CLI_COMMAND_POLICY,
    REPAIR_FORBIDDEN_ACTIONS,
    REPAIR_NEXT_ACTION,
    REPAIR_NEXT_REPAIR_STEP,
    REPAIR_REFERENCE,
    _agent_after_review_ready_message,
    _agent_entry_return_run_command,
    _agent_entry_return_slash_command,
    _agent_entry_review,
    _agent_gen_error_summary,
    _agent_plan_repair_action,
    _agent_repair_cli_command,
    _agent_review_message_cli_command,
    _agent_task_message_from_session,
    _agent_web_review_focus,
    _agent_web_review_next_step,
    _agent_web_review_status,
    _agent_web_review_task_anchor_fields,
    _recommended_review_option,
)
from loopora.cli_agent_plan_repair_hints import validation_repair_hints as _validation_repair_hints
from loopora.cli_summary_helpers import clip_inline as _clip_inline


def _print_agent_web_review_guidance(result: dict) -> None:
    typer.echo(f"review_status: {_agent_web_review_status(result)}")
    _print_agent_web_review_task_anchor(result)
    _print_agent_web_review_recommended_action(result)
    typer.echo("review_focus:")
    for item in _agent_web_review_focus(result):
        typer.echo(f"- {item}")
    if result.get("loopora_fit_contradiction"):
        typer.echo(f"next_review_step: {_agent_web_review_next_step(result, not_fit=True)}")
        return
    typer.echo(f"next_review_step: {_agent_web_review_next_step(result, not_fit=False)}")
    _print_agent_web_review_return_command(result)


def _print_agent_web_review_recommended_action(result: dict) -> None:
    review = _agent_entry_review(result)
    recommended = _recommended_review_option(review)
    if not recommended:
        return
    label = str(recommended.get("label") or recommended.get("id") or "").strip()
    if label:
        typer.echo(f"review_recommended_action: {label}")
    reply = str(recommended.get("user_reply") or review.get("suggested_reply") or "").strip()
    if reply:
        typer.echo(f"review_reply_preview: {_clip_inline(reply, 260)}")
    message_cli_command = str(result.get("message_cli_command") or result.get("next_plan_cli_command") or "").strip()
    if not message_cli_command and reply:
        message_cli_command = _agent_review_message_cli_command(result, reply=reply)
    if message_cli_command:
        typer.echo(f"next_plan_cli_command: {message_cli_command}")


def _print_agent_web_review_task_anchor(result: dict) -> None:
    fields = _agent_web_review_task_anchor_fields(result)
    for key in ("task_anchor_status", "task_anchor_preview", "review_scope"):
        text = fields.get(key, "")
        if text:
            typer.echo(f"{key}: {text}")


def _print_agent_web_review_return_command(result: dict) -> None:
    command = _agent_entry_return_run_command(result)
    typer.echo(f"after_review_ready: {_agent_after_review_ready_message(result)}")
    typer.echo("run_blocked_until_web_review: yes")
    typer.echo("after_review_cli_command_status: blocked_until_web_review_complete")
    typer.echo(f"after_review_slash_command: {_agent_entry_return_slash_command()}")
    if command:
        typer.echo(f"after_web_review_cli_command: {command}")
        typer.echo(f"after_review_cli_command: {command}")
        typer.echo(f"after_review_command: {command}")


def _print_agent_repair_guidance(result: dict) -> None:
    session = result.get("session") if isinstance(result.get("session"), dict) else {}
    binding = result.get("binding") if isinstance(result.get("binding"), dict) else {}
    source_path = str(binding.get("source_path") or session.get("bundle_path") or "").strip()
    session_bundle_path = str(session.get("bundle_path") or "").strip()
    error = _agent_gen_error_summary(result)
    hints = _validation_repair_hints(error)
    repair_task_message = _agent_task_message_from_session(result)
    if result.get("loopora_fit_contradiction"):
        typer.echo(
            "not_fit: task summary says this looks like one-off, direct-answer, no-new-evidence, "
            "or benchmark/test-harness-only work; reframe the task with later evidence, handoff, "
            "or GateKeeper value before trying a runnable Loop"
        )
    _print_agent_plan_repair_panel(result)
    if source_path:
        typer.echo(f"plan_file_to_repair: {source_path}")
    if session_bundle_path and session_bundle_path != source_path:
        typer.echo(f"preview_plan_copy: {session_bundle_path}")
    if repair_task_message:
        typer.echo(f"repair_task_message: {repair_task_message}")
    if hints:
        typer.echo("repair_focus:")
        for hint in hints:
            typer.echo(f"- {hint}")
    typer.echo("next_plan_command: /loopora-plan")
    if source_path:
        typer.echo(f"repair_slash_command: /loopora-plan {shlex.quote(source_path)}")
    repair_cli_command = _agent_repair_cli_command(result, plan_file=source_path)
    if repair_cli_command:
        typer.echo(f"repair_cli_command: {repair_cli_command}")
        typer.echo(f"repair_cli_command_policy: {REPAIR_CLI_COMMAND_POLICY}")
    typer.echo(f"repair_reference: {REPAIR_REFERENCE}")
    typer.echo(f"next_repair_step: {REPAIR_NEXT_REPAIR_STEP}")


def _print_agent_plan_repair_panel(result: dict) -> None:
    action = _agent_plan_repair_action(result)
    typer.echo("agent_work_panel:")
    typer.echo("state: repair_candidate_plan_file")
    typer.echo("task_proven: false")
    typer.echo("task_outcome: not_ready_repair_candidate_plan_file")
    typer.echo(f"next_action: {_clip_inline(REPAIR_NEXT_ACTION, 260)}")
    typer.echo("evidence_focus: validation_error and repair_focus from the rejected candidate plan")
    typer.echo("todo_items:")
    typer.echo("- edit the candidate plan file")
    typer.echo("- rerun repair_cli_command exactly with compact JSON")
    typer.echo("- start /loopora-run only after preview readiness")
    typer.echo("repair_action:")
    for key in ("file_to_edit", "command_after_edit", "stop_before"):
        value = str(action.get(key) or "").strip()
        if value:
            typer.echo(f"{key}: {_clip_inline(value, 360)}")
    typer.echo("allowed_inputs:")
    for item in list(action.get("allowed_inputs") or []):
        text = str(item).strip()
        if text:
            typer.echo(f"- {_clip_inline(text, 220)}")
    typer.echo("forbidden_actions:")
    for item in REPAIR_FORBIDDEN_ACTIONS:
        typer.echo(f"- {_clip_inline(item, 220)}")
