from __future__ import annotations

from pathlib import Path
import shlex

import typer

from loopora.agent_adapter_workdir_recovery import adapter_workdir_state
from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.cli_common import echo_json
from loopora.first_use_action_readiness import (
    first_use_action_readiness_summary,
    project_first_use_action_readiness_summary,
)
from loopora.spec_recovery_commands import SpecInitStrategyContext, spec_init_strategy_source_error


def exit_if_unusable_loop_workdir(  # noqa: PLR0913 - mirrors the direct Loop compose recovery surface.
    *,
    workdir: Path | str | None,
    action: str,
    retry_command: str,
    json_output: bool = False,
    retry_before_readiness: bool = False,
    strategy_context: SpecInitStrategyContext | None = None,
) -> None:
    state = adapter_workdir_state(workdir)
    if state["status"] == "ready":
        return
    exit_with_loop_workdir_recovery(
        workdir=workdir,
        action=action,
        retry_command=retry_command,
        json_output=json_output,
        retry_before_readiness=retry_before_readiness,
        strategy_context=strategy_context,
    )


def exit_with_loop_workdir_recovery(  # noqa: PLR0913 - mirrors the direct Loop compose recovery surface.
    *,
    workdir: Path | str | None,
    action: str,
    retry_command: str,
    json_output: bool = False,
    retry_before_readiness: bool = False,
    strategy_context: SpecInitStrategyContext | None = None,
) -> None:
    payload = loop_workdir_recovery_payload(
        workdir=workdir,
        action=action,
        retry_command=retry_command,
        retry_before_readiness=retry_before_readiness,
        strategy_context=strategy_context,
    )
    if json_output:
        echo_json(payload)
    else:
        _print_loop_workdir_recovery(payload)
    raise typer.Exit(code=1)


def loop_workdir_recovery_payload(
    *,
    workdir: Path | str | None,
    action: str,
    retry_command: str,
    retry_before_readiness: bool = False,
    strategy_context: SpecInitStrategyContext | None = None,
) -> dict[str, object]:
    state = adapter_workdir_state(workdir)
    strategy_error = spec_init_strategy_source_error(strategy_context=strategy_context)
    state = dict(state)
    if strategy_error:
        state["strategy_source_state"] = {
            "status": "unavailable",
            "error": strategy_error,
        }
    summary = _loop_workdir_summary(str(state["status"]), state=state)
    state["summary"] = summary
    next_actions = _loop_workdir_next_actions(
        state,
        action=action,
        retry_command=retry_command,
        retry_before_readiness=retry_before_readiness,
    )
    payload = {
        "loop_workdir_recovery_summary": {
            "ready": False,
            "loop_recovery": "target_workdir_unavailable",
            "status": "blocked_by_workdir",
            "surface": "cli_loop_command",
            "action": action,
            "workdir": state["workdir"],
            "workdir_state_status": str(state.get("status") or ""),
            "next_action_kinds": _loop_action_kinds(next_actions),
        },
        "loop_recovery": "target_workdir_unavailable",
        "status": "blocked_by_workdir",
        "surface": "cli_loop_command",
        "action": action,
        "workdir": state["workdir"],
        "workdir_state": state,
        "summary": summary,
        "error": summary,
        "next_actions": next_actions,
    }
    _project_loop_workdir_action_contract(payload)
    return payload


def _project_loop_workdir_action_contract(payload: dict[str, object]) -> None:
    actions = [action for action in list(payload.get("next_actions") or []) if isinstance(action, dict)]
    action_kinds = _loop_action_kinds(actions)
    payload["next_action_kinds"] = action_kinds
    readiness = first_use_action_readiness_summary(actions)
    project_first_use_action_readiness_summary(payload, prefix="next_action", readiness=readiness)
    summary = payload.get("loop_workdir_recovery_summary")
    if isinstance(summary, dict):
        summary["next_action_kinds"] = list(action_kinds)
        project_first_use_action_readiness_summary(summary, prefix="next_action", readiness=readiness)


def _loop_action_kinds(actions: list[dict[str, object]]) -> list[str]:
    return [str(action.get("kind") or "").strip() for action in actions if str(action.get("kind") or "").strip()]


