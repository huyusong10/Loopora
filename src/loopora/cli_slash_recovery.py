from __future__ import annotations

import click
from pathlib import Path

import typer

from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.agent_adapter_workdir_recovery import adapter_workdir_state
from loopora.agent_adapters import (
    adapter_first_task_handoff_policy,
    adapter_first_task_message_example,
    adapter_first_task_message_example_state,
)
from loopora.cli_adapter_recovery import (
    _append_adapter_choice_lines,
    _command_recovery_wants_json,
    _command_recovery_workdir,
    _recovery_plain_label,
    _unsupported_agent_adapter_choices,
    _unsupported_agent_adapter_create_action,
    _unsupported_agent_adapter_workdir_arg,
)
from loopora.cli_common import echo_json
from loopora.cli_first_task_handoff import first_task_handoff_lines
from loopora.first_use_action_readiness import (
    first_use_action_readiness_summary,
    project_first_use_action_readiness_summary,
)
from loopora.first_use_web_guidance import web_creation_path_note


class SlashCommandRecovery(click.Command):
    def __init__(self, slash_command: str):
        super().__init__(
            slash_command,
            context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
        )
        self.slash_command = slash_command

    def get_help(self, ctx):
        workdir = _command_recovery_workdir(ctx)
        return _slash_command_recovery_message(self.slash_command, workdir=workdir)

    def invoke(self, ctx):
        workdir = _command_recovery_workdir(ctx)
        if _slash_recovery_wants_json(ctx):
            echo_json(_slash_command_recovery_json_payload(self.slash_command, workdir=workdir))
        else:
            typer.echo(_slash_command_recovery_message(self.slash_command, workdir=workdir))
        raise typer.Exit(code=2)


def _normalized_slash_recovery_command(command: str) -> str:
    normalized = str(command or "").strip()
    if normalized.startswith("/"):
        return normalized
    if normalized in {"loopora-plan", "loopora-run", "next"}:
        return f"/{normalized}"
    return ""


def _slash_recovery_wants_json(ctx) -> bool:
    return _command_recovery_wants_json(ctx)


def _slash_command_recovery_json_payload(slash_command: str, *, workdir: Path | None = None) -> dict:
    payload = _slash_command_recovery_payload(slash_command, workdir=workdir)
    payload["next_actions"] = _slash_command_recovery_next_actions(payload)
    _project_slash_command_recovery_action_contract(payload)
    return {"slash_command_recovery_summary": _slash_command_recovery_summary(payload), **payload}


def _slash_command_recovery_summary(payload: dict) -> dict:
    readiness_keys = {
        "next_action_kinds",
        "next_action_ready_kinds",
        "next_action_ready_now_kinds",
        "next_action_ready_after_actions",
        "next_action_blocked_kinds",
        "next_action_command_blockers",
    }
    summary_keys = [
        "ready",
        "slash_command_recovery",
        "slash_command",
        "agent_command",
        "shell_subcommand",
        "next_step",
        "check_fit_first",
        "web_creation_path",
        "web_creation_path_note",
        "install_first",
        "install_first_adapter_choices",
        "if_missing_in_agent",
        "if_missing_in_agent_adapter_choices",
        "readiness_check",
        "plan_first",
        "create_workdir",
        "choose_workdir",
        "workdir",
        "workdir_state",
        "first_task_message_example_state",
        "first_task_handoff_policy",
        "debug_cli",
        "debug_cli_adapter_choices",
        "next_action_kinds",
        "next_action_ready_kinds",
        "next_action_ready_now_kinds",
        "next_action_ready_after_actions",
        "next_action_blocked_kinds",
        "next_action_command_blockers",
    ]
    summary = {key: payload[key] for key in summary_keys if key in payload and (key in readiness_keys or payload[key] not in ("", [], {}))}
    actions = payload.get("next_actions") if isinstance(payload.get("next_actions"), list) else []
    summary["next_action_kinds"] = [
        str(action.get("kind") or "").strip() for action in actions if isinstance(action, dict) and str(action.get("kind") or "").strip()
    ]
    return summary


def _project_slash_command_recovery_action_contract(payload: dict[str, object]) -> None:
    actions = [action for action in list(payload.get("next_actions") or []) if isinstance(action, dict)]
    payload["next_action_kinds"] = [str(action.get("kind") or "").strip() for action in actions if str(action.get("kind") or "").strip()]
    readiness = first_use_action_readiness_summary(actions)
    project_first_use_action_readiness_summary(payload, prefix="next_action", readiness=readiness)


