from __future__ import annotations

import shlex

import typer

from loopora.agent_adapters import agent_loop_json_command
from loopora.agent_native_surface import attach_native_run_surface, agent_native_run_surface_for_result, native_surface_plain_lines
from loopora.cli_agent_plan_repair_hints import validation_repair_hints as _validation_repair_hints
from loopora.cli_agent_runtime_support import agent_plan_cli_command as _agent_plan_cli_command
from loopora.cli_agent_runtime_support import print_web_status as _print_web_status
from loopora.cli_shared import echo_json
from loopora.cli_summary_helpers import (
    clip as _clip,
    clip_inline as _clip_inline,
    non_bool_int as _non_bool_int,
    set_summary_list as _set_summary_list,
    set_summary_mapping as _set_summary_mapping,
    set_summary_text as _set_summary_text,
)


def _print_agent_gen_result(result: dict, *, json_output: bool) -> None:
    _attach_agent_ready_run_handoff_fields(result)
    if json_output:
        _attach_agent_gen_recovery_fields(result)
        echo_json(_agent_gen_json_payload(result))
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
    elif result.get("requires_web_alignment"):
        typer.echo("Loopora Loop preview needs Web review before /loopora-run")
        if result.get("loopora_fit_contradiction"):
            typer.echo(
                "not_fit: task summary says this looks like one-off, direct-answer, no-new-evidence, "
                "or benchmark/test-harness-only work; "
                "define later evidence, handoff, or GateKeeper value before generating a runnable Loop"
            )
        _print_agent_web_review_guidance(result)
    else:
        typer.echo(f"Loopora Loop preview status: {result.get('status')}")
    _print_agent_native_run_surface(result)
    typer.echo(f"session_id: {result['session']['id']}")
    typer.echo(f"preview_url: {result.get('preview_url') or result.get('preview_path')}")
    _print_web_status(result)


def _agent_gen_json_payload(result: dict) -> dict:
    payload = {"agent_plan_summary": _agent_plan_summary(result)}
    payload.update(result)
    return payload


def _agent_plan_summary(result: dict) -> dict:
    _attach_agent_ready_run_handoff_fields(result)
    summary: dict[str, object] = {
        "ready": bool(result.get("ready")),
        "status": str(result.get("status") or "").strip(),
        "loop_recovery": str(result.get("loop_recovery") or "").strip(),
        "requires_web_alignment": bool(result.get("requires_web_alignment")),
        "requires_candidate_repair": bool(result.get("requires_candidate_repair")),
        "loopora_fit_contradiction": bool(result.get("loopora_fit_contradiction")),
    }
    attach_native_run_surface(summary, result)
    _set_summary_text(summary, "workdir", result.get("workdir"))
    _set_summary_text(summary, "message", result.get("message"))
    _set_summary_list(summary, "required_inputs", result.get("required_inputs"))
    _set_summary_text(summary, "ask_user", result.get("ask_user"))
    _set_summary_mapping(summary, "question_action", result.get("question_action"))
    _set_summary_text(summary, "example_user_reply", result.get("example_user_reply"))
    _set_summary_text(summary, "task_message_template", result.get("task_message_template"))
    _set_summary_text(summary, "first_task_message_example", result.get("first_task_message_example"))
    _set_summary_text(summary, "debug_cli_example_command", result.get("debug_cli_example_command"))
    _set_summary_text(summary, "next", result.get("next"))
    _set_summary_text(summary, "preview_url", result.get("preview_url") or result.get("preview_path"))
    _set_summary_text(summary, "validation_error", result.get("validation_error") or _agent_gen_error_summary(result))
    _set_summary_list(summary, "repair_focus", result.get("repair_focus"))
    _set_summary_text(summary, "repair_task_message", result.get("repair_task_message"))
    _set_summary_text(summary, "plan_file_to_repair", result.get("plan_file_to_repair"))
    _set_summary_text(summary, "preview_plan_copy", result.get("preview_plan_copy"))
    _set_summary_text(summary, "next_plan_command", result.get("next_plan_command"))
    _set_summary_text(summary, "repair_slash_command", result.get("repair_slash_command"))
    _set_summary_text(summary, "repair_cli_command", result.get("repair_cli_command"))
    _set_summary_text(summary, "next_repair_step", result.get("next_repair_step"))
    _set_summary_text(summary, "next_review_step", result.get("next_review_step"))
    _set_summary_text(summary, "review_status", result.get("review_status"))
    _set_summary_list(summary, "review_focus", result.get("review_focus"))
    _set_summary_text(summary, "task_anchor_status", result.get("task_anchor_status"))
    _set_summary_text(summary, "task_anchor_preview", result.get("task_anchor_preview"))
    _set_summary_text(summary, "review_scope", result.get("review_scope"))
    _set_summary_text(summary, "review_recommended_action", result.get("review_recommended_action"))
    _set_summary_text(summary, "review_reply_preview", result.get("review_reply_preview"))
    _set_summary_text(summary, "after_review_ready", result.get("after_review_ready"))
    _set_summary_text(summary, "after_review_slash_command", result.get("after_review_slash_command"))
    _set_summary_text(summary, "after_review_cli_command", result.get("after_review_cli_command"))
    _set_summary_text(summary, "after_review_command", result.get("after_review_command"))
    if result.get("ready"):
        _set_summary_mapping(summary, "ready_review_projection", result.get("ready_review_projection"))
        _set_summary_text(summary, "review_before_loop", result.get("review_before_loop"))
        _set_summary_text(summary, "ready_next_step", result.get("ready_next_step"))
        _set_summary_text(summary, "ready_slash_command", result.get("ready_slash_command"))
        _set_summary_text(summary, "ready_cli_command", result.get("ready_cli_command"))
        _set_summary_text(summary, "ready_run_command", result.get("ready_run_command"))
    return {key: value for key, value in summary.items() if value not in ("", [], {})}


