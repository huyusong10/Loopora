from __future__ import annotations

from pathlib import Path

import typer

from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.cli_common import echo_json
from loopora.first_use_action_readiness import (
    first_use_action_readiness_summary,
    project_first_use_action_readiness_summary,
)
from loopora.spec_recovery_commands import (
    SpecInitStrategyContext,
    spec_init_strategy_source_error,
    spec_init_recovery_command,
    spec_init_recovery_command_template,
)
from loopora.workdir_inputs import spec_path_state


def exit_if_unusable_loop_spec(  # noqa: PLR0913 - mirrors the direct Loop compose recovery surface.
    *,
    spec: Path | str | None,
    action: str,
    retry_command: str,
    retry_command_template: str = "",
    strategy_context: SpecInitStrategyContext | None = None,
    json_output: bool = False,
) -> None:
    state = loop_spec_state(
        spec,
        strategy_context=strategy_context,
    )
    if state["status"] == "ready":
        return
    payload = loop_spec_recovery_payload(
        spec=spec,
        action=action,
        retry_command=retry_command,
        retry_command_template=retry_command_template,
        strategy_context=strategy_context,
    )
    if json_output:
        echo_json(payload)
    else:
        _print_loop_spec_recovery(payload)
    raise typer.Exit(code=1)


def exit_if_unusable_loop_strategy_source(
    *,
    action: str,
    strategy_context: SpecInitStrategyContext | None = None,
    json_output: bool = False,
) -> None:
    strategy_error = spec_init_strategy_source_error(strategy_context=strategy_context)
    if not strategy_error:
        return
    payload = loop_strategy_source_recovery_payload(
        action=action,
        validation_error=strategy_error,
    )
    if json_output:
        echo_json(payload)
    else:
        _print_loop_strategy_source_recovery(payload)
    raise typer.Exit(code=1)


def loop_strategy_source_recovery_payload(*, action: str, validation_error: str) -> dict[str, object]:
    next_actions = [
        {"kind": "repair_strategy_source", "validation_error": validation_error},
        {"kind": "choose_strategy_source"},
        {"kind": "choose_workflow_preset"},
        {"kind": _loop_retry_action_kind(action)},
    ]
    summary = (
        "The selected Strategy Source file is unavailable; repair it, choose another Strategy Source file, "
        "or use a built-in workflow preset before composing a Loop."
    )
    return {
        "loop_strategy_source_recovery_summary": {
            "ready": False,
            "loop_recovery": "target_strategy_source_unavailable",
            "status": "blocked_by_strategy_source_file",
            "surface": "cli_loop_command",
            "action": action,
            "next_action_kinds": _loop_action_kinds(next_actions),
        },
        "loop_recovery": "target_strategy_source_unavailable",
        "status": "blocked_by_strategy_source_file",
        "surface": "cli_loop_command",
        "action": action,
        "strategy_source_state": {
            "status": "unavailable",
            "error": validation_error,
        },
        "summary": summary,
        "error": summary,
        "next_actions": next_actions,
    }


def loop_spec_recovery_payload(
    *,
    spec: Path | str | None,
    action: str,
    retry_command: str,
    retry_command_template: str = "",
    strategy_context: SpecInitStrategyContext | None = None,
) -> dict[str, object]:
    state = loop_spec_state(
        spec,
        strategy_context=strategy_context,
    )
    state = dict(state)
    summary = _loop_spec_summary(str(state["status"]), state=state)
    state["summary"] = summary
    next_actions = _loop_spec_next_actions(
        state,
        action=action,
        retry_command=retry_command,
        retry_command_template=retry_command_template,
    )
    payload = {
        "loop_spec_recovery_summary": {
            "ready": False,
            "loop_recovery": "target_spec_unavailable",
            "status": "blocked_by_spec",
            "surface": "cli_loop_command",
            "action": action,
            "spec_path": state["spec_path"],
            "spec_state_status": str(state.get("status") or ""),
            "next_action_kinds": _loop_action_kinds(next_actions),
        },
        "loop_recovery": "target_spec_unavailable",
        "status": "blocked_by_spec",
        "surface": "cli_loop_command",
        "action": action,
        "spec_path": state["spec_path"],
        "spec_state": state,
        "summary": summary,
        "error": summary,
        "next_actions": next_actions,
    }
    _project_loop_spec_action_contract(payload)
    return payload


def _project_loop_spec_action_contract(payload: dict[str, object]) -> None:
    actions = [action for action in list(payload.get("next_actions") or []) if isinstance(action, dict)]
    action_kinds = _loop_action_kinds(actions)
    payload["next_action_kinds"] = action_kinds
    readiness = first_use_action_readiness_summary(actions)
    project_first_use_action_readiness_summary(payload, prefix="next_action", readiness=readiness)
    summary = payload.get("loop_spec_recovery_summary")
    if isinstance(summary, dict):
        summary["next_action_kinds"] = list(action_kinds)
        project_first_use_action_readiness_summary(summary, prefix="next_action", readiness=readiness)


def _loop_action_kinds(actions: list[dict[str, object]]) -> list[str]:
    return [str(action.get("kind") or "").strip() for action in actions if str(action.get("kind") or "").strip()]


def loop_spec_state(
    spec: Path | str | None,
    *,
    strategy_context: SpecInitStrategyContext | None = None,
) -> dict[str, object]:
    state = spec_path_state(spec)
    strategy_error = spec_init_strategy_source_error(strategy_context=strategy_context)
    if strategy_error:
        state["strategy_source_state"] = {
            "status": "unavailable",
            "error": strategy_error,
        }
    if state["status"] == "missing":
        path = str(state["spec_path"])
        init_command = "" if strategy_error else spec_init_recovery_command(path, strategy_context=strategy_context)
        if init_command:
            state["commands"] = {"init": init_command}
    elif state["status"] == "required":
        init_template = "" if strategy_error else spec_init_recovery_command_template(strategy_context=strategy_context)
        if init_template:
            state["commands"] = {"init_template": init_template}
    return state


