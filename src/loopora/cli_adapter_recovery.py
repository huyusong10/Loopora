from __future__ import annotations

import click
from pathlib import Path
import shlex

import typer

from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.agent_adapter_workdir_recovery import adapter_workdir_state
from loopora.agent_native_adapter_contracts import AGENT_ADAPTER_KINDS, normalize_agent_adapter_kind
from loopora.cli_common import echo_json
from loopora.first_use_action_readiness import (
    first_use_action_readiness_summary,
    project_first_use_action_readiness_summary,
)
from loopora.service_types import LooporaError


class UnsupportedAgentAdapterCommand(click.Command):
    def __init__(self, adapter: str, *, command_group: str):
        super().__init__(
            adapter,
            context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
        )
        self.adapter = adapter
        self.command_group = command_group

    def get_help(self, ctx):
        workdir = _command_recovery_workdir(ctx)
        return _unsupported_agent_adapter_message(self.adapter, command_group=self.command_group, workdir=workdir)

    def invoke(self, ctx):
        workdir = _command_recovery_workdir(ctx)
        payload = _unsupported_agent_adapter_payload(self.adapter, command_group=self.command_group, workdir=workdir)
        if _command_recovery_wants_json(ctx):
            echo_json({"unsupported_agent_adapter_summary": _unsupported_agent_adapter_summary(payload), **payload})
        else:
            typer.echo(_unsupported_agent_adapter_message(self.adapter, command_group=self.command_group, workdir=workdir))
        raise typer.Exit(code=2)


def _normalized_adapter_alias(adapter: str) -> str:
    try:
        return normalize_agent_adapter_kind(adapter)
    except LooporaError:
        return ""


def _command_recovery_wants_json(ctx) -> bool:
    return any(str(arg or "").strip() == "--json" for arg in list(getattr(ctx, "args", []) or []))


def _command_recovery_workdir(ctx) -> Path | None:
    parent = getattr(ctx, "parent", None)
    while parent is not None:
        parent_workdir = (getattr(parent, "params", {}) or {}).get("workdir")
        if parent_workdir is not None:
            return parent_workdir
        parent = getattr(parent, "parent", None)
    args = list(getattr(ctx, "args", []) or [])
    for index, raw_arg in enumerate(args):
        arg = str(raw_arg or "").strip()
        if arg == "--workdir" and index + 1 < len(args):
            return Path(str(args[index + 1]))
        if arg.startswith("--workdir="):
            return Path(arg.split("=", 1)[1])
    return None


def _unsupported_agent_adapter_summary(payload: dict) -> dict:
    summary_keys = [
        "ready",
        "status",
        "adapter",
        "command_group",
        "supported_adapters",
        "workdir",
        "workdir_state",
        "next_action_kinds",
        "next_action_ready_kinds",
        "next_action_ready_now_kinds",
        "next_action_ready_after_actions",
        "next_action_blocked_kinds",
        "next_action_command_blockers",
    ]
    summary = {key: payload[key] for key in summary_keys if key in payload}
    actions = payload.get("next_actions") if isinstance(payload.get("next_actions"), list) else []
    summary["next_action_kinds"] = _unsupported_agent_adapter_action_kinds(actions)
    readiness = first_use_action_readiness_summary([action for action in actions if isinstance(action, dict)])
    project_first_use_action_readiness_summary(summary, prefix="next_action", readiness=readiness)
    return summary


def _unsupported_agent_adapter_payload(adapter: str, *, command_group: str, workdir: Path | None = None) -> dict:
    supported = list(AGENT_ADAPTER_KINDS)
    workdir_state = adapter_workdir_state(workdir) if workdir is not None else None
    actions_by_group = _unsupported_agent_adapter_actions_by_group(workdir_state)
    payload = {
        "ready": False,
        "status": "unsupported_agent_adapter",
        "adapter": str(adapter or "").strip(),
        "command_group": command_group,
        "message": f"{adapter} is not a supported Loopora Agent adapter.",
        "supported_adapters": supported,
        "supported_aliases": {
            "openai-codex": "codex",
            "claude-code": "claude",
            "claudecode": "claude",
            "open-code": "opencode",
        },
        "next_actions": actions_by_group.get(command_group, actions_by_group["agent"]),
    }
    if workdir_state is not None:
        payload["workdir"] = str(workdir_state.get("workdir") or "")
        payload["workdir_state"] = workdir_state
    _project_unsupported_agent_adapter_action_contract(payload)
    return payload


