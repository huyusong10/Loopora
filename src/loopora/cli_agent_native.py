from __future__ import annotations

import json
import os
import re
import shlex
from pathlib import Path

import typer

from loopora.agent_adapters import (
    adapter_first_task_message_example,
    agent_loop_json_command,
    prefix_loopora_command,
    read_agent_binding,
    resolve_adapter_project_root,
)
from loopora.agent_web import ensure_local_web_service, web_url_for_path
from loopora.cli_shared import call_spawn_background_worker, echo_json
from loopora.service import LooporaError
from loopora.service_types import LooporaConflictError

PASSING_TASK_VERDICT_STATUSES = frozenset({"passed", "passed_with_residual_risk"})


def _attach_web_url(result: dict, *, path_key: str, url_key: str, no_web: bool) -> None:
    path = str(result.get(path_key) or "")
    if not path:
        return
    if no_web:
        result[url_key] = path
        return
    web = ensure_local_web_service()
    result["web"] = web
    result[url_key] = web_url_for_path(path, web=web)


def _attach_recoverable_context_preview_urls(result: dict, *, no_web: bool) -> None:
    resolution = result.get("context_resolution") if isinstance(result.get("context_resolution"), dict) else {}
    choices = [choice for choice in resolution.get("choices") or [] if isinstance(choice, dict)]
    preview_choices = [choice for choice in choices if str(choice.get("preview_path") or "").strip()]
    if not preview_choices:
        return
    web = None if no_web else ensure_local_web_service()
    if web:
        result["web"] = web
    for choice in preview_choices:
        path = str(choice.get("preview_path") or "").strip()
        choice["preview_url"] = path if no_web else web_url_for_path(path, web=web)


def _resolved_entry_source(entry_source: str) -> str:
    return str(entry_source or "").strip() or os.environ.get("LOOPORA_AGENT_ENTRY_SOURCE", "").strip()


def _spawn_agent_loop_worker_if_needed(service, result: dict) -> None:
    if result.get("execution_plane") == "agent_native":
        return
    if not result.get("started_new_run"):
        return
    run = result.get("run")
    if not isinstance(run, dict):
        return
    spawned_run = call_spawn_background_worker(service, run)
    result["run"] = spawned_run


def _print_agent_plan_recovery_guidance(
    exc: Exception,
    *,
    adapter: str,
    workdir: Path,
    context_id: str,
    entry_source: str,
    json_output: bool,
) -> bool:
    if not _agent_plan_error_requires_message(str(exc)):
        return False
    result = _agent_plan_message_required_result(
        adapter=adapter,
        workdir=workdir,
        context_id=context_id,
        entry_source=entry_source,
    )
    if json_output:
        echo_json(result)
    else:
        _print_agent_plan_message_required(result)
    return True


def _agent_plan_error_requires_message(error: str) -> bool:
    return "--message task summary" in error


def _agent_plan_message_required_result(
    *,
    adapter: str,
    workdir: Path,
    context_id: str = "",
    entry_source: str = "",
) -> dict:
    root = resolve_adapter_project_root(workdir)
    context_request = _agent_plan_context_guidance_fields(
        adapter=adapter,
        workdir=root,
        context_id=context_id,
        entry_source=entry_source,
    )
    return {
        "adapter": adapter,
        "workdir": str(root),
        "ready": False,
        "loop_recovery": "plan_message_required",
        "message": "A non-empty task summary is required before /loopora-plan can create or review a Loop preview.",
        **context_request,
        "next_plan_command": "/loopora-plan",
        "next": "Ask the user the ask_user question, then rerun /loopora-plan with the user's task context.",
    }


def _agent_plan_debug_cli_example_command(
    *,
    adapter: str,
    workdir: Path,
    context_id: str = "",
    entry_source: str = "",
) -> str:
    message = _agent_plan_context_request_fields()["example_user_reply"]
    return _agent_plan_cli_command(
        adapter=adapter,
        workdir=workdir,
        message=message,
        context_id=context_id,
        entry_source=entry_source,
    )


def _agent_plan_cli_command(
    *,
    adapter: str,
    workdir: Path | str,
    message: str,
    context_id: str = "",
    entry_source: str = "",
    bundle_file: str = "",
) -> str:
    command_bits = [
        "loopora",
        "agent",
        str(adapter).strip(),
        "plan",
        "--workdir",
        shlex.quote(str(workdir)),
    ]
    normalized_context_id = str(context_id or "").strip()
    if normalized_context_id:
        command_bits.extend(["--context-id", shlex.quote(normalized_context_id)])
    command_bits.extend(["--message", shlex.quote(message)])
    normalized_bundle_file = str(bundle_file or "").strip()
    if normalized_bundle_file:
        command_bits.extend(["--bundle-file", shlex.quote(normalized_bundle_file)])
    normalized_entry_source = str(entry_source or "").strip()
    if normalized_entry_source:
        command_bits.extend(["--entry-source", shlex.quote(normalized_entry_source)])
    command = " ".join(command_bits)
    return prefix_loopora_command(command, entry_source=normalized_entry_source)


def _agent_plan_context_guidance_fields(
    *,
    adapter: str,
    workdir: Path,
    context_id: str = "",
    entry_source: str = "",
) -> dict:
    return {
        **_agent_plan_context_request_fields(),
        "task_message_template": "Goal: ...; Fake-done risks: ...; Required evidence: ...; Judgment tradeoffs: ...",
        "first_task_message_example": adapter_first_task_message_example(),
        "debug_cli_example_command": _agent_plan_debug_cli_example_command(
            adapter=adapter,
            workdir=workdir,
            context_id=context_id,
            entry_source=entry_source,
        ),
    }