def _loop_workdir_summary(status: str, *, state: dict[str, object] | None = None) -> str:
    strategy_state = state.get("strategy_source_state") if isinstance(state, dict) else {}
    strategy_error = str(strategy_state.get("error") or "").strip() if isinstance(strategy_state, dict) else ""
    if status == "required":
        summary = "Target project directory is required; choose a project directory before composing or running a Loop."
        return _append_strategy_source_note(summary) if strategy_error else summary
    if status == "missing":
        summary = "Target project directory does not exist yet; create it before composing or running a Loop."
        return _append_strategy_source_note(summary) if strategy_error else summary
    if status == "not_directory":
        summary = "Target project path exists but is not a directory; choose a project directory before composing or running a Loop."
        return _append_strategy_source_note(summary) if strategy_error else summary
    if status == "unavailable":
        summary = "Target project directory cannot be inspected; choose a readable project directory before composing or running a Loop."
        return _append_strategy_source_note(summary) if strategy_error else summary
    return ""


def _append_strategy_source_note(summary: str) -> str:
    return f"{summary} The selected Strategy Source file is also unavailable; repair it before retrying."


def _loop_workdir_next_actions(
    state: dict[str, object],
    *,
    action: str,
    retry_command: str,
    retry_before_readiness: bool,
) -> list[dict[str, str]]:
    commands = state.get("commands") if isinstance(state.get("commands"), dict) else {}
    create_command = str(commands.get("create") or "")
    actions: list[dict[str, str]] = []
    workdir_action = (
        {"kind": "create_workdir", "command": create_command}
        if create_command
        else {"kind": "choose_workdir"}
    )
    actions.append(workdir_action)
    workdir_action_kind = str(workdir_action.get("kind") or "")
    confirm_action = {"kind": "confirm_readiness"}
    retry_action = {"kind": _loop_retry_action_kind(action)}
    if create_command:
        confirm_action["command"] = copyable_loopora_command(
            f"loopora doctor --workdir {shlex.quote(str(state['workdir']))}"
        )
        if retry_command:
            retry_action["command"] = copyable_loopora_command(retry_command)
    strategy_state = state.get("strategy_source_state") if isinstance(state.get("strategy_source_state"), dict) else {}
    strategy_error = str(strategy_state.get("error") or "").strip()
    if strategy_error:
        retry_action.pop("command", None)
        actions.append(
            {
                "kind": "repair_strategy_source",
                "validation_error": strategy_error,
                "after_action": workdir_action_kind,
            }
        )
        confirm_action["after_action"] = "repair_strategy_source"
        retry_action["after_action"] = "confirm_readiness"
        actions.append(confirm_action)
        actions.append(retry_action)
        return actions
    if retry_before_readiness:
        retry_action["after_action"] = workdir_action_kind
        confirm_action["after_action"] = str(retry_action.get("kind") or "")
        actions.append(retry_action)
        actions.append(confirm_action)
        return actions
    confirm_action["after_action"] = workdir_action_kind
    retry_action["after_action"] = "confirm_readiness"
    actions.append(confirm_action)
    actions.append(retry_action)
    return actions


def _loop_retry_action_kind(action: str) -> str:
    return {
        "create": "retry_loop_create",
        "run": "retry_loop_run",
        "rerun": "retry_loop_rerun",
    }.get(action, "retry_loop_command")


def _print_loop_workdir_recovery(payload: dict[str, object]) -> None:
    action = str(payload.get("action") or "create")
    workdir_state = payload.get("workdir_state") if isinstance(payload.get("workdir_state"), dict) else {}
    typer.echo(f"Loopora Loop {action} is blocked")
    typer.echo(f"target project: {payload.get('workdir')}")
    typer.echo(f"project directory state: {workdir_state.get('status')}")
    summary = str(payload.get("summary") or "").strip()
    if summary:
        typer.echo(f"note: {summary}")
    typer.echo("next:")
    for item in payload.get("next_actions") or []:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "")
        command = str(item.get("command") or "").strip()
        label = {
            "create_workdir": "Create the target project directory",
            "choose_workdir": "Choose an existing project directory",
            "repair_strategy_source": "Repair the selected Strategy Source file",
            "confirm_readiness": "Confirm readiness after the target exists",
            "retry_loop_create": "Retry the Loop command",
            "retry_loop_run": "Retry the Loop command",
            "retry_loop_rerun": "Retry the Loop command",
            "retry_loop_command": "Retry the Loop command",
        }.get(kind, kind)
        detail = command
        if not detail and kind == "repair_strategy_source":
            detail = str(item.get("validation_error") or "").strip()
        typer.echo(f"- {label}: {detail}" if detail else f"- {label}")