def _attach_agent_gen_recovery_fields(result: dict) -> None:
    if result.get("ready"):
        return
    if result.get("requires_candidate_repair"):
        result["loop_recovery"] = "repair_candidate_plan_file"
        error = _agent_gen_error_summary(result)
        result["validation_error"] = error
        result["repair_focus"] = _validation_repair_hints(error)
        repair_task_message = _agent_task_message_from_session(result)
        if repair_task_message:
            result["repair_task_message"] = repair_task_message
        session = result.get("session") if isinstance(result.get("session"), dict) else {}
        binding = result.get("binding") if isinstance(result.get("binding"), dict) else {}
        plan_file = str(binding.get("source_path") or session.get("bundle_path") or "").strip()
        result["plan_file_to_repair"] = plan_file
        result["preview_plan_copy"] = str(session.get("bundle_path") or "").strip()
        result["next_plan_command"] = "/loopora-plan"
        if plan_file:
            result["repair_slash_command"] = f"/loopora-plan {shlex.quote(plan_file)}"
        repair_cli_command = _agent_repair_cli_command(result, plan_file=plan_file)
        if repair_cli_command:
            result["repair_cli_command"] = repair_cli_command
        result["next_repair_step"] = (
            "repair the candidate plan file so it preserves repair_task_message and repair_focus in spec, roles, "
            "workflow, and evidence rules; rerun repair_cli_command or repair_slash_command, then use /loopora-run "
            "only after the preview is ready"
        )
        return
    if result.get("requires_web_alignment"):
        _attach_agent_web_review_recovery_fields(result)


def _attach_agent_web_review_recovery_fields(result: dict) -> None:
    result["loop_recovery"] = "finish_web_review"
    result["review_status"] = _agent_web_review_status(result)
    result["review_focus"] = _agent_web_review_focus(result)
    result.update(_agent_web_review_task_anchor_fields(result))
    review = _agent_entry_review(result)
    recommended = _recommended_review_option(review)
    label = str(recommended.get("label") or recommended.get("id") or "").strip()
    if label:
        result["review_recommended_action"] = label
    reply = str(recommended.get("user_reply") or review.get("suggested_reply") or "").strip()
    if reply:
        result["review_reply_preview"] = _clip_inline(reply, 260)
    result["next_review_step"] = "open the preview URL, complete the Web review checklist, then use /loopora-run only after the preview is ready"
    result["after_review_ready"] = "return to this Agent session and run /loopora-run; do not start the Agent-native run from Web"
    result["after_review_slash_command"] = _agent_entry_return_slash_command()
    command = _agent_entry_return_run_command(result)
    if command:
        result["after_review_cli_command"] = command
        result["after_review_command"] = command


def _agent_repair_cli_command(result: dict, *, plan_file: str) -> str:
    binding = result.get("binding") if isinstance(result.get("binding"), dict) else {}
    adapter = str(result.get("adapter") or binding.get("adapter") or binding.get("candidate_adapter") or "").strip()
    workdir = str(result.get("workdir") or binding.get("workdir") or "").strip()
    message = _agent_task_message_from_session(result)
    if not adapter or not workdir or not message:
        return ""
    context_id = str(binding.get("host_context_id") or result.get("host_context_id") or "").strip()
    entry_source = str(
        result.get("candidate_entry_source") or binding.get("candidate_entry_source") or binding.get("entry_source") or ""
    ).strip()
    command = _agent_plan_cli_command(
        adapter=adapter,
        workdir=workdir,
        message=message,
        context_id=context_id,
        entry_source=entry_source,
        bundle_file=plan_file,
    )
    return f"{command} --json"


def _agent_task_message_from_session(result: dict) -> str:
    session = result.get("session") if isinstance(result.get("session"), dict) else {}
    transcript = session.get("transcript") if isinstance(session.get("transcript"), list) else []
    for item in reversed(transcript):
        if not isinstance(item, dict):
            continue
        if str(item.get("role") or "").strip() != "user":
            continue
        content = str(item.get("content") or "").strip()
        if content:
            return content
    return ""


