from __future__ import annotations

import shlex

import typer

from loopora.cli_agent_plan_recovery_results import (
    _agent_entry_return_run_command,
    _agent_entry_return_slash_command,
    _agent_entry_review,
    _agent_gen_error_summary,
    _agent_repair_cli_command,
    _agent_task_message_from_session,
    _agent_web_review_focus,
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
    typer.echo(
        "next_review_step: open the preview URL, complete the Web review checklist, "
        "then use /loopora-run only after the preview is ready"
    )
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


def _print_agent_web_review_task_anchor(result: dict) -> None:
    fields = _agent_web_review_task_anchor_fields(result)
    for key in ("task_anchor_status", "task_anchor_preview", "review_scope"):
        text = fields.get(key, "")
        if text:
            typer.echo(f"{key}: {text}")


def _print_agent_web_review_return_command(result: dict) -> None:
    command = _agent_entry_return_run_command(result)
    typer.echo("after_review_ready: return to this Agent session and run /loopora-run; do not start the Agent Runner run from Web")
    typer.echo(f"after_review_slash_command: {_agent_entry_return_slash_command()}")
    if command:
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
    typer.echo(
        "next_repair_step: repair the candidate plan file so it preserves repair_task_message and repair_focus in "
        "spec, roles, workflow, and evidence rules; rerun repair_cli_command or repair_slash_command, then use "
        "/loopora-run only after the preview is ready"
    )