def _agent_plan_context_request_fields() -> dict:
    ask_user = (
        "What long-running task should Loopora govern? Please include the goal, fake-done risks, required evidence, "
        "and any judgment tradeoff that should guide later rounds."
    )
    return {
        "required_inputs": [
            "task_goal",
            "fake_done_risks",
            "required_evidence",
            "judgment_tradeoffs",
        ],
        "ask_user": ask_user,
        "question_action": {
            "kind": "ask_user",
            "target": "main_agent_session",
            "prompt": ask_user,
            "native_tool_policy": "Use the host's official user-question or follow-up capability when available; otherwise ask this question in the main chat.",
            "subagent_policy": "Do not ask user questions from a role subagent; collect missing judgment in the parent Agent session.",
        },
        "example_user_reply": (
            "Build the account-deletion audit flow; fake done would be UI-only deletion or missing provider-failure handling; "
            "required evidence is contract tests plus an audit-log artifact; prefer a smaller proven flow over broad unverified polish."
        ),
    }


def _print_agent_plan_message_required(result: dict) -> None:
    typer.echo("loop_recovery: provide task context before /loopora-plan can create a preview")
    typer.echo(f"message: {result.get('message')}")
    typer.echo(f"next_plan_command: {result.get('next_plan_command') or '/loopora-plan'}")
    _print_agent_plan_context_request_fields(result)
    _print_agent_plan_context_guidance_fields(result)
    typer.echo(f"next: {result.get('next')}")


def _print_agent_plan_context_request_fields(result: dict) -> None:
    inputs = [str(item).strip() for item in list(result.get("required_inputs") or []) if str(item).strip()]
    if inputs:
        typer.echo("required_inputs:")
        for item in inputs:
            typer.echo(f"- {item}")
    ask_user = str(result.get("ask_user") or "").strip()
    if ask_user:
        typer.echo(f"ask_user: {ask_user}")
    question_action = result.get("question_action") if isinstance(result.get("question_action"), dict) else {}
    if question_action:
        typer.echo(
            "question_action: "
            + str(question_action.get("native_tool_policy") or "Ask the user in the main Agent session.").strip()
        )
    example = str(result.get("example_user_reply") or "").strip()
    if example:
        typer.echo(f"example_user_reply: {example}")


def _print_agent_plan_context_guidance_fields(result: dict) -> None:
    task_message_template = str(result.get("task_message_template") or "").strip()
    if task_message_template:
        typer.echo(f"task_message_template: {task_message_template}")
    first_task_message_example = str(result.get("first_task_message_example") or "").strip()
    if first_task_message_example:
        typer.echo("first_task_message_example:")
        typer.echo(first_task_message_example)
    debug_cli_example_command = str(result.get("debug_cli_example_command") or "").strip()
    if debug_cli_example_command:
        typer.echo(f"debug_cli_example_command: {debug_cli_example_command}")


def _print_adapter_mutation_result(result: dict, *, action: str, json_output: bool) -> None:
    if json_output:
        echo_json(result)
        return
    label = str(result.get("label") or _adapter_label(str(result.get("adapter") or "")))
    if action == "installed":
        typer.echo(f"{label} Loopora entry is installed")
        typer.echo(f"target project: {result['workdir']}")
        _print_adapter_next_steps(label, result.get("next_steps"))
        _print_adapter_first_task_message_example(result)
        _print_adapter_next_commands(result.get("next_commands"))
    else:
        typer.echo(f"{label} Loopora entry {action}: {result['status']}")
        typer.echo(f"target project: {result['workdir']}")
    _print_adapter_file_details(result)


def _print_adapter_check_result(result: dict, *, json_output: bool) -> None:
    if json_output:
        echo_json(result)
        return
    label = str(result.get("label") or _adapter_label(str(result.get("adapter") or "")))
    check_status = str(result.get("check_status") or "fail")
    typer.echo(f"{label} Loopora entry check: {check_status}")
    typer.echo(f"target project: {result['workdir']}")
    recovery = result.get("check_recovery") if isinstance(result.get("check_recovery"), dict) else {}
    _print_adapter_check_recovery_summary(recovery)
    if recovery.get("state") == "not_installed":
        _print_adapter_check_recovery(result, recovery)
        return
    checks = [item for item in list(result.get("checks") or []) if isinstance(item, dict)]
    if checks:
        typer.echo("checks:")
        for item in checks:
            suffix = f" ({item.get('path')})" if item.get("path") else ""
            message = f": {item.get('message')}" if item.get("message") else ""
            typer.echo(f"- {item.get('status')}: {item.get('name')}{suffix}{message}")
    if check_status == "pass":
        _print_adapter_next_steps(label, result.get("next_steps"))
        _print_adapter_first_task_message_example(result)
        _print_adapter_next_commands(result.get("next_commands"))
    if check_status != "pass":
        _print_adapter_check_recovery(result, recovery)


def _print_adapter_check_recovery_summary(recovery: dict) -> None:
    state = str(recovery.get("state") or "").strip()
    summary = str(recovery.get("summary") or "").strip()
    if state:
        typer.echo(f"install_state: {state}")
    if summary:
        typer.echo(f"summary: {summary}")