def _print_agent_ready_review_projection(projection: object) -> None:
    review = projection if isinstance(projection, dict) else {}
    if not review:
        return
    typer.echo("ready_review:")
    _print_ready_review_items("loopora_fit", review.get("loopora_fit_reasons"))
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


def _attach_agent_ready_run_handoff_fields(result: dict) -> None:
    if not result.get("ready"):
        return
    result["review_before_loop"] = "confirm the preview carries these judgments before running /loopora-run"
    result["ready_next_step"] = "return to this Agent session and run /loopora-run; do not start the Agent-native run from Web"
    result["ready_slash_command"] = _agent_entry_return_slash_command()
    command = _agent_entry_return_run_command(result)
    if command:
        result["ready_cli_command"] = command
        result["ready_run_command"] = command


def _print_ready_review_items(label: str, values: object) -> None:
    items = [str(item).strip() for item in list(values or []) if str(item).strip()] if isinstance(values, list) else []
    if not items:
        return
    typer.echo(f"{label}:")
    for item in items:
        typer.echo(f"- {_clip(item, 220)}")


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
    typer.echo("after_review_ready: return to this Agent session and run /loopora-run; do not start the Agent-native run from Web")
    typer.echo(f"after_review_slash_command: {_agent_entry_return_slash_command()}")
    if command:
        typer.echo(f"after_review_cli_command: {command}")
        typer.echo(f"after_review_command: {command}")


def _agent_web_review_task_anchor_fields(result: dict) -> dict[str, str]:
    message = _agent_task_message_from_session(result)
    if not message:
        return {}
    if result.get("loopora_fit_contradiction"):
        status = (
            "task anchor preserved from /loopora-plan; Loopora fit must be redefined before it can become a runnable Loop"
        )
    else:
        status = (
            "task anchor preserved from /loopora-plan; no candidate plan has projected it into a runnable Loop yet"
        )
    return {
        "task_anchor_status": status,
        "task_anchor_preview": _clip_inline(message, 260),
        "review_scope": "review_focus lists Loop surfaces to compile from the task anchor, not missing chat input",
    }


def _agent_web_review_status(result: dict) -> str:
    if result.get("loopora_fit_contradiction"):
        return "not runnable; Loopora fit needs to be redefined"
    return "not runnable; no candidate plan file was submitted"


def _agent_entry_return_slash_command() -> str:
    return "/loopora-run"


def _agent_entry_return_run_command(result: dict) -> str:
    binding = result.get("binding") if isinstance(result.get("binding"), dict) else {}
    adapter = str(result.get("adapter") or binding.get("adapter") or binding.get("candidate_adapter") or "").strip()
    workdir = str(result.get("workdir") or binding.get("workdir") or "").strip()
    context_id = str(binding.get("host_context_id") or "").strip()
    entry_source = str(binding.get("candidate_entry_source") or binding.get("entry_source") or "").strip()
    if adapter and workdir:
        return agent_loop_json_command(adapter, workdir, entry_source=entry_source, context_id=context_id)
    return str(_agent_entry_launch(result).get("loop_command") or "").strip()


def _agent_entry_review(result: dict) -> dict:
    session = result.get("session") if isinstance(result.get("session"), dict) else {}
    return session.get("agent_entry_review") if isinstance(session.get("agent_entry_review"), dict) else {}


def _agent_entry_launch(result: dict) -> dict:
    session = result.get("session") if isinstance(result.get("session"), dict) else {}
    return session.get("agent_entry_launch") if isinstance(session.get("agent_entry_launch"), dict) else {}


def _recommended_review_option(review: dict) -> dict:
    options = [item for item in list(review.get("decision_options") or []) if isinstance(item, dict)]
    recommended = next((item for item in options if item.get("recommended") is True), None)
    return recommended or (options[0] if options else {})


def _agent_web_review_focus(result: dict) -> list[str]:
    focus = [
        "Loopora fit: explain what future rounds add beyond one Agent pass",
        "Success surface: name the user-visible outcome that must be proven",
        "Fake-done risks: name shallow states that must block closure",
        "Evidence expectations: name the checks, logs, browser paths, audits, or artifacts to trust",
        "Execution strategy and tradeoffs: say what to prove, repair, narrow, expand, or defer first",
        "Residual risk and local governance: name what may remain, who owns it, and which project rules must be read or gated",
    ]
    if result.get("loopora_fit_contradiction"):
        focus[0] = "Loopora fit: define later evidence, handoffs, or GateKeeper value before creating a runnable Loop"
    return focus


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


def _print_agent_native_run_surface(result: dict) -> None:
    for line in native_surface_plain_lines(agent_native_run_surface_for_result(result)):
        typer.echo(line)


def _agent_gen_error_summary(result: dict) -> str:
    session = result.get("session") if isinstance(result.get("session"), dict) else {}
    validation = session.get("validation") if isinstance(session.get("validation"), dict) else {}
    return str(session.get("error_message") or validation.get("error") or "").strip()
