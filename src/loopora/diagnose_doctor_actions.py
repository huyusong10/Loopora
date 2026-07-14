from __future__ import annotations

from pathlib import Path
import shlex
from typing import Any

from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.cli_recovery_archive_guidance import recovery_archive_action
from loopora.diagnose_doctor_web_state import (
    doctor_app_state_command as _app_state_command,
    doctor_web_option_args as _doctor_web_option_args,
    doctor_workdir_command as _workdir_command,
)


def doctor_next_action_items(
    root: Path,
    *,
    workdir_state: dict[str, Any],
    agent_entries: list[dict[str, Any]],
    app_state: dict[str, Any],
    web: dict[str, Any],
) -> list[dict[str, Any]]:
    ready_entries = [entry for entry in agent_entries if entry.get("ready") is True]
    if not ready_entries:
        return _doctor_actions_without_ready_entry(
            root,
            workdir_state=workdir_state,
            agent_entries=agent_entries,
            app_state=app_state,
            web=web,
        )
    archive_command = _app_state_command(app_state, "recovery_archive")
    reset_command = _app_state_command(app_state, "reset")
    app_archive_action = _app_archive_action(app_state, archive_command)
    app_reset_action = _app_reset_action(app_state, reset_command)
    if app_archive_action and app_reset_action:
        app_reset_action["after_action"] = "create_recovery_archive"
    entry = ready_entries[0]
    actions = []
    if app_reset_action:
        actions.append(app_archive_action)
        actions.append(app_reset_action)
        actions.append(_temporary_app_home_action(app_state))
        actions.append(_web_start_blocker_action(web))
        confirm_action = _confirm_readiness_action(root, web=web)
        confirm_action["after_action"] = str(app_reset_action.get("kind") or "")
        actions.append(confirm_action)
    actions.extend(
        [
            _agent_action("return_to_agent", entry),
            _agent_action("confirm_agent_visibility", entry),
            {"kind": "run_loopora_plan", "command": "/loopora-plan"},
            {"kind": "review_ready_loop_preview"},
            {"kind": "run_loopora_run", "command": "/loopora-run"},
            _support_action(root, web=web),
        ]
    )
    if not app_reset_action:
        actions.append(_web_start_action(web))
    return [action for action in actions if action]


def _doctor_actions_without_ready_entry(
    root: Path,
    *,
    workdir_state: dict[str, Any],
    agent_entries: list[dict[str, Any]],
    app_state: dict[str, Any],
    web: dict[str, Any],
) -> list[dict[str, Any]]:
    workdir_action = _workdir_action(workdir_state)
    if workdir_action:
        confirm_action = _confirm_readiness_action(root, web=web)
        confirm_action["after_action"] = str(workdir_action.get("kind") or "")
        if str(workdir_state.get("status") or "") != "missing":
            confirm_action.pop("command", None)
        return [workdir_action, confirm_action, _support_action(root, web=web)]

    archive_command = _app_state_command(app_state, "recovery_archive")
    reset_command = _app_state_command(app_state, "reset")
    app_archive_action = _app_archive_action(app_state, archive_command)
    app_reset_action = _app_reset_action(app_state, reset_command)
    if app_archive_action and app_reset_action:
        app_reset_action["after_action"] = "create_recovery_archive"
    install_action = {
        "kind": "install_agent_entry",
        "selection_required": True,
        "adapter_choices": _agent_adapter_choices(agent_entries, fallback_root=root),
    }
    actions: list[dict[str, Any] | None] = []
    if app_reset_action:
        actions.extend(
            [
                app_archive_action,
                app_reset_action,
                _temporary_app_home_action(app_state),
                _web_start_blocker_action(web),
            ]
        )
        confirm_action = _confirm_readiness_action(root, web=web)
        confirm_action["after_action"] = str(app_reset_action.get("kind") or "")
        actions.append(confirm_action)
    else:
        actions.extend([_check_fit_first_action(root), install_action])
        confirm_action = _confirm_readiness_action(root, web=web)
        confirm_action["after_action"] = "install_agent_entry"
        actions.append(confirm_action)
    if app_reset_action:
        actions.extend([_check_fit_first_action(root), install_action])
    actions.extend([{"kind": "run_loopora_plan", "command": "/loopora-plan"}, _support_action(root, web=web)])
    return [action for action in actions if action]