def _loop_spec_summary(status: str, *, state: dict[str, object] | None = None) -> str:
    strategy_state = state.get("strategy_source_state") if isinstance(state, dict) else {}
    strategy_error = str(strategy_state.get("error") or "").strip() if isinstance(strategy_state, dict) else ""
    if strategy_error and status in {"required", "missing"}:
        return (
            "Spec creation needs the selected Strategy Source file, but that file is unavailable; "
            "repair the Strategy Source file or choose an existing Markdown spec before composing a Loop."
        )
    if status == "required":
        return "Spec path is required; choose an existing Markdown spec before composing a Loop."
    if status == "missing":
        return "Spec file does not exist yet; create a starter spec or choose an existing Markdown spec before composing a Loop."
    if status == "not_file":
        return "Spec path exists but is not a file; choose an existing Markdown spec before composing a Loop."
    if status == "unavailable":
        return "Spec path cannot be inspected; choose a readable Markdown spec before composing a Loop."
    return ""


def _loop_spec_next_actions(
    state: dict[str, object],
    *,
    action: str,
    retry_command: str,
    retry_command_template: str = "",
) -> list[dict[str, str]]:
    commands = state.get("commands") if isinstance(state.get("commands"), dict) else {}
    init_command = str(commands.get("init") or "")
    init_template = str(commands.get("init_template") or "")
    actions: list[dict[str, str]] = []
    retry_action = {"kind": _loop_retry_action_kind(action)}
    strategy_state = state.get("strategy_source_state") if isinstance(state.get("strategy_source_state"), dict) else {}
    strategy_error = str(strategy_state.get("error") or "").strip()
    if strategy_error:
        actions.append({"kind": "repair_strategy_source", "validation_error": strategy_error})
        actions.append({"kind": "choose_spec"})
        retry_action["after_action"] = "repair_strategy_source"
        actions.append(retry_action)
        return actions
    if init_command:
        actions.append({"kind": "create_spec", "command": init_command})
        if retry_command:
            retry_action["command"] = copyable_loopora_command(retry_command)
        retry_action["after_action"] = "create_spec"
        actions.append(retry_action)
        actions.append({"kind": "choose_spec"})
        return actions
    if init_template:
        actions.append({"kind": "create_spec", "command_template": init_template})
        if retry_command_template:
            retry_action["command_template"] = copyable_loopora_command(retry_command_template)
        retry_action["after_action"] = "create_spec"
        actions.append(retry_action)
        actions.append({"kind": "choose_spec"})
        return actions
    actions.append({"kind": "choose_spec"})
    retry_action["after_action"] = "choose_spec"
    actions.append(retry_action)
    return actions


def _loop_retry_action_kind(action: str) -> str:
    return {
        "create": "retry_loop_create",
        "run": "retry_loop_run",
    }.get(action, "retry_loop_command")


def _print_loop_spec_recovery(payload: dict[str, object]) -> None:
    action = str(payload.get("action") or "create")
    spec_state = payload.get("spec_state") if isinstance(payload.get("spec_state"), dict) else {}
    typer.echo(f"Loopora Loop {action} is blocked")
    typer.echo(f"spec: {payload.get('spec_path')}")
    typer.echo(f"spec_state: {spec_state.get('status')}")
    summary = str(payload.get("summary") or "").strip()
    if summary:
        typer.echo(f"note: {summary}")
    typer.echo("next:")
    for item in payload.get("next_actions") or []:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "")
        command = str(item.get("command") or "").strip()
        command_template = str(item.get("command_template") or "").strip()
        label = {
            "create_spec": "Create a starter spec",
            "repair_strategy_source": "Repair the selected Strategy Source file",
            "choose_spec": "Choose an existing Markdown spec",
            "retry_loop_create": "Retry the Loop command after the spec exists",
            "retry_loop_run": "Retry the Loop command after the spec exists",
            "retry_loop_command": "Retry the Loop command after the spec exists",
        }.get(kind, kind)
        detail = command or command_template
        if not detail and kind == "repair_strategy_source":
            detail = str(item.get("validation_error") or "").strip()
        typer.echo(f"- {label}: {detail}" if detail else f"- {label}")


def _print_loop_strategy_source_recovery(payload: dict[str, object]) -> None:
    action = str(payload.get("action") or "create")
    strategy_state = payload.get("strategy_source_state") if isinstance(payload.get("strategy_source_state"), dict) else {}
    typer.echo(f"Loopora Loop {action} is blocked")
    typer.echo("strategy_source_state: unavailable")
    summary = str(payload.get("summary") or "").strip()
    if summary:
        typer.echo(f"note: {summary}")
    typer.echo("next:")
    for item in payload.get("next_actions") or []:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "")
        label = {
            "repair_strategy_source": "Repair the selected Strategy Source file",
            "choose_strategy_source": "Choose another Strategy Source file",
            "choose_workflow_preset": "Use a built-in workflow preset",
            "retry_loop_create": "Retry the Loop command after the Strategy Source is usable",
            "retry_loop_run": "Retry the Loop command after the Strategy Source is usable",
            "retry_loop_command": "Retry the Loop command after the Strategy Source is usable",
        }.get(kind, kind)
        detail = str(item.get("validation_error") or "").strip() if kind == "repair_strategy_source" else ""
        if kind == "repair_strategy_source" and not detail:
            detail = str(strategy_state.get("error") or "").strip()
        typer.echo(f"- {label}: {detail}" if detail else f"- {label}")