def _unsupported_agent_adapter_actions_by_group(workdir_state: dict[str, object] | None) -> dict[str, list[dict[str, object]]]:
    workdir_arg = _unsupported_agent_adapter_workdir_arg(workdir_state)
    if workdir_state is not None and workdir_state.get("status") not in {"ready", "missing"}:
        return _unsupported_agent_adapter_choose_actions(workdir_arg)
    supported_note = "Choose codex, claude, or opencode to match your current Agent host."
    support_action = _unsupported_agent_adapter_support_action(workdir_arg)
    install_action = {
        "kind": "install_supported_agent_entry",
        "selection_required": True,
        "adapter_choices": _unsupported_agent_adapter_choices("init", workdir_arg),
        "note": supported_note,
    }
    check_action = {
        "kind": "check_supported_agent_entry",
        "selection_required": True,
        "adapter_choices": _unsupported_agent_adapter_choices("check", workdir_arg),
        "note": supported_note,
    }
    actions_by_group = {
        "init": [
            {"kind": "check_fit_first", "command": copyable_loopora_command(f"loopora fit --workdir {workdir_arg}")},
            install_action,
            {"kind": "confirm_readiness", "command": copyable_loopora_command(f"loopora doctor --workdir {workdir_arg}")},
            support_action,
        ],
        "uninstall": [
            {
                "kind": "choose_supported_agent_entry",
                "selection_required": True,
                "adapter_choices": _unsupported_agent_adapter_choices("uninstall", workdir_arg),
                "note": supported_note,
            },
            {
                "kind": "review_installed_entries",
                "command": copyable_loopora_command(f"loopora doctor --workdir {workdir_arg}"),
            },
            support_action,
        ],
        "agent": [
            check_action,
            install_action,
            {"kind": "confirm_readiness", "command": copyable_loopora_command(f"loopora doctor --workdir {workdir_arg}")},
            support_action,
        ],
    }
    create_action = _unsupported_agent_adapter_create_action(workdir_state)
    if create_action:
        return {group: [create_action, *_unsupported_agent_adapter_actions_after("create_workdir", actions)] for group, actions in actions_by_group.items()}
    return actions_by_group


def _project_unsupported_agent_adapter_action_contract(payload: dict[str, object]) -> None:
    actions = [action for action in list(payload.get("next_actions") or []) if isinstance(action, dict)]
    payload["next_action_kinds"] = _unsupported_agent_adapter_action_kinds(actions)
    readiness = first_use_action_readiness_summary(actions)
    project_first_use_action_readiness_summary(payload, prefix="next_action", readiness=readiness)


def _unsupported_agent_adapter_action_kinds(actions: object) -> list[str]:
    return [str(action.get("kind") or "").strip() for action in list(actions or []) if isinstance(action, dict) and str(action.get("kind") or "").strip()]


def _unsupported_agent_adapter_actions_after(
    prerequisite_kind: str,
    actions: list[dict[str, object]],
) -> list[dict[str, object]]:
    gated_actions: list[dict[str, object]] = []
    for action in actions:
        action_copy = dict(action)
        kind = str(action_copy.get("kind") or "").strip()
        if kind and kind != "support" and not action_copy.get("after_action"):
            action_copy["after_action"] = prerequisite_kind
        gated_actions.append(action_copy)
    return gated_actions


def _unsupported_agent_adapter_choices(action: str, workdir_arg: str) -> list[dict[str, str]]:
    commands = {
        "init": "loopora init {adapter} --workdir {workdir_arg}",
        "check": "loopora agent {adapter} check --workdir {workdir_arg}",
        "uninstall": "loopora uninstall {adapter} --workdir {workdir_arg}",
    }
    template = commands[action]
    return [
        {
            "adapter": adapter,
            "command": copyable_loopora_command(template.format(adapter=adapter, workdir_arg=workdir_arg)),
        }
        for adapter in AGENT_ADAPTER_KINDS
    ]


def _unsupported_agent_adapter_workdir_arg(workdir_state: dict[str, object] | None) -> str:
    if workdir_state is None:
        return '"$PWD"'
    return shlex.quote(str(workdir_state.get("workdir") or ""))


def _unsupported_agent_adapter_create_action(workdir_state: dict[str, object] | None) -> dict[str, str] | None:
    if workdir_state is None or workdir_state.get("status") != "missing":
        return None
    commands = workdir_state.get("commands") if isinstance(workdir_state.get("commands"), dict) else {}
    create_command = str(commands.get("create") or "").strip()
    return {"kind": "create_workdir", "command": create_command} if create_command else None


def _unsupported_agent_adapter_support_action(workdir_arg: str) -> dict[str, str]:
    return {
        "kind": "support",
        "command": copyable_loopora_command(f"loopora support --workdir {workdir_arg}"),
    }