def target_required_doctor_next_action_items() -> list[dict[str, Any]]:
    return [
        {
            "kind": "choose_workdir",
            "command_ready": False,
            "command_blockers": ["target_project_required"],
        },
        {"kind": "support"},
    ]


def _check_fit_first_action(root: Path) -> dict[str, str]:
    return {
        "kind": "check_fit_first",
        "command": copyable_loopora_command(f"loopora fit --workdir {shlex.quote(str(root))}"),
    }


def _app_reset_action(app_state: dict[str, Any], reset_command: str) -> dict[str, str] | None:
    if app_state.get("web_ready") is False and reset_command:
        kind = _app_state_recovery_action_kind(app_state)
        action = {"kind": kind, "command": reset_command}
        if kind == "use_matching_loopora_version_or_reset":
            action["note"] = "Use a matching or newer Loopora version if available; otherwise preview the App database reset scope"
        elif kind == "inspect_or_reset_app_state":
            action["note"] = "Inspect local App state first; if choosing reset, preview the App database reset scope"
        return action
    return None


def _app_archive_action(app_state: dict[str, Any], archive_command: str) -> dict[str, object] | None:
    if app_state.get("web_ready") is False and archive_command:
        return recovery_archive_action(archive_command)
    return None


def _app_state_recovery_action_kind(app_state: dict[str, Any]) -> str:
    next_action = str(app_state.get("next_action") or "").strip()
    if next_action in {"use_matching_loopora_version_or_reset", "inspect_or_reset_app_state"}:
        return next_action
    return "preview_app_database_reset"


def _temporary_app_home_action(app_state: dict[str, Any]) -> dict[str, str] | None:
    command = _app_state_command(app_state, "temporary_serve")
    if app_state.get("web_ready") is False and command:
        return {"kind": "use_temporary_app_home", "command": command}
    return None


def _workdir_action(workdir_state: dict[str, Any]) -> dict[str, str] | None:
    status = str(workdir_state.get("status") or "").strip()
    if status == "missing":
        command = _workdir_command(workdir_state, "create")
        return {"kind": "create_workdir", "command": command} if command else {"kind": "create_workdir"}
    if status in {"required", "not_directory", "unavailable"}:
        return {"kind": "choose_workdir"}
    return None


def _web_start_action(web: dict[str, Any]) -> dict[str, Any]:
    command = str(web.get("start_command") or "").strip()
    origin = str(web.get("origin") or "").strip()
    if web.get("start_blocked_reason") == "auth_required":
        action: dict[str, str] = {"kind": "configure_web_auth"}
        auth_command = str(web.get("auth_start_command") or "").strip()
        unsafe_command = str(web.get("unsafe_start_command") or "").strip()
        if auth_command:
            action["command"] = auth_command
        if unsafe_command:
            action["unsafe_command"] = unsafe_command
        if origin:
            action["origin"] = origin
        return _web_action_with_command_readiness(action, web)
    if web.get("start_blocked_reason") == "port_in_use":
        return _web_action_with_command_readiness(_web_port_conflict_action(web, fallback_origin=origin), web)
    if web.get("start_available") is False:
        return _web_action_with_command_readiness(_web_unavailable_action(web, fallback_origin=origin), web)
    already_running = web.get("already_running") is True
    action = {
        "kind": "start_web",
        "operation": str(web.get("access_mode") or ("open_existing" if already_running else "start_or_open")),
        "already_running": already_running,
    }
    if command:
        action["command"] = command
    if origin:
        action["origin"] = origin
    return _web_action_with_command_readiness(action, web)


