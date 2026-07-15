from __future__ import annotations

from pathlib import Path

import typer

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
from loopora.cli_agent_plan_results import (
    _agent_gen_json_payload,
)
from loopora.cli_agent_plan_recovery import (
    agent_plan_error_requires_message as _agent_plan_error_requires_message,
    agent_plan_message_required_result as _agent_plan_message_required_result,
    print_agent_plan_context_guidance_fields as _print_agent_plan_context_guidance_fields,
    print_agent_plan_context_request_fields as _print_agent_plan_context_request_fields,
    print_agent_plan_message_required as _print_agent_plan_message_required,
)
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
        echo_json(_agent_gen_json_payload(result))
    else:
        _print_agent_plan_message_required(result)
    return True


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