def _print_adapter_check_recovery(result: dict, recovery: dict) -> None:
    install_command = str(recovery.get("install_command") or "").strip()
    if not install_command:
        install_command = prefix_loopora_command(f"loopora init {result.get('adapter')} --workdir {shlex.quote(str(result.get('workdir')))}")
    check_command = str(recovery.get("check_command") or "").strip()
    if not check_command:
        check_command = f"{install_command} --check"
    typer.echo("recovery:")
    typer.echo(f"- Run: {install_command}")
    typer.echo(f"- Then verify: {check_command}")
    if recovery.get("state") != "not_installed":
        typer.echo("- If a file is unmanaged, inspect it before replacing or moving it.")


def _handle_adapter_install_conflict(adapter: str, *, workdir: Path, exc: LooporaConflictError, json_output: bool) -> None:
    label = _adapter_label(adapter)
    root = resolve_adapter_project_root(workdir)
    conflicts = _adapter_conflict_paths(str(exc))
    recovery = {
        "state": "install_conflict",
        "summary": "Loopora found existing Agent entry files or host config that it does not own, so it left the project unchanged.",
        "inspect": "Inspect the listed file or config before changing it.",
        "user_owned_action": "If it is yours, move or rename it, or choose another target project directory.",
        "install_command": prefix_loopora_command(f"loopora init {adapter} --workdir {shlex.quote(str(root))}"),
    }
    if json_output:
        echo_json(
            {
                "adapter": adapter,
                "label": label,
                "workdir": str(root),
                "status": "not_installed",
                "install_status": "conflict",
                "loop_recovery": "adapter_install_conflict",
                "message": f"{label} Loopora entry was not installed.",
                "conflicting_files": conflicts,
                "raw_conflict": str(exc),
                "recovery": recovery,
            }
        )
        raise typer.Exit(code=1)
    typer.secho(f"{label} Loopora entry was not installed.", fg=typer.colors.RED, err=True)
    typer.echo(f"target project: {root}", err=True)
    typer.echo(recovery["summary"], err=True)
    if conflicts:
        typer.echo("conflicting files:", err=True)
        for path in conflicts:
            typer.echo(f"- {path}", err=True)
    else:
        typer.echo(f"details: {exc}", err=True)
    typer.echo("recovery:", err=True)
    typer.echo(f"- {recovery['inspect']}", err=True)
    typer.echo(f"- {recovery['user_owned_action']}", err=True)
    typer.echo(f"- Then rerun: {recovery['install_command']}", err=True)
    raise typer.Exit(code=1)


def _adapter_conflict_paths(message: str) -> list[str]:
    marker = "adapter files:"
    if marker not in message:
        return []
    return [part.strip() for part in message.split(marker, 1)[1].split(",") if part.strip()]


def _print_adapter_file_details(result: dict) -> None:
    managed_files = result.get("managed_files")
    if isinstance(managed_files, list):
        typer.echo("managed files:")
        for item in managed_files:
            if isinstance(item, dict):
                typer.echo(f"- {item.get('path')}: {item.get('state', 'managed')}")
    removed_files = result.get("removed_files")
    _print_adapter_plain_list("removed:", removed_files)
    removed_obsolete_files = result.get("removed_obsolete_files")
    _print_adapter_plain_list("removed obsolete managed files:", removed_obsolete_files)
    kept_files = result.get("kept_files")
    if isinstance(kept_files, list) and kept_files:
        typer.echo("kept:")
        for item in kept_files:
            if isinstance(item, dict):
                typer.echo(f"- {item.get('path')}: {item.get('reason')}")


def _print_adapter_plain_list(label: str, items: object) -> None:
    if not isinstance(items, list) or not items:
        return
    typer.echo(label)
    for item in items:
        typer.echo(f"- {item}")


def _print_adapter_next_steps(label: str, steps: object = None) -> None:
    typer.echo("next:")
    if isinstance(steps, list) and steps:
        for step in steps:
            text = str(step or "").strip()
            if text:
                typer.echo(f"- {text}")
        return
    typer.echo(
        f"- Return to {label} in this project with the task goal, fake-done risk, and required evidence."
    )
    typer.echo("- Run /loopora-plan to prepare the Loop preview before starting work.")
    typer.echo("- Review the READY Loop preview, then run /loopora-run in the same Agent session.")
    typer.echo(f"- If /loopora-plan or /loopora-run is not visible in {label}, rerun the diagnostics below and refresh or restart {label}.")
    typer.echo("- Use Web to observe evidence, gaps, and verdicts while execution stays in the Agent.")


def _print_adapter_next_commands(commands: object) -> None:
    if not isinstance(commands, dict):
        return
    check_command = str(commands.get("check") or "").strip()
    agent_check_command = str(commands.get("agent_check") or "").strip()
    if not check_command and not agent_check_command:
        return
    typer.echo("diagnostics:")
    if check_command:
        typer.echo(f"- verify install: {check_command}")
    if agent_check_command:
        typer.echo(f"- agent-runtime check: {agent_check_command}")


def _print_adapter_first_task_message_example(result: dict) -> None:
    example = str(result.get("first_task_message_example") or "").strip()
    if not example:
        return
    typer.echo("first task message example:")
    typer.echo(example)


def _adapter_label(adapter: str) -> str:
    return {
        "codex": "Codex",
        "claude": "Claude Code",
        "opencode": "OpenCode",
    }.get(adapter, adapter or "Agent")


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


def _set_summary_text(summary: dict[str, object], key: str, value: object) -> None:
    text = str(value or "").strip()
    if text:
        summary[key] = text


def _set_summary_list(summary: dict[str, object], key: str, value: object) -> None:
    items = [str(item).strip() for item in list(value or []) if str(item).strip()] if isinstance(value, list) else []
    if items:
        summary[key] = items