def _slash_command_recovery_next_actions(payload: dict) -> list[dict[str, object]]:
    actions: list[dict[str, object]] = []
    for key, value_field in (
        ("create_workdir", "command"),
        ("choose_workdir", "note"),
        ("check_fit_first", "command"),
        ("web_creation_path", "command"),
        ("install_first", "command"),
        ("if_missing_in_agent", "command"),
        ("readiness_check", "command"),
        ("plan_first", "note"),
        ("next_step", "note"),
        ("debug_cli", "command"),
    ):
        value = str(payload.get(key) or "").strip()
        choices = payload.get(f"{key}_adapter_choices")
        if not value and not choices:
            continue
        action: dict[str, object] = {"kind": key}
        if value:
            action[value_field] = value
        note = str(payload.get(f"{key}_note") or "").strip()
        if note:
            action["note"] = note
        if isinstance(choices, list) and choices:
            action["selection_required"] = True
            action["adapter_choices"] = choices
        actions.append(action)
    return actions


def _slash_command_recovery_payload(slash_command: str, *, workdir: Path | None = None) -> dict:
    command = str(slash_command or "").strip()
    workdir_state = adapter_workdir_state(workdir) if workdir is not None else None
    commands = _slash_command_recovery_commands(workdir_state)
    fit_command = _slash_command_fit_command(workdir_state)
    if command == "/loopora-plan":
        payload = {
            "ready": False,
            "slash_command_recovery": "agent_slash_command_in_shell",
            "slash_command": "/loopora-plan",
            "agent_command": True,
            "shell_subcommand": False,
            "message": "/loopora-plan is an Agent slash command, not a shell subcommand.",
            "check_fit_first": fit_command,
            "next_step": (
                "return to that Agent with the Loopora fit reason, task goal, fake-done risk, required evidence, "
                "judgment tradeoffs, and optional direct-path context, "
                "then run /loopora-plan there."
            ),
            "first_task_message_example": adapter_first_task_message_example(),
            "first_task_message_example_state": adapter_first_task_message_example_state(),
            "first_task_handoff_policy": _slash_command_first_task_handoff_policy(workdir_state),
        }
        payload.update(_slash_command_plan_commands(commands))
        return _slash_command_recovery_with_workdir(payload, workdir_state)
    if command == "/loopora-run":
        payload = {
            "ready": False,
            "slash_command_recovery": "agent_slash_command_in_shell",
            "slash_command": "/loopora-run",
            "agent_command": True,
            "shell_subcommand": False,
            "message": "/loopora-run is an Agent slash command, not a shell subcommand.",
            "check_fit_first": fit_command,
            "plan_first": "run /loopora-plan inside the Agent and review the READY preview before /loopora-run",
            "next_step": "run /loopora-run inside the same Agent session that created or selected the READY Loop preview.",
        }
        payload.update(_slash_command_run_commands(commands))
        return _slash_command_recovery_with_workdir(payload, workdir_state)
    if command == "/next":
        payload = {
            "ready": False,
            "slash_command_recovery": "unsupported_loopora_slash_command",
            "slash_command": "/next",
            "agent_command": False,
            "shell_subcommand": False,
            "message": "Loopora does not install a top-level /next slash command.",
            "next_step": "use /loopora-run inside the Agent to start, resume, or continue the current Loop.",
        }
        payload.update(_slash_command_next_commands(commands))
        return _slash_command_recovery_with_workdir(payload, workdir_state)
    payload = {
        "ready": False,
        "slash_command_recovery": "unknown_loopora_shell_subcommand",
        "slash_command": command,
        "agent_command": False,
        "shell_subcommand": False,
        "message": f"{command} is not a Loopora shell subcommand.",
        "known_agent_commands": ["/loopora-plan", "/loopora-run"],
        "check_fit_first": fit_command,
        "first_task_message_example": adapter_first_task_message_example(),
        "first_task_message_example_state": adapter_first_task_message_example_state(),
        "first_task_handoff_policy": _slash_command_first_task_handoff_policy(workdir_state),
        "next_step": "run Loopora slash commands inside the Coding Agent, not in the shell.",
    }
    payload.update(_slash_command_plan_commands(commands))
    return _slash_command_recovery_with_workdir(payload, workdir_state)


def _slash_command_recovery_commands(workdir_state: dict[str, object] | None) -> dict[str, object]:
    if workdir_state is not None and workdir_state.get("status") not in {"ready", "missing"}:
        return {
            "choose_workdir": "Choose an existing project directory before managing Agent entries.",
        }
    workdir_arg = _unsupported_agent_adapter_workdir_arg(workdir_state)
    commands = {
        "web_creation_path": copyable_loopora_command(f"loopora serve --open --workdir {workdir_arg} --host 127.0.0.1 --port 8742"),
        "web_creation_path_note": web_creation_path_note(),
        "install_first": copyable_loopora_command(f"loopora init --workdir {workdir_arg}"),
        "install_first_adapter_choices": _unsupported_agent_adapter_choices("init", workdir_arg),
        "if_missing_in_agent": copyable_loopora_command(f"loopora agent --workdir {workdir_arg}"),
        "if_missing_in_agent_adapter_choices": _unsupported_agent_adapter_choices("check", workdir_arg),
        "readiness_check": copyable_loopora_command(f"loopora doctor --workdir {workdir_arg}"),
        "debug_cli": copyable_loopora_command(f"loopora agent --workdir {workdir_arg}"),
        "debug_cli_adapter_choices": _unsupported_agent_adapter_choices("check", workdir_arg),
        "run_debug_cli": copyable_loopora_command(f"loopora agent --workdir {workdir_arg}"),
        "run_debug_cli_adapter_choices": _unsupported_agent_adapter_choices("check", workdir_arg),
        "next_debug_cli": copyable_loopora_command(f"loopora agent --workdir {workdir_arg}"),
        "next_debug_cli_adapter_choices": _unsupported_agent_adapter_choices("check", workdir_arg),
    }
    create_action = _unsupported_agent_adapter_create_action(workdir_state)
    if create_action:
        commands["create_workdir"] = str(create_action.get("command") or "")
    return commands


