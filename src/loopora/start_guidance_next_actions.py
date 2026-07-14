from __future__ import annotations

from collections.abc import Mapping
import shlex

from loopora.agent_adapter_command_prefix import DEFAULT_LOOPORA_CLI_ENTRY
from loopora.start_guidance_actions import (
    _action_by_kind,
    _actions,
    _copy_route_action,
    _rewrite,
    _start_support_command,
)
from loopora.fit_review_guidance import FIT_FIRST_TASK_MESSAGE_STATUS
from loopora.start_guidance_constants import START_REVIEW_INPUT_OPTIONS


def _truthy_review_input(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _start_next_actions(
    fit_payload: Mapping[str, object],
    *,
    route_actions: list[dict[str, object]],
    action_state: Mapping[str, object],
    workdir_state: Mapping[str, object],
    language: str,
) -> list[dict[str, object]]:
    task_review_supplied = bool(action_state.get("task_review_supplied"))
    fit_setup_allowed = bool(action_state.get("fit_setup_allowed"))
    route_commands_are_placeholders = bool(action_state.get("route_commands_are_placeholders"))
    cli_entry = str(action_state.get("cli_entry") or DEFAULT_LOOPORA_CLI_ENTRY)
    review_inputs = action_state.get("review_inputs") if isinstance(action_state.get("review_inputs"), Mapping) else {}
    web_route = action_state.get("web_route") if isinstance(action_state.get("web_route"), Mapping) else {}
    if task_review_supplied and not fit_setup_allowed:
        fit_actions = _actions(fit_payload, "next_actions")
        if _payload_prefers_direct(fit_payload) or _payload_needs_direct_decision_input(fit_payload):
            return _start_fit_actions_with_read_only_support(
                fit_actions,
                workdir_state=workdir_state,
                language=language,
                cli_entry=cli_entry,
                web_route=web_route,
            )
        if workdir_state and str(workdir_state.get("status") or "") == "ready":
            return _start_fit_actions_with_route_support(fit_actions, route_actions)
        return _start_combined_blocker_actions(
            fit_actions,
            workdir_state,
            recovery_context={
                "route_actions": route_actions,
                "language": language,
                "cli_entry": cli_entry,
                "review_inputs": review_inputs,
                "include_confirm": not route_commands_are_placeholders,
            },
        )
    if not workdir_state or str(workdir_state.get("status") or "") == "ready":
        if route_commands_are_placeholders:
            actions: list[dict[str, object]] = []
            if not task_review_supplied:
                actions.append(_copy_route_action(_action_by_kind(route_actions, "check_fit_first")))
            actions.append(
                _start_choose_workdir_action(
                    workdir_state,
                    language=language,
                    cli_entry=cli_entry,
                    review_inputs=review_inputs,
                )
            )
            if not workdir_state:
                actions.append(_start_generic_support_action(language=language, cli_entry=cli_entry))
            return [action for action in actions if action]
        fit_actions = _actions(fit_payload, "next_actions") if not task_review_supplied else []
        return (
            [_copy_route_action(action) for action in fit_actions]
            if fit_actions
            else _start_ready_route_actions(route_actions, include_fit_check=not task_review_supplied)
        )
    actions: list[dict[str, object]] = []
    if not task_review_supplied:
        actions.append(_copy_route_action(_action_by_kind(route_actions, "check_fit_first")))
    actions.extend(
        _start_workdir_recovery_actions(
            workdir_state,
            route_actions=route_actions,
            recovery_context={"language": language, "cli_entry": cli_entry, "review_inputs": review_inputs},
            include_confirm=not route_commands_are_placeholders,
        )
    )
    return [action for action in actions if action]


def _payload_prefers_direct(payload: Mapping[str, object]) -> bool:
    state = payload.get("primary_first_task_message_state")
    return isinstance(state, Mapping) and str(state.get("status") or "") == FIT_FIRST_TASK_MESSAGE_STATUS["direct"]


def _payload_needs_direct_decision_input(payload: Mapping[str, object]) -> bool:
    state = payload.get("primary_first_task_message_state")
    return isinstance(state, Mapping) and str(state.get("status") or "") == FIT_FIRST_TASK_MESSAGE_STATUS["direct_input"]


def _start_fit_actions_with_route_support(
    fit_actions: list[dict[str, object]],
    route_actions: list[dict[str, object]],
) -> list[dict[str, object]]:
    support_action = _action_by_kind(route_actions, "support")
    if not support_action:
        return fit_actions
    return [
        _copy_route_action(support_action) if str(action.get("kind") or "").strip() == "support" else action
        for action in fit_actions
    ]


def _start_fit_actions_with_read_only_support(
    fit_actions: list[dict[str, object]],
    *,
    workdir_state: Mapping[str, object],
    language: str,
    cli_entry: str,
    web_route: Mapping[str, object],
) -> list[dict[str, object]]:
    if not workdir_state:
        return fit_actions
    support_action = _start_support_recovery_action(
        workdir_state,
        language=language,
        cli_entry=cli_entry,
        web_route=web_route,
    )
    actions: list[dict[str, object]] = []
    replaced = False
    for action in fit_actions:
        if str(action.get("kind") or "").strip() == "support":
            actions.append(support_action)
            replaced = True
        else:
            actions.append(action)
    return actions if replaced else [*actions, support_action]


def _start_ready_route_actions(
    route_actions: list[dict[str, object]],
    *,
    include_fit_check: bool,
) -> list[dict[str, object]]:
    return [
        _copy_route_action(action)
        for action in route_actions
        if include_fit_check or str(action.get("kind") or "") != "check_fit_first"
    ]


def _start_combined_blocker_actions(
    fit_actions: list[dict[str, object]],
    workdir_state: Mapping[str, object],
    *,
    recovery_context: Mapping[str, object],
) -> list[dict[str, object]]:
    actions: list[dict[str, object]] = []
    continue_actions: list[dict[str, object]] = []
    for action in fit_actions:
        target = continue_actions if str(action.get("kind") or "") == "continue_if_strong_fit" else actions
        target.append(_copy_route_action(action))
    existing_kinds = {str(action.get("kind") or "") for action in actions}
    route_actions = [action for action in list(recovery_context.get("route_actions") or []) if isinstance(action, dict)]
    actions.extend(
        action
        for action in _start_workdir_recovery_actions(
            workdir_state,
            route_actions=route_actions,
            recovery_context=recovery_context,
            include_confirm=bool(recovery_context.get("include_confirm", True)),
        )
        if str(action.get("kind") or "") not in existing_kinds
    )
    actions.extend(continue_actions)
    return [action for action in actions if action]


def _start_workdir_recovery_actions(
    workdir_state: Mapping[str, object],
    *,
    route_actions: list[dict[str, object]],
    recovery_context: Mapping[str, object],
    include_confirm: bool = True,
) -> list[dict[str, object]]:
    language = str(recovery_context.get("language") or "en")
    cli_entry = str(recovery_context.get("cli_entry") or DEFAULT_LOOPORA_CLI_ENTRY)
    review_inputs = recovery_context.get("review_inputs") if isinstance(recovery_context.get("review_inputs"), Mapping) else {}
    commands = workdir_state.get("commands") if isinstance(workdir_state.get("commands"), Mapping) else {}
    create_command = str(commands.get("create") or "").strip()
    first_action = (
        {"kind": "create_workdir", "command": create_command}
        if create_command
        else _start_choose_workdir_action(
            workdir_state,
            language=language,
            cli_entry=cli_entry,
            review_inputs=review_inputs,
        )
    )
    support_action = (
        _start_support_recovery_action(workdir_state, language=language, cli_entry=cli_entry)
        if workdir_state
        else _start_generic_support_action(language=language, cli_entry=cli_entry)
    )
    if not include_confirm:
        return [action for action in (first_action, support_action) if action]
    confirm_action = _copy_route_action(_action_by_kind(route_actions, "confirm_readiness"))
    confirm_action["after_action"] = str(first_action.get("kind") or "")
    return [action for action in (first_action, confirm_action, support_action) if action]


def _start_support_recovery_action(
    workdir_state: Mapping[str, object],
    *,
    language: str,
    cli_entry: str,
    web_route: Mapping[str, object] | None = None,
) -> dict[str, object]:
    workdir = str(workdir_state.get("workdir") or "").strip()
    workdir_arg = shlex.quote(workdir) if workdir else '"$PWD"'
    command = _rewrite(
        _start_support_command(workdir_arg=workdir_arg, web_route=web_route or {}, language=language),
        cli_entry=cli_entry,
    )
    return {
        "kind": "support",
        "command": command,
        "command_ready": True,
        "command_blockers": [],
        "setup_independent": True,
        "local_only": True,
    }


def _start_generic_support_action(*, language: str, cli_entry: str) -> dict[str, object]:
    language_arg = "" if language == "en" else f" --language {shlex.quote(language)}"
    return {
        "kind": "support",
        "command": _rewrite(f"loopora support{language_arg}", cli_entry=cli_entry),
        "command_ready": True,
        "command_blockers": [],
        "setup_independent": True,
        "local_only": True,
    }


def _start_choose_workdir_action(
    workdir_state: Mapping[str, object],
    *,
    language: str,
    cli_entry: str,
    review_inputs: Mapping[str, object] | None = None,
) -> dict[str, object]:
    if language == "zh":
        note = {
            "required": "请先进入目标项目目录，再运行此命令获取路线命令。",
            "unavailable": "目标项目目录暂时无法检查；请改用可读取的项目目录。",
            "not_directory": "目标项目路径不是目录；请改用项目目录。",
        }.get(str(workdir_state.get("status") or ""), "请先进入目标项目目录，再运行此命令获取路线命令。")
    else:
        note = str(
            workdir_state.get("summary") or "Run from the target project directory before copying route commands."
        ).strip()
    command = _rewrite(_start_target_project_command(language, review_inputs=review_inputs), cli_entry=cli_entry)
    return {"kind": "choose_workdir", "command": command, "note": note, "command_ready": True, "command_blockers": []}


def _start_target_project_command(language: str, *, review_inputs: Mapping[str, object] | None = None) -> str:
    parts = ["loopora", "start"]
    if language != "en":
        parts.extend(["--language", shlex.quote(language)])
    parts.extend(["--workdir", '"$PWD"'])
    parts.extend(_start_supplied_review_option_args(review_inputs or {}))
    return " ".join(parts)


def _start_supplied_review_option_args(review_inputs: Mapping[str, object]) -> list[str]:
    parts = ["--prefer-direct"] if _truthy_review_input(review_inputs.get("prefer_direct")) else []
    for input_id, option in START_REVIEW_INPUT_OPTIONS:
        value = " ".join(str(review_inputs.get(input_id) or "").split())
        if value:
            parts.extend([f"--{option}", shlex.quote(value)])
    return parts