def _set_summary_mapping(summary: dict[str, object], key: str, value: object) -> None:
    if isinstance(value, dict) and value:
        summary[key] = value


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


def _print_agent_loop_unready_guidance(
    exc: Exception,
    *,
    service,
    adapter: str,
    workdir: Path,
    context_id: str,
    entry_source: str,
    no_web: bool,
    json_output: bool,
) -> bool:
    result = _agent_loop_unready_recovery_result(
        exc,
        service=service,
        adapter=adapter,
        workdir=workdir,
        context_id=context_id,
        entry_source=entry_source,
        no_web=no_web,
    )
    if not result:
        return False
    if json_output:
        echo_json(_agent_loop_recovery_json_payload(result))
        return True
    _print_agent_loop_recovery_result(result)
    return True


def _print_agent_next_recovery_guidance(
    exc: Exception,
    *,
    service,
    adapter: str,
    workdir: Path,
    context_id: str,
    entry_source: str,
    no_web: bool,
    json_output: bool,
) -> bool:
    result = _agent_next_recovery_result(
        exc,
        service=service,
        adapter=adapter,
        workdir=workdir,
        context_id=context_id,
        entry_source=entry_source,
        no_web=no_web,
    )
    if not result:
        return False
    if json_output:
        echo_json(_agent_next_recovery_json_payload(result))
        return True
    _print_agent_next_recovery_result(result)
    return True


def _agent_next_recovery_result(
    exc: Exception,
    *,
    service,
    adapter: str,
    workdir: Path,
    context_id: str,
    entry_source: str,
    no_web: bool,
) -> dict:
    error = str(exc)
    if service is None or "no Loopora run is associated with this agent session/workdir" not in error:
        return {}
    root = resolve_adapter_project_root(workdir)
    result = _agent_loop_unbound_recovery_result(
        service,
        adapter=adapter,
        root=root,
        context_id=context_id,
        entry_source=entry_source,
        no_web=no_web,
    )
    if not result:
        return {}
    result["recovery_source"] = "agent_next_missing_binding"
    result["error"] = error
    if result.get("loop_recovery") == "choose_recoverable_context":
        result["message"] = (
            "Current Agent context is not bound to a Loopora run, but recoverable contexts exist; "
            "choose the intended run or pass --run-id to claim its current step."
        )
        _attach_agent_next_commands_to_recovery_choices(
            result,
            adapter=adapter,
            workdir=root,
            context_id=context_id,
            entry_source=entry_source,
        )
    elif result.get("loop_recovery") == "plan_first":
        result["message"] = "No Loopora run is bound to this Agent context/workdir; plan and start a Loop before claiming a step."
        result["next"] = "Ask the user for task context, run /loopora-plan, review the READY preview, then run /loopora-run."
    return result


def _attach_agent_next_commands_to_recovery_choices(
    result: dict,
    *,
    adapter: str,
    workdir: Path,
    context_id: str,
    entry_source: str,
) -> None:
    resolution = result.get("context_resolution") if isinstance(result.get("context_resolution"), dict) else {}
    choices = [choice for choice in resolution.get("choices") or [] if isinstance(choice, dict)]
    direct_commands: list[str] = []
    for choice in choices:
        if choice.get("runnable") is False:
            continue
        linked_run_id = str(choice.get("linked_run_id") or "").strip()
        if not linked_run_id:
            continue
        choice_entry_source = str(choice.get("entry_source") or entry_source or "").strip()
        command = _agent_next_command_hint(
            adapter=adapter,
            workdir=workdir,
            context_id=context_id,
            run_id=linked_run_id,
            entry_source=choice_entry_source,
        )
        choice["next_agent_command"] = command
        direct_commands.append(command)
    if len(direct_commands) == 1:
        result["next_active_run_command"] = direct_commands[0]


def _agent_loop_unready_recovery_result(
    exc: Exception,
    *,
    service,
    adapter: str,
    workdir: Path,
    context_id: str,
    entry_source: str,
    no_web: bool,
) -> dict:
    error = str(exc)
    if service is None or not _agent_loop_error_supports_recovery(error):
        return {}
    root = resolve_adapter_project_root(workdir)
    if "another active run is already using" in error:
        return _agent_active_run_conflict_recovery_result(
            service,
            adapter=adapter,
            root=root,
            context_id=context_id,
            entry_source=entry_source,
            no_web=no_web,
            error=error,
        )
    return _agent_bound_preview_recovery_result(
        service,
        adapter=adapter,
        root=root,
        context_id=context_id,
        entry_source=entry_source,
        no_web=no_web,
    )


def _agent_loop_error_supports_recovery(error: str) -> bool:
    return (
        "/loopora-run" in error
        or "run /loopora-plan first" in error
        or "no ready Loop preview" in error
        or "does not reference a ready Loop preview" in error
        or "another active run is already using" in error
    )