def _append_adapter_choice_lines(lines: list[str], heading: str, choices: object, *, indent: str) -> bool:
    if not isinstance(choices, list) or not choices:
        return False
    lines.append(heading)
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        adapter_choice = str(choice.get("adapter") or "").strip()
        choice_command = str(choice.get("command") or "").strip()
        if adapter_choice and choice_command:
            lines.append(f"{indent}- {adapter_choice}: {choice_command}")
    return True


def _recovery_plain_label(key: object) -> str:
    labels = {
        "check_fit_first": "check fit first",
        "install_supported_agent_entry": "install supported same-Agent project entry",
        "check_supported_agent_entry": "check supported same-Agent project entry",
        "choose_supported_agent_entry": "choose supported same-Agent project entry",
        "review_installed_entries": "review installed entries",
        "confirm_readiness": "confirm readiness",
        "create_workdir": "create project directory",
        "choose_workdir": "choose project directory",
        "web_creation_path": "Fit Guide/Web choices",
        "install_first": "install first",
        "if_missing_in_agent": "choose or check same-Agent project entry, then refresh or restart that Agent if missing",
        "readiness_check": "readiness check",
        "plan_first": "plan first",
        "next_step": "next step",
        "debug_cli": "debug CLI",
        "support": "Usage/setup help",
    }
    raw = str(key or "").strip()
    return labels.get(raw, raw.replace("_", " "))


def _unsupported_agent_adapter_choose_actions(workdir_arg: str) -> dict[str, list[dict[str, str]]]:
    supported_note = "Choose codex, claude, or opencode to match your current Agent host."
    support_action = _unsupported_agent_adapter_support_action(workdir_arg)
    return {
        "init": [
            {"kind": "choose_workdir", "note": "Choose an existing project directory before installing a same-Agent project entry."},
            {"kind": "choose_supported_agent_entry", "note": supported_note, "after_action": "choose_workdir"},
            support_action,
        ],
        "uninstall": [
            {"kind": "choose_workdir", "note": "Choose an existing project directory before uninstalling a same-Agent project entry."},
            {"kind": "choose_supported_agent_entry", "note": supported_note, "after_action": "choose_workdir"},
            support_action,
        ],
        "agent": [
            {"kind": "choose_workdir", "note": "Choose an existing project directory before checking a same-Agent project entry."},
            {"kind": "choose_supported_agent_entry", "note": supported_note, "after_action": "choose_workdir"},
            support_action,
        ],
    }


def _unsupported_agent_adapter_message(adapter: str, *, command_group: str, workdir: Path | None = None) -> str:
    payload = _unsupported_agent_adapter_payload(adapter, command_group=command_group, workdir=workdir)
    lines = [
        f"unsupported Agent adapter: {payload['message']}",
        "supported Agent adapters: " + ", ".join(str(item) for item in payload["supported_adapters"]),
        "supported aliases: openai-codex -> codex, claude-code -> claude, claudecode -> claude, open-code -> opencode",
    ]
    workdir_state = payload.get("workdir_state") if isinstance(payload.get("workdir_state"), dict) else None
    if workdir_state:
        lines.append(f"project directory: {payload.get('workdir')}")
        lines.append(f"project directory state: {workdir_state.get('status')}")
        summary = str(workdir_state.get("summary") or "").strip()
        if summary:
            lines.append(f"note: {summary}")
    lines.append("next:")
    for item in payload["next_actions"]:
        if not isinstance(item, dict):
            continue
        command = str(item.get("command") or "").strip()
        note = str(item.get("note") or "").strip()
        suffix = f" ({note})" if note else ""
        label = _unsupported_agent_adapter_plain_label(item.get("kind"))
        choices = item.get("adapter_choices")
        if _append_adapter_choice_lines(lines, f"- {label}{suffix}", choices, indent="  "):
            continue
        lines.append(f"- {label}: {command}{suffix}" if command else f"- {label}{suffix}")
    return "\n".join(lines)


def _unsupported_agent_adapter_plain_label(key: object) -> str:
    labels = {
        "check_fit_first": "Check fit first",
        "install_supported_agent_entry": "Install supported same-Agent project entry",
        "check_supported_agent_entry": "Check supported same-Agent project entry",
        "choose_supported_agent_entry": "Choose supported same-Agent project entry",
        "review_installed_entries": "Review installed entries",
        "confirm_readiness": "Confirm readiness",
        "create_workdir": "Create target project directory",
        "choose_workdir": "Choose project directory",
        "support": "Usage/setup help",
    }
    raw = str(key or "").strip()
    return labels.get(raw, _recovery_plain_label(raw))
