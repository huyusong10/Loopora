from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path

from loopora.agent_adapters import prefix_loopora_command
from loopora.cli_agent_runtime_support import agent_next_command_hint as _agent_next_command_hint
from loopora.cli_agent_runtime_support import attach_web_url as _attach_web_url


@dataclass(frozen=True)
class AgentActiveRunConflictRecoveryRequest:
    service: object
    adapter: str
    root: Path
    context_id: str
    entry_source: str
    no_web: bool
    error: str


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


def _agent_active_run_conflict_recovery_result(request: AgentActiveRunConflictRecoveryRequest) -> dict:
    try:
        activity = request.service.get_runtime_activity()
    except Exception:  # noqa: BLE001 - error recovery must never replace the primary domain error.
        return {}
    active_runs = [
        _active_run_recovery_projection(request.service, run)
        for run in list(activity.get("runs") or [])
        if isinstance(run, dict) and _same_recovery_workdir(run.get("workdir"), request.root)
    ]
    active_runs = [run for run in active_runs if run]
    if not active_runs:
        return {}
    first_run_id = str(active_runs[0].get("id") or "").strip()
    result = {
        "adapter": request.adapter,
        "workdir": str(request.root),
        "ready": False,
        "loop_recovery": "active_run_conflict",
        "error": request.error,
        "message": "another active Loopora run already owns this workdir; continue or stop it before starting another preview or run",
        "active_runs": active_runs,
    }
    if first_run_id:
        result["active_run_path"] = f"/runs/{first_run_id}"
        result["next_active_run_command"] = _agent_next_command_hint(
            adapter=request.adapter,
            workdir=request.root,
            context_id=request.context_id,
            run_id=first_run_id,
            entry_source=request.entry_source,
        )
        result["stop_active_run_command"] = prefix_loopora_command(f"loopora loops stop {shlex.quote(first_run_id)}")
        _attach_web_url(result, path_key="active_run_path", url_key="active_run_url", no_web=request.no_web)
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
        submit_hint = current_step.get("submit_hint") if isinstance(current_step.get("submit_hint"), dict) else {}
        projection["current_step"] = {
            "step_id": str(current_step.get("step_id") or "").strip(),
            "target_agent": str(current_step.get("target_agent") or "").strip(),
            "context_path": str(current_step.get("context_absolute_path") or current_step.get("context_path") or "").strip(),
            "result_template_path": str(
                submit_hint.get("result_template_absolute_path") or submit_hint.get("result_template_path") or ""
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