def _agent_bound_preview_recovery_result(
    service,
    *,
    adapter: str,
    root: Path,
    context_id: str,
    entry_source: str,
    no_web: bool,
) -> dict:
    try:
        binding = read_agent_binding(adapter, root, context_id=context_id)
        session_id = str(binding.get("alignment_session_id") or "").strip()
        session = service.get_alignment_session(session_id) if session_id else {}
    except LooporaError as binding_exc:
        if "agent binding is unreadable" not in str(binding_exc) and "agent binding is invalid" not in str(binding_exc):
            return {}
        return {
            "adapter": adapter,
            "workdir": str(root),
            "ready": False,
            "loop_recovery": "repair_agent_binding",
            "binding_error": str(binding_exc),
            "check_command": prefix_loopora_command(f"loopora init {adapter} --check --workdir {shlex.quote(str(root))}"),
        }
    except Exception:  # noqa: BLE001 - error recovery must never replace the primary domain error.
        return {}
    if not binding or not session:
        return _agent_loop_unbound_recovery_result(
            service,
            adapter=adapter,
            root=root,
            context_id=context_id,
            entry_source=entry_source,
            no_web=no_web,
        )
    result = {
        "adapter": adapter,
        "workdir": str(root),
        "ready": False,
        "status": session.get("status"),
        "requires_web_alignment": binding.get("requires_web_alignment") is True,
        "requires_candidate_repair": binding.get("requires_candidate_repair") is True,
        "loopora_fit_contradiction": binding.get("loopora_fit_contradiction") is True,
        "session": session,
        "binding": binding,
        "preview_path": str(binding.get("preview_path") or f"/loops/new/bundle?alignment_session_id={session_id}"),
    }
    _attach_web_url(result, path_key="preview_path", url_key="preview_url", no_web=no_web)
    if result["requires_candidate_repair"]:
        _attach_agent_gen_recovery_fields(result)
    elif result["requires_web_alignment"]:
        _attach_agent_web_review_recovery_fields(result)
    else:
        result["loop_recovery"] = "preview_not_ready"
    return result


def _agent_loop_unbound_recovery_result(
    service,
    *,
    adapter: str,
    root: Path,
    context_id: str,
    entry_source: str,
    no_web: bool,
) -> dict:
    try:
        resolution = service.resolve_loopora_context(root, intent="run", adapter=adapter, context_id=context_id)
    except Exception:  # noqa: BLE001 - error recovery must never replace the primary domain error.
        return {}
    if resolution.get("action") == "plan_first":
        result = {
            "adapter": adapter,
            "workdir": str(root),
            "ready": False,
            "loop_recovery": "plan_first",
            "context_resolution": resolution,
            "next_plan_command": "/loopora-plan",
            "message": (
                "No ready Loop preview or recoverable run context is bound to this Agent session/workdir; "
                "run /loopora-plan first."
            ),
            "next": "Ask the user the ask_user question, then run /loopora-plan with the user's task context.",
        }
        result.update(
            _agent_plan_context_guidance_fields(
                adapter=adapter,
                workdir=root,
                context_id=context_id,
                entry_source=entry_source,
            )
        )
        return result
    if resolution.get("action") != "choose_recoverable_context":
        return {}
    result = {
        "adapter": adapter,
        "workdir": str(root),
        "ready": False,
        "loop_recovery": "choose_recoverable_context",
        "context_resolution": resolution,
    }
    _attach_recoverable_context_preview_urls(result, no_web=no_web)
    return result


def _agent_active_run_conflict_recovery_result(
    service,
    *,
    adapter: str,
    root: Path,
    context_id: str,
    entry_source: str,
    no_web: bool,
    error: str,
) -> dict:
    try:
        activity = service.get_runtime_activity()
    except Exception:  # noqa: BLE001 - error recovery must never replace the primary domain error.
        return {}
    active_runs = [
        _active_run_recovery_projection(service, run)
        for run in list(activity.get("runs") or [])
        if isinstance(run, dict) and _same_recovery_workdir(run.get("workdir"), root)
    ]
    active_runs = [run for run in active_runs if run]
    if not active_runs:
        return {}
    first_run_id = str(active_runs[0].get("id") or "").strip()
    result = {
        "adapter": adapter,
        "workdir": str(root),
        "ready": False,
        "loop_recovery": "active_run_conflict",
        "error": error,
        "message": "another active Loopora run already owns this workdir; continue or stop it before starting another preview or run",
        "active_runs": active_runs,
    }
    if first_run_id:
        result["active_run_path"] = f"/runs/{first_run_id}"
        result["next_active_run_command"] = _agent_next_command_hint(
            adapter=adapter,
            workdir=root,
            context_id=context_id,
            run_id=first_run_id,
            entry_source=entry_source,
        )
        result["stop_active_run_command"] = prefix_loopora_command(f"loopora loops stop {shlex.quote(first_run_id)}")
        _attach_web_url(result, path_key="active_run_path", url_key="active_run_url", no_web=no_web)
    return result


def _active_run_recovery_projection(service, run: dict) -> dict:
    run_id = str(run.get("id") or "").strip()
    if not run_id:
        return {}
    projection = {
        "id": run_id,
        "status": str(run.get("status") or "").strip(),
        "loop_id": str(run.get("loop_id") or "").strip(),
        "loop_name": str(run.get("loop_name") or "").strip(),
        "active_role": str(run.get("active_role") or "").strip(),
        "current_iter": run.get("current_iter"),
        "workdir": str(run.get("workdir") or "").strip(),
        "updated_at": str(run.get("updated_at") or "").strip(),
        "run_path": f"/runs/{run_id}",
    }
    try:
        snapshot = service.run_observation_snapshot(run_id)
    except Exception:  # noqa: BLE001 - step details are best-effort recovery context.
        return projection
    current_step = snapshot.get("current_agent_step") if isinstance(snapshot, dict) else {}
    if isinstance(current_step, dict) and current_step:
        projection["current_step"] = {
            "step_id": str(current_step.get("step_id") or "").strip(),
            "target_agent": str(current_step.get("target_agent") or "").strip(),
            "context_path": str(current_step.get("context_absolute_path") or current_step.get("context_path") or "").strip(),
            "result_template_path": str(
                (current_step.get("submit_hint") if isinstance(current_step.get("submit_hint"), dict) else {}).get(
                    "result_template_absolute_path"
                )
                or (current_step.get("submit_hint") if isinstance(current_step.get("submit_hint"), dict) else {}).get(
                    "result_template_path"
                )
                or ""
            ).strip(),
        }
    return projection


