from __future__ import annotations

import typer

from loopora.agent_native_surface import agent_native_run_surface_for_result, native_surface_plain_lines
from loopora.cli_agent_plan_recovery_results import (
    _agent_entry_return_run_command,
    _agent_entry_return_slash_command,
    _agent_entry_review,
    _agent_gen_error_summary,
    _agent_repair_cli_command,
    _agent_task_message_from_session,
    _agent_web_review_focus,
    _agent_web_review_language,
    _agent_web_review_status,
    _agent_web_review_task_anchor_fields,
    _attach_agent_gen_recovery_fields,
    _attach_agent_ready_run_handoff_fields,
    _attach_agent_web_review_recovery_fields,
    _recommended_review_option,
)
from loopora.cli_agent_plan_results import (
    _agent_gen_json_payload,
    _agent_plan_summary,
)
from loopora.cli_agent_runtime_support import print_web_status as _print_web_status
from loopora.cli_shared import echo_json
from loopora.cli_summary_helpers import (
    clip as _clip,
    non_bool_int as _non_bool_int,
)

import shlex


from loopora.cli_agent_plan_recovery_results import (
    REPAIR_CLI_COMMAND_POLICY,
    REPAIR_FORBIDDEN_ACTIONS,
    REPAIR_NEXT_ACTION,
    REPAIR_NEXT_REPAIR_STEP,
    REPAIR_REFERENCE,
    _agent_after_review_ready_message,
    _agent_plan_repair_action,
    _agent_review_message_cli_command,
    _agent_web_review_next_step,
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

__all__ = [
    "_agent_entry_return_run_command",
    "_agent_entry_return_slash_command",
    "_agent_entry_review",
    "_agent_gen_error_summary",
    "_agent_gen_json_payload",
    "_agent_plan_summary",
    "_agent_repair_cli_command",
    "_agent_task_message_from_session",
    "_agent_web_review_focus",
    "_agent_web_review_language",
    "_agent_web_review_status",
    "_agent_web_review_task_anchor_fields",
    "_attach_agent_gen_recovery_fields",
    "_attach_agent_ready_run_handoff_fields",
    "_attach_agent_web_review_recovery_fields",
    "_print_agent_gen_result",
    "_print_agent_repair_guidance",
    "_print_agent_web_review_guidance",
    "_recommended_review_option",
]


def _print_agent_gen_result(result: dict, *, json_output: bool, compact_json_output: bool = False) -> None:
    _attach_agent_ready_run_handoff_fields(result)
    if json_output or compact_json_output:
        _attach_agent_gen_recovery_fields(result)
        echo_json(_agent_gen_json_payload(result, include_raw=not compact_json_output))
        return
    if result.get("ready"):
        typer.echo("Loopora Loop preview is ready")
        typer.echo("next_agent_step: review the preview URL, then run /loopora-run in this same Agent session")
        _print_agent_ready_review_projection(result.get("ready_review_projection"))
        _print_agent_ready_run_handoff(result)
    elif result.get("requires_candidate_repair"):
        typer.echo("Loopora Loop preview needs plan file repair before /loopora-run")
        if result.get("loopora_fit_contradiction"):
            typer.echo(
                "not_fit: task summary says this looks like one-off, direct-answer, no-new-evidence, "
                "or benchmark/test-harness-only work; "
                "reframe the task with later evidence, handoff, or GateKeeper value before trying a runnable Loop"
            )
        error = _agent_gen_error_summary(result)
        if error:
            typer.echo(f"validation_error: {error}")
        _print_agent_repair_guidance(result)
    elif str(result.get("status") or "").strip() == "skipped":
        _print_agent_skipped_result(result)
        return
    elif result.get("continued_alignment_session") and result.get("requires_web_alignment"):
        typer.echo("Loopora planning conversation is waiting for user input")
        _print_agent_alignment_dialogue_guidance(result)
    elif result.get("requires_web_alignment"):
        _print_agent_web_alignment_header(result)
        _print_agent_web_review_guidance(result)
    else:
        typer.echo(f"Loopora Loop preview status: {result.get('status')}")
    _print_agent_native_run_surface(result)
    typer.echo(f"session_id: {result['session']['id']}")
    typer.echo(f"preview_url: {result.get('preview_url') or result.get('preview_path')}")
    _print_web_status(result)


def _print_agent_skipped_result(result: dict) -> None:
    typer.echo("Loopora plan generation skipped")
    latest = _latest_alignment_assistant_turn(result.get("session") if isinstance(result.get("session"), dict) else {})
    message = str(latest.get("content") or "").strip()
    if message:
        typer.echo(f"alignment_assistant_message: {_clip(message, 1000)}")
    typer.echo(f"session_id: {result['session']['id']}")


def _print_agent_web_alignment_header(result: dict) -> None:
    language = _agent_web_review_language(result)
    if result.get("loopora_fit_contradiction"):
        if language == "es":
            typer.echo("El encaje con Loopora necesita una decisión del usuario antes de generar un Loop ejecutable")
            typer.echo(
                "not_fit: el resumen de la tarea parece una tarea puntual, una respuesta directa, sin evidencia nueva "
                "o solo cubierta por benchmarks/pruebas; define evidencia posterior, handoff o valor de GateKeeper "
                "antes de generar un Loop ejecutable"
            )
            return
        typer.echo("Loopora fit needs a user decision before generating a runnable Loop")
        typer.echo(
            "not_fit: task summary says this looks like one-off, direct-answer, no-new-evidence, "
            "or benchmark/test-harness-only work; "
            "define later evidence, handoff, or GateKeeper value before generating a runnable Loop"
        )
        return
    if language == "es":
        typer.echo("La vista previa de Loopora necesita Web review antes de /loopora-run")
        return
    typer.echo("Loopora Loop preview needs Web review before /loopora-run")


def _print_agent_alignment_dialogue_guidance(result: dict) -> None:
    session = result.get("session") if isinstance(result.get("session"), dict) else {}
    latest = _latest_alignment_assistant_turn(session)
    session_id = str(session.get("id") or "").strip()
    stage = str(session.get("alignment_stage") or "").strip()
    if session_id:
        typer.echo(f"alignment_session_id: {session_id}")
    if stage:
        typer.echo(f"alignment_stage: {stage}")
    message = str(latest.get("content") or "").strip()
    if message:
        typer.echo(f"alignment_assistant_message: {_clip(message, 1000)}")
    options = latest.get("decision_options") if isinstance(latest.get("decision_options"), list) else []
    if options:
        typer.echo("alignment_decision_options:")
        for option in options:
            if not isinstance(option, dict):
                continue
            label = str(option.get("label") or option.get("id") or "").strip()
            reply = str(option.get("user_reply") or "").strip()
            recommended = " (Recommended)" if option.get("recommended") is True else ""
            if label and reply:
                typer.echo(f"- {label}{recommended}: {_clip(reply, 360)}")
            elif label:
                typer.echo(f"- {label}{recommended}")
    next_step = str(result.get("next_alignment_step") or "").strip()
    if next_step:
        typer.echo(f"next_alignment_step: {_clip(next_step, 500)}")


def _latest_alignment_assistant_turn(session: dict) -> dict:
    transcript = session.get("transcript") if isinstance(session.get("transcript"), list) else []
    for item in reversed(transcript):
        if isinstance(item, dict) and str(item.get("role") or "").strip() == "assistant":
            return item
    return {}


def _print_agent_ready_review_projection(projection: object) -> None:
    review = projection if isinstance(projection, dict) else {}
    if not review:
        return
    typer.echo("ready_review:")
    _print_ready_review_items("loopora_fit", review.get("loopora_fit_reasons"))
    _print_ready_review_items("task_scope", review.get("task_scope"))
    _print_ready_review_items("success_surface", review.get("success_surface"))
    _print_ready_review_items("fake_done_risks", review.get("fake_done_risks"))
    _print_ready_review_items("evidence_preferences", review.get("evidence_preferences"))
    _print_ready_review_items("execution_strategy", review.get("execution_strategy"))
    _print_ready_review_items("judgment_tradeoffs", review.get("judgment_tradeoffs"))
    _print_ready_review_items("residual_risk", review.get("residual_risk_policy"))
    _print_ready_review_items("local_governance", review.get("local_governance"))
    coverage = review.get("coverage") if isinstance(review.get("coverage"), dict) else {}
    if coverage:
        typer.echo(
            "coverage_targets: "
            f"{coverage.get('check_count', 0)} checks / "
            f"{coverage.get('target_count', 0)} targets / "
            f"{coverage.get('required_target_count', 0)} required"
        )
    traceability = review.get("traceability") if isinstance(review.get("traceability"), dict) else {}
    if traceability:
        typer.echo(f"judgment_projection: {traceability.get('mapped_count', 0)}/{traceability.get('required_count', 0)} mapped")
    gatekeeper = review.get("gatekeeper") if isinstance(review.get("gatekeeper"), dict) else {}
    if gatekeeper:
        gatekeeper_text = "evidence_refs_required" if gatekeeper.get("requires_evidence_refs") else "configured"
        typer.echo(f"closure_gate: {'GateKeeper' if gatekeeper.get('enabled') else 'run budget'} ({gatekeeper_text})")
    diagnostic_count = _non_bool_int(review.get("diagnostic_count"))
    if diagnostic_count:
        typer.echo(f"review_warnings: {diagnostic_count}")
    typer.echo("review_before_loop: confirm the preview carries these judgments before running /loopora-run")


def _print_agent_ready_run_handoff(result: dict) -> None:
    _attach_agent_ready_run_handoff_fields(result)
    command = str(result.get("ready_cli_command") or result.get("ready_run_command") or "").strip()
    typer.echo(f"ready_next_step: {result.get('ready_next_step')}")
    typer.echo(f"ready_slash_command: {result.get('ready_slash_command')}")
    if command:
        typer.echo(f"ready_cli_command: {command}")
        typer.echo(f"ready_run_command: {command}")


def _print_ready_review_items(label: str, values: object) -> None:
    items = [str(item).strip() for item in list(values or []) if str(item).strip()] if isinstance(values, list) else []
    if not items:
        return
    typer.echo(f"{label}:")
    for item in items:
        typer.echo(f"- {_clip(item, 220)}")


def _print_agent_native_run_surface(result: dict) -> None:
    for line in native_surface_plain_lines(agent_native_run_surface_for_result(result)):
        typer.echo(line)
