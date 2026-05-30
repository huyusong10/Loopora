from __future__ import annotations

import shlex
from pathlib import Path

import typer

from loopora.agent_adapters import (
    prefix_loopora_command,
    read_agent_binding,
    resolve_adapter_project_root,
)
from loopora.agent_native_task_proof import PASSING_TASK_VERDICT_STATUSES as _PASSING_TASK_VERDICT_STATUSES
from loopora.cli_agent_context_recovery_output import (
    _agent_loop_recovery_json_payload,
    _agent_next_recovery_json_payload,
    _print_active_run_conflict_recovery,
    _print_recoverable_context_choices,
)
from loopora.cli_agent_runtime_support import agent_next_command_hint as _agent_next_command_hint
from loopora.cli_agent_runtime_support import attach_recoverable_context_preview_urls as _attach_recoverable_context_preview_urls
from loopora.cli_agent_runtime_support import attach_web_url as _attach_web_url
from loopora.cli_agent_runtime_support import print_web_status as _print_web_status
from loopora.cli_agent_plan_output import (
    _agent_gen_json_payload,
    _attach_agent_gen_recovery_fields,
    _attach_agent_web_review_recovery_fields,
    _print_agent_repair_guidance,
    _print_agent_web_review_guidance,
)
from loopora.cli_agent_plan_recovery import (
    agent_plan_context_guidance_fields as _agent_plan_context_guidance_fields,
    agent_plan_error_requires_message as _agent_plan_error_requires_message,
    agent_plan_message_required_result as _agent_plan_message_required_result,
    print_agent_plan_context_guidance_fields as _print_agent_plan_context_guidance_fields,
    print_agent_plan_context_request_fields as _print_agent_plan_context_request_fields,
    print_agent_plan_message_required as _print_agent_plan_message_required,
)
from loopora.cli_shared import echo_json
from loopora.service import LooporaError

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
        if not _agent_context_card_error_is_repairable(str(binding_exc)):
            return {}
        return {
            "adapter": adapter,
            "workdir": str(root),
            "ready": False,
            "loop_recovery": "repair_agent_binding",
            "binding_error": str(binding_exc),
            "context_card_error": str(binding_exc),
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


def _agent_context_card_error_is_repairable(error: str) -> bool:
    return any(
        marker in error
        for marker in (
            "agent context card is unreadable",
            "agent context card is invalid",
            "agent binding is unreadable",
            "agent binding is invalid",
        )
    )


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