def _same_recovery_workdir(candidate: object, root: Path) -> bool:
    if not candidate:
        return False
    try:
        return Path(str(candidate)).resolve() == root.resolve()
    except (OSError, RuntimeError):
        return str(candidate).strip() == str(root)


def _print_agent_loop_recovery_result(result: dict) -> None:
    if result.get("loop_recovery") == "active_run_conflict":
        typer.echo("loop_recovery: continue or stop the active Loopora run before starting another preview or run")
        _print_active_run_conflict_recovery(result)
        return
    if result.get("loop_recovery") == "plan_first":
        typer.echo("loop_recovery: run /loopora-plan before /loopora-run can start")
        message = str(result.get("message") or "").strip()
        if message:
            typer.echo(f"message: {message}")
        typer.echo(f"next_plan_command: {result.get('next_plan_command') or '/loopora-plan'}")
        _print_agent_plan_context_request_fields(result)
        _print_agent_plan_context_guidance_fields(result)
        typer.echo(
            f"next: {result.get('next') or 'describe the task goal, fake-done risks, required evidence, and judgment tradeoffs in /loopora-plan.'}"
        )
        return
    if result.get("loop_recovery") == "choose_recoverable_context":
        typer.echo("loop_recovery: choose a recoverable Loopora context before /loopora-run can start")
        _print_recoverable_context_choices(result.get("context_resolution") if isinstance(result.get("context_resolution"), dict) else {})
        return
    if result.get("loop_recovery") == "repair_agent_binding":
        typer.echo("loop_recovery: repair the current Agent binding before /loopora-run can start")
        typer.echo(f"binding_error: {result.get('binding_error')}")
        typer.echo(f"check_command: {result.get('check_command')}")
        typer.echo("next: inspect the binding, rerun the check, or use /loopora-plan fresh if you want a new Loop.")
        return
    if result["requires_candidate_repair"]:
        typer.echo("loop_recovery: repair the current plan file before /loopora-run can start")
        _print_agent_repair_guidance(result)
    elif result["requires_web_alignment"]:
        typer.echo("loop_recovery: finish the current Web review before /loopora-run can start")
        _print_agent_web_review_guidance(result)
    else:
        typer.echo("loop_recovery: the current preview is not ready; return to /loopora-plan or Web review before /loopora-run")
    session = result.get("session") if isinstance(result.get("session"), dict) else {}
    session_id = str(session.get("id") or "")
    typer.echo(f"session_id: {session_id}")
    typer.echo(f"preview_url: {result.get('preview_url') or result.get('preview_path')}")
    _print_web_status(result)


def _print_agent_next_recovery_result(result: dict) -> None:
    if result.get("loop_recovery") == "choose_recoverable_context":
        typer.echo("loop_recovery: choose a recoverable Loopora context before claiming the next Agent step")
        message = str(result.get("message") or "").strip()
        if message:
            typer.echo(f"message: {message}")
        if result.get("next_active_run_command"):
            typer.echo(f"next_active_run_command: {result.get('next_active_run_command')}")
        _print_recoverable_context_choices(result.get("context_resolution") if isinstance(result.get("context_resolution"), dict) else {})
        return
    if result.get("loop_recovery") == "plan_first":
        typer.echo("loop_recovery: run /loopora-plan and /loopora-run before claiming the next Agent step")
        message = str(result.get("message") or "").strip()
        if message:
            typer.echo(f"message: {message}")
        typer.echo(f"next_plan_command: {result.get('next_plan_command') or '/loopora-plan'}")
        _print_agent_plan_context_request_fields(result)
        _print_agent_plan_context_guidance_fields(result)
        typer.echo(f"next: {result.get('next') or 'create and start a Loop before using agent next.'}")
        return
    _print_agent_loop_recovery_result(result)


def _agent_loop_recovery_json_payload(result: dict) -> dict:
    payload = {"agent_loop_recovery_summary": _agent_loop_recovery_summary(result)}
    payload.update(result)
    return payload


def _agent_next_recovery_json_payload(result: dict) -> dict:
    payload = {"agent_next_recovery_summary": _agent_loop_recovery_summary(result)}
    payload.update(result)
    return payload


def _agent_loop_recovery_summary(result: dict) -> dict:
    summary: dict[str, object] = {
        "ready": bool(result.get("ready")),
        "loop_recovery": str(result.get("loop_recovery") or "").strip(),
    }
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
            choice
            for choice in choices
            if choice.get("runnable") is False and id(choice) not in displayed_choice_ids
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


def _validation_repair_hints(error: str) -> list[str]:
    text = str(error or "")
    hints: list[str] = _task_projection_repair_hints(text)
    hints.extend(_semantic_lint_repair_hints(text))
    for patterns, hint in _VALIDATION_REPAIR_HINT_RULES:
        if any(pattern in text for pattern in patterns):
            hints.append(hint)
    deduped: list[str] = []
    for hint in hints:
        if hint not in deduped:
            deduped.append(hint)
    return deduped[:8]