def _web_action_with_command_readiness(action: dict[str, str], web: dict[str, Any]) -> dict[str, Any]:
    blockers = _web_action_command_blockers(web)
    if not blockers:
        return action
    return {
        **action,
        "command_ready": False,
        "command_blockers": blockers,
        "blocked_until": _web_action_blocked_until(blockers),
    }


def _web_action_command_blockers(web: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for item in list(web.get("readiness_blockers") or []):
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "").strip()
        if kind == "app_state_not_ready":
            blockers.append(kind)
    return blockers


def _web_action_blocked_until(blockers: list[str]) -> list[str]:
    blocked_until: list[str] = []
    if "app_state_not_ready" in blockers:
        blocked_until.append("app_state_ready")
    return blocked_until


def _web_start_blocker_action(web: dict[str, Any]) -> dict[str, Any] | None:
    if web.get("start_available") is False:
        return _web_start_action(web)
    return None


def _web_port_conflict_action(web: dict[str, Any], *, fallback_origin: str) -> dict[str, str]:
    action = {"kind": "resolve_web_port"}
    suggested_command = str(web.get("suggested_start_command") or "").strip()
    requested_command = str(web.get("requested_start_command") or "").strip()
    suggested_origin = str(web.get("suggested_origin") or "").strip()
    requested_origin = str(web.get("requested_origin") or fallback_origin).strip()
    if suggested_command or requested_command:
        action["command"] = suggested_command or requested_command
    if suggested_origin or requested_origin:
        action["origin"] = suggested_origin or requested_origin
    return action


def _web_unavailable_action(web: dict[str, Any], *, fallback_origin: str) -> dict[str, str]:
    kind = "resolve_web_bind" if web.get("start_blocked_reason") == "bind_failed" else "resolve_web_port"
    action: dict[str, str] = {
        "kind": kind,
        "origin": str(web.get("requested_origin") or fallback_origin),
    }
    requested_command = str(web.get("requested_start_command") or "").strip()
    if requested_command:
        action["command"] = requested_command
    return action


def _agent_adapter_choices(agent_entries: list[dict[str, Any]], *, fallback_root: Path) -> list[dict[str, str]]:
    choices = []
    for entry in agent_entries:
        adapter = str(entry.get("adapter") or "").strip()
        if not adapter:
            continue
        commands = entry.get("commands") if isinstance(entry.get("commands"), dict) else {}
        command = str(commands.get("install") or "").strip()
        if not command:
            command = copyable_loopora_command(f"loopora init {adapter} --workdir {shlex.quote(str(fallback_root))}")
        choices.append({"adapter": adapter, "label": str(entry.get("label") or adapter), "command": command})
    return choices


def _agent_action(
    kind: str,
    entry: dict[str, Any],
    *,
    command_key: str = "",
    fallback_root: Path | None = None,
) -> dict[str, Any]:
    adapter = str(entry.get("adapter") or "codex")
    action = {
        "kind": kind,
        "adapter": adapter,
        "label": str(entry.get("label") or adapter),
    }
    commands = entry.get("commands") if isinstance(entry.get("commands"), dict) else {}
    command = str(commands.get(command_key) or "").strip() if command_key else ""
    if command_key and not command and fallback_root is not None:
        command = copyable_loopora_command(f"loopora init {adapter} --workdir {shlex.quote(str(fallback_root))}")
    if command:
        action["command"] = command
    return action


def _confirm_readiness_action(root: Path, *, web: dict[str, Any] | None = None) -> dict[str, str]:
    return {
        "kind": "confirm_readiness",
        "command": doctor_readiness_command(root, web=web),
    }


def doctor_readiness_command(root: Path, *, web: dict[str, Any] | None = None) -> str:
    web_args = _doctor_web_option_args(web or {})
    return copyable_loopora_command(f"loopora doctor --workdir {shlex.quote(str(root))}{web_args}")


def _support_action(root: Path, *, web: dict[str, Any] | None = None) -> dict[str, str]:
    web_args = _doctor_web_option_args(web or {})
    return {
        "kind": "support",
        "command": copyable_loopora_command(f"loopora support --workdir {shlex.quote(str(root))}{web_args}"),
    }
