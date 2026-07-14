from __future__ import annotations

import shlex
from pathlib import Path

import typer

from loopora.agent_adapters import resolve_adapter_project_root
from loopora.agent_native_task_proof import PASSING_TASK_VERDICT_STATUSES as _PASSING_TASK_VERDICT_STATUSES
from loopora.cli_agent_context_recovery_output import (
    _agent_loop_recovery_json_payload,
    _agent_next_recovery_json_payload,
    _print_active_run_conflict_recovery,
    _print_recoverable_context_choices,
)
from loopora.cli_agent_plan_output import (
    _print_agent_repair_guidance,
    _print_agent_web_review_guidance,
)
from loopora.cli_agent_plan_recovery_results import (
    REPAIR_CLI_COMMAND_POLICY,
    REPAIR_NEXT_REPAIR_STEP,
    REPAIR_REFERENCE,
    _agent_plan_repair_action,
    _agent_repair_cli_command,
    _attach_agent_gen_recovery_fields,
)
from loopora.cli_agent_plan_results import (
    _agent_gen_json_payload,
)
from loopora.cli_agent_plan_recovery import (
    agent_plan_error_requires_message as _agent_plan_error_requires_message,
    agent_plan_message_required_result as _agent_plan_message_required_result,
    print_agent_plan_context_request_fields as _print_agent_plan_context_request_fields,
    print_agent_plan_message_required as _print_agent_plan_message_required,
    print_agent_plan_surface_hint as _print_agent_plan_surface_hint,
)
from loopora.cli_agent_runtime_support import print_preview_url as _print_preview_url
from loopora.cli_agent_runtime_support import print_web_status as _print_web_status
from loopora.cli_agent_recovery_results import (
    _agent_loop_unready_recovery_result,
    _agent_next_recovery_result,
)
from loopora.cli_shared import echo_json

PASSING_TASK_VERDICT_STATUSES = _PASSING_TASK_VERDICT_STATUSES


def _print_agent_plan_recovery_guidance(
    exc: Exception,
    *,
    adapter: str,
    workdir: Path,
    context_id: str,
    entry_source: str,
    message: str,
    bundle_file: Path | None,
    json_output: bool,
) -> bool:
    error = str(exc)
    if _agent_plan_error_requires_candidate_file_repair(error):
        result = _agent_plan_candidate_file_repair_result(
            adapter=adapter,
            workdir=workdir,
            context_id=context_id,
            entry_source=entry_source,
            message=message,
            bundle_file=bundle_file,
            error=error,
        )
        if json_output:
            echo_json(_agent_gen_json_payload(result))
        else:
            typer.echo("Loopora Loop preview needs plan file repair before /loopora-run")
            typer.echo(f"validation_error: {result['validation_error']}")
            _print_agent_repair_guidance(result)
        return True
    if not _agent_plan_error_requires_message(error):
        return False
    result = _agent_plan_message_required_result(
        adapter=adapter,
        workdir=workdir,
        context_id=context_id,
        entry_source=entry_source,
    )
    if json_output:
        echo_json(_agent_gen_json_payload(result))
    else:
        _print_agent_plan_message_required(result)
    return True


def _agent_plan_error_requires_candidate_file_repair(error: str) -> bool:
    return str(error or "").strip() in {
        "bundle file could not be read",
        "bundle file does not exist",
        "bundle file must be UTF-8 encoded YAML",
        "candidate plan file could not be saved",
    }


def _agent_plan_candidate_file_repair_result(
    *,
    adapter: str,
    workdir: Path,
    context_id: str,
    entry_source: str,
    message: str,
    bundle_file: Path | None,
    error: str,
) -> dict:
    root = resolve_adapter_project_root(workdir)
    plan_file = str(bundle_file or "").strip()
    task_message = str(message or "").strip()
    result = {
        "adapter": adapter,
        "workdir": str(root),
        "ready": False,
        "status": "blocked",
        "requires_web_alignment": False,
        "requires_candidate_repair": True,
        "loopora_fit_contradiction": False,
        "session": {
            "id": "",
            "status": "blocked",
            "error_message": str(error or "").strip(),
            "validation": {"error": str(error or "").strip()},
            "bundle_path": "",
            "transcript": [{"role": "user", "content": task_message}] if task_message else [],
        },
        "binding": {
            "source_path": plan_file,
            "adapter": adapter,
            "workdir": str(root),
            "candidate_adapter": adapter,
            "candidate_entry_source": entry_source,
            "entry_source": entry_source,
            "host_context_id": context_id,
        },
        "candidate_origin": "agent_entry",
        "candidate_entry_source": entry_source,
        "host_context_id": context_id,
    }
    _attach_agent_gen_recovery_fields(result)
    if plan_file:
        result["repair_slash_command"] = f"/loopora-plan {shlex.quote(plan_file)}"
    result["next_plan_command"] = "/loopora-plan"
    result["repair_reference"] = REPAIR_REFERENCE
    result["next_repair_step"] = REPAIR_NEXT_REPAIR_STEP
    repair_cli_command = _agent_repair_cli_command(result, plan_file=plan_file)
    if repair_cli_command:
        result["repair_cli_command"] = repair_cli_command
        result["repair_cli_command_policy"] = REPAIR_CLI_COMMAND_POLICY
    action = _agent_plan_repair_action(result)
    if action:
        result["repair_action"] = action
    return result


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


def _print_agent_loop_recovery_result(result: dict) -> None:
    preview_printed = False
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
        _print_agent_plan_surface_hint()
        typer.echo(
            f"next: {result.get('next') or 'describe the Loopora fit reason, task goal, fake-done risks, required evidence, judgment tradeoffs, and any direct-path context in /loopora-plan.'}"
        )
        return
    if result.get("loop_recovery") == "choose_recoverable_context":
        typer.echo("loop_recovery: choose a recoverable Loopora context before /loopora-run can start")
        _print_recoverable_context_choices(result.get("context_resolution") if isinstance(result.get("context_resolution"), dict) else {})
        return
    if result.get("loop_recovery") == "repair_agent_binding":
        typer.echo("loop_recovery: repair the current Agent context card before /loopora-run can start")
        typer.echo(f"context_card_error: {result.get('context_card_error') or result.get('binding_error')}")
        typer.echo(f"check_command: {result.get('check_command')}")
        typer.echo("next: inspect the context card, rerun the check, or use /loopora-plan fresh if you want a new Loop.")
        return
    if result["requires_candidate_repair"]:
        typer.echo("loop_recovery: repair the current plan file before /loopora-run can start")
        _print_agent_repair_guidance(result)
    elif result["requires_web_alignment"]:
        typer.echo("loop_recovery: finish the current Web review before /loopora-run can start")
        _print_agent_web_review_guidance(result)
        preview_printed = True
    else:
        typer.echo("loop_recovery: the current preview is not ready; return to /loopora-plan or Web review before /loopora-run")
    session = result.get("session") if isinstance(result.get("session"), dict) else {}
    session_id = str(session.get("id") or "")
    typer.echo(f"session_id: {session_id}")
    if not preview_printed:
        _print_preview_url(result)
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
        _print_agent_plan_surface_hint()
        typer.echo(f"next: {result.get('next') or 'create and start a Loop before using agent next.'}")
        return
    _print_agent_loop_recovery_result(result)