def _semantic_lint_repair_hints(error: str) -> list[str]:
    issues = _semantic_lint_issues(error)
    hints: list[str] = []
    for issue in issues:
        hint = _semantic_lint_issue_hint(issue)
        if hint:
            hints.append(hint)
    return hints


def _semantic_lint_issues(error: str) -> list[str]:
    text = str(error or "").strip()
    if not text:
        return []
    prefix = "bundle semantic lint failed:"
    if prefix not in text:
        return []
    text = text.split(prefix, 1)[1]
    return [item.strip() for item in text.split(";") if item.strip()]


_SEMANTIC_LINT_HINT_RULES = (
    (
        ("collaboration_summary must explain why this task needs multi-round loopora governance",),
        "explain in collaboration_summary what later evidence, reviews, handoffs, or GateKeeper rounds add beyond one Agent pass",
    ),
    (
        ("collaboration_summary must explain the governance story",),
        "rewrite collaboration_summary with the concrete task, evidence flow, blockers, and GateKeeper closure",
    ),
    (("collaboration_summary must mention evidence",), "mention the evidence, proof, handoff, or blocker path in collaboration_summary"),
    (("collaboration_summary must explain gatekeeper",), "describe the GateKeeper or final judgment posture in collaboration_summary"),
    (
        ("spec must include residual risk guidance",),
        "add # Residual Risk guidance naming accepted risks, owners/follow-ups, or fail-closed conditions",
    ),
    (
        ("spec residual risk guidance must name accepted risk handling or fail closed",),
        "add # Residual Risk guidance naming accepted risks, owners/follow-ups, or fail-closed conditions",
    ),
    (
        ("alignment bundle must project task verdict evidence into proven, weak, unproven, blocking, and residual risk buckets",),
        "project evidence buckets into collaboration_summary, Evidence Preferences, Inspector posture, and GateKeeper closure",
    ),
    (
        ("web alignment bundles must use gatekeeper completion_mode",),
        "set loop.completion_mode to gatekeeper and include a finishing GateKeeper role/step",
    ),
    (
        ("workflow.collaboration_intent must explain evidence flow",),
        "rewrite workflow.collaboration_intent to name evidence flow, GateKeeper closure, and weak-evidence or fake-done exposure",
    ),
    (
        ("workflow.collaboration_intent must explain the task-specific judgment order",),
        "rewrite workflow.collaboration_intent to explain the task-specific Builder, review, and GateKeeper order",
    ),
    (
        ("must query", "inputs.evidence_query"),
        "add inputs.evidence_query to the workflow step named in the lint issue so it can see required evidence",
    ),
    (
        ("must include", "inputs.handoffs_from"),
        "add inputs.handoffs_from to the workflow step named in the lint issue so upstream handoffs are explicit",
    ),
    (
        ("must name", "inputs.handoffs_from"),
        "add inputs.handoffs_from to the workflow step named in the lint issue so upstream handoffs are explicit",
    ),
    (
        ("must declare inputs.iteration_memory",),
        "add inputs.iteration_memory=summary_only where the lint issue names cross-iteration evidence flow",
    ),
    (
        ("must use inputs.iteration_memory=summary_only",),
        "set inputs.iteration_memory=summary_only for the workflow step named in the lint issue",
    ),
    (
        ("role_definition", "must use a task-specific role name"),
        "rename generic role_definitions to task-specific role names tied to this task's evidence responsibilities",
    ),
    (
        ("role_definition", "must include task-scoped posture_notes"),
        "add task-scoped posture_notes explaining each role's evidence responsibility",
    ),
    (
        ("role_definitions must have distinct task evidence responsibilities",),
        "split overlapping review roles so each role_definition owns a distinct task evidence responsibility",
    ),
    (("markdown-fenced output",), "save the candidate as one raw YAML document without markdown fences"),
    (("must start with version: 1",), "make the candidate YAML start with version: 1"),
    (
        ("metadata.source_bundle_id",),
        "remove lineage metadata such as metadata.source_bundle_id and metadata.revision from the final candidate",
    ),
    (
        ("metadata.revision",),
        "remove lineage metadata such as metadata.source_bundle_id and metadata.revision from the final candidate",
    ),
    (
        ("task-scoped, not personality memory",),
        "rewrite the bundle as a task-scoped Loop instead of global preferences or personality memory",
    ),
    (
        ("must not present prompt pack",),
        "reframe the bundle as Loopora governance, not a prompt pack, role zoo, loop script, benchmark grinder, or chat wrapper",
    ),
    (
        ("must not claim a single pass",),
        "remove claims that one pass, direct chat, or no-new-evidence work is sufficient; define evidence and GateKeeper value",
    ),
)


def _semantic_lint_issue_hint(issue: str) -> str:
    lower = issue.lower()
    section = _missing_spec_section(issue)
    if section:
        return f"add # {section} bullets that make the task judgment reviewable and runnable"
    for needles, hint in _SEMANTIC_LINT_HINT_RULES:
        if all(needle in lower for needle in needles):
            return hint
    return "address semantic lint issue in the plan file: " + _clip_inline(issue, 180)


def _missing_spec_section(issue: str) -> str:
    match = re.search(r"spec must include at least one (?P<section>Done When|Success Surface|Fake Done|Evidence Preferences) bullet", issue)
    if not match:
        return ""
    return str(match.group("section") or "").strip()