def _slash_command_fit_command(workdir_state: dict[str, object] | None) -> str:
    if workdir_state is not None and workdir_state.get("status") not in {"ready", "missing"}:
        return copyable_loopora_command("loopora fit")
    return copyable_loopora_command(f"loopora fit --workdir {_unsupported_agent_adapter_workdir_arg(workdir_state)}")


def _slash_command_first_task_handoff_policy(workdir_state: dict[str, object] | None) -> dict[str, str]:
    return adapter_first_task_handoff_policy(fit_command=_slash_command_fit_command(workdir_state))


def _slash_command_plan_commands(commands: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in commands.items()
        if key not in {"run_debug_cli", "run_debug_cli_adapter_choices", "next_debug_cli", "next_debug_cli_adapter_choices"}
    }


def _slash_command_run_commands(commands: dict[str, object]) -> dict[str, object]:
    run_commands = {
        key: value
        for key, value in commands.items()
        if key
        not in {
            "debug_cli",
            "debug_cli_adapter_choices",
            "run_debug_cli",
            "run_debug_cli_adapter_choices",
            "next_debug_cli",
            "next_debug_cli_adapter_choices",
        }
    }
    if "run_debug_cli" in commands:
        run_commands["debug_cli"] = commands["run_debug_cli"]
    if "run_debug_cli_adapter_choices" in commands:
        run_commands["debug_cli_adapter_choices"] = commands["run_debug_cli_adapter_choices"]
    return run_commands


def _slash_command_next_commands(commands: dict[str, object]) -> dict[str, object]:
    next_commands = {key: value for key, value in commands.items() if key in {"create_workdir", "choose_workdir"}}
    if "next_debug_cli" in commands:
        next_commands["debug_cli"] = commands["next_debug_cli"]
    if "next_debug_cli_adapter_choices" in commands:
        next_commands["debug_cli_adapter_choices"] = commands["next_debug_cli_adapter_choices"]
    return next_commands


def _slash_command_recovery_with_workdir(payload: dict, workdir_state: dict[str, object] | None) -> dict:
    if workdir_state is None:
        return payload
    payload["workdir"] = str(workdir_state.get("workdir") or "")
    payload["workdir_state"] = workdir_state
    return payload


def _slash_command_recovery_message(slash_command: str, *, workdir: Path | None = None) -> str:
    payload = _slash_command_recovery_payload(slash_command, workdir=workdir)
    lines = [f"slash command recovery: {payload['message']}"]
    known_agent_commands = payload.get("known_agent_commands")
    if isinstance(known_agent_commands, list) and known_agent_commands:
        lines.append("known Agent commands: " + ", ".join(str(item) for item in known_agent_commands))
    workdir_state = payload.get("workdir_state") if isinstance(payload.get("workdir_state"), dict) else None
    if workdir_state:
        lines.append(f"project directory: {payload.get('workdir')}")
        lines.append(f"project directory state: {workdir_state.get('status')}")
        summary = str(workdir_state.get("summary") or "").strip()
        if summary:
            lines.append(f"note: {summary}")
    for key in (
        "check_fit_first",
        "create_workdir",
        "choose_workdir",
        "web_creation_path",
        "install_first",
        "if_missing_in_agent",
        "readiness_check",
        "plan_first",
        "next_step",
        "first_task_message_example",
        "debug_cli",
    ):
        value = str(payload.get(key) or "").strip()
        choices = payload.get(f"{key}_adapter_choices")
        if _append_adapter_choice_lines(lines, f"{_recovery_plain_label(key)}:", choices, indent=""):
            continue
        if value:
            if key == "first_task_message_example":
                lines.extend(first_task_handoff_lines(payload, example=value))
                continue
            note = str(payload.get(f"{key}_note") or "").strip()
            suffix = f" ({note})" if note else ""
            lines.append(f"{_recovery_plain_label(key)}: {value}{suffix}")
    return "\n".join(lines)