def _task_projection_repair_hints(error: str) -> list[str]:
    pattern = re.compile(
        r"agent-first candidate must project (?:the )?(?:explicit )?host Agent "
        r"(?P<area>[^:\n]+?) into runnable surfaces:\s*missing\s+(?P<terms>[^;.\n]+)"
    )
    hints: list[str] = []
    for match in pattern.finditer(str(error or "")):
        terms = [term.strip() for term in match.group("terms").split(",") if term.strip()]
        if not terms:
            continue
        area = str(match.group("area") or "task summary").strip()
        if area == "task summary":
            hints.extend(
                [
                    "add these missing task objects from --message to runnable plan surfaces: " + ", ".join(terms[:8]),
                    "include those objects in spec success criteria, role responsibilities, workflow intent, and evidence preferences",
                ]
            )
            continue
        hints.extend(
            [
                f"add these missing {area} categories from --message to runnable plan surfaces: " + ", ".join(terms[:8]),
                _task_projection_area_repair_hint(area),
            ]
        )
    return list(dict.fromkeys(hints))


def _task_projection_area_repair_hint(area: str) -> str:
    normalized = str(area or "").strip().lower()
    hints = {
        "success criteria": "include those categories in spec Done When/Success Surface, role responsibilities, workflow intent, evidence preferences, and GateKeeper closure",
        "fake-done risks": "include those risks in spec Fake Done, Inspector blocking checks, GateKeeper pass/block policy, and evidence expectations",
        "evidence preferences": "include those evidence modes in spec Evidence Preferences, Inspector responsibilities, workflow handoffs, and GateKeeper closure",
        "judgment tradeoffs": "include those tradeoffs in collaboration summary, role postures, workflow sequencing, and GateKeeper decision policy",
        "execution strategy": "include those strategy categories in workflow order, role responsibilities, next-pass priorities, and GateKeeper repair direction",
        "residual-risk policy": "include those residual-risk rules in spec Residual Risk, GateKeeper pass/block policy, and owner/follow-up semantics",
    }
    return hints.get(
        normalized,
        "include those categories in spec, role responsibilities, workflow intent, evidence rules, and GateKeeper closure",
    )


_VALIDATION_REPAIR_HINT_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("metadata.name is required",), "add metadata.name so the plan has a stable reviewable identity"),
    (("spec is required", "spec."), "fill the spec with the concrete task contract, done conditions, risks, and evidence expectations"),
    (("role_definitions", "workflow"), "include role_definitions and workflow steps so the Loop can run through Builder, reviewers, and GateKeeper"),
    (("spec Task must describe the concrete user-facing task",), "make # Task name the concrete user-facing outcome, not only internal governance language"),
    (("must follow Chinese user language",), "keep user-facing plan names, spec prose, role names, and posture notes in the user's language"),
    (("host Agent task summary", "project the host Agent task summary"), "project the task objects from --message into spec, roles, workflow intent, and evidence rules"),
    (("evidence preferences", "explicit host Agent evidence"), "compile required evidence modes into runnable surfaces, not only the CLI summary"),
    (("Loopora fit", "one-off", "no-new-evidence"), "explain what later rounds add: new evidence, handoffs, GateKeeper judgment, or residual-risk tracking"),
)


def _agent_gen_error_summary(result: dict) -> str:
    session = result.get("session") if isinstance(result.get("session"), dict) else {}
    validation = session.get("validation") if isinstance(session.get("validation"), dict) else {}
    return str(session.get("error_message") or validation.get("error") or "").strip()


def _non_bool_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else f"{text[: limit - 1].rstrip()}…"


def _clip_inline(text: str, limit: int) -> str:
    return _clip(" ".join(str(text or "").split()), limit)


def _agent_next_command_hint(*, adapter: str, context_id: str, run_id: str, entry_source: str = "", workdir: Path | None = None) -> str:
    bits = [f"loopora agent {adapter} next", "--workdir", _agent_command_workdir_arg(workdir)]
    if run_id:
        bits.append(f"--run-id {run_id}")
    elif context_id:
        bits.append(f"--context-id {context_id}")
    bits.append("--json")
    normalized_entry_source = str(entry_source or "").strip()
    if normalized_entry_source:
        bits.extend(["--entry-source", shlex.quote(normalized_entry_source)])
    command = " ".join(bits)
    return prefix_loopora_command(command, entry_source=normalized_entry_source)


def _agent_command_workdir_arg(workdir: Path | None) -> str:
    if workdir is None or str(workdir).strip() in ("", "."):
        return '"$PWD"'
    try:
        return shlex.quote(str(Path(workdir).expanduser().resolve()))
    except OSError:
        return shlex.quote(str(workdir))


def _print_web_status(result: dict) -> None:
    web = result.get("web")
    if not isinstance(web, dict):
        return
    base_url = str(web.get("base_url") or "").strip()
    if not base_url:
        return
    if web.get("started"):
        typer.echo(f"web: started {base_url}")
    elif web.get("reused"):
        typer.echo(f"web: reused {base_url}")
    else:
        typer.echo(f"web: {base_url}")
    warning = str(web.get("warning") or "").strip()
    if warning:
        typer.echo(f"web_warning: {warning}")


def _read_result_json(path: Path) -> tuple[dict, dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LooporaError(f"result file is not valid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise LooporaError("result file must contain one JSON object")
    if "loopora_host_dispatch" in payload or "result" in payload:
        host_dispatch = payload.get("loopora_host_dispatch")
        result = payload.get("result")
        if not isinstance(host_dispatch, dict):
            raise LooporaError("result wrapper must contain loopora_host_dispatch object")
        if not isinstance(result, dict):
            raise LooporaError("result wrapper must contain result object")
        return result, host_dispatch
    return payload, {}
