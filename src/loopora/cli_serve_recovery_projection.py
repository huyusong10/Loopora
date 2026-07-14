from __future__ import annotations

from loopora.app_state_readiness import app_state_web_readiness_blockers
from loopora.cli_recovery_archive_guidance import recovery_archive_action
from loopora.first_use_action_readiness import (
    first_use_action_readiness_summary,
    project_first_use_action_readiness_summary,
)
from loopora.web_origins import http_origin


def serve_port_validation_error_payload(message: str) -> dict[str, object]:
    next_actions = [{"kind": "choose_valid_port", "note": "Use an integer between 1 and 65535."}]
    payload = {
        "serve_startup_error_summary": {
            "ready": False,
            "status": "error",
            "option": "port",
            "start_blocked_reason": "invalid_port",
            "next_action_kinds": serve_action_kinds(next_actions),
        },
        "status": "error",
        "error": message,
        "start_blocked_reason": "invalid_port",
        "next_actions": next_actions,
    }
    project_serve_next_action_contract(payload, summary_key="serve_startup_error_summary")
    return payload


def serve_startup_recovery_payload(  # noqa: PLR0913 - startup recovery payload is the public JSON boundary.
    *,
    status: str,
    start_blocked_reason: str,
    error: str,
    host: str,
    port: int,
    startup_workdir: str,
    next_actions: list[dict[str, object]],
    network_auth_required: bool,
    app_state: dict[str, object],
) -> dict[str, object]:
    readiness_blockers = app_state_web_readiness_blockers(app_state)
    payload = {
        "serve_startup_recovery_summary": {
            "ready": False,
            "status": status,
            "surface": "cli_serve",
            "start_blocked_reason": start_blocked_reason,
            "host": host,
            "port": port,
            "workdir": startup_workdir,
            "next_action_kinds": serve_action_kinds(next_actions),
            "network_auth_required": network_auth_required,
            "app_state_status": str(app_state.get("status") or ""),
            "app_state_web_ready": app_state.get("web_ready") is not False,
            "readiness_blockers": readiness_blockers,
        },
        "status": status,
        "surface": "cli_serve",
        "start_blocked_reason": start_blocked_reason,
        "readiness_blockers": readiness_blockers,
        "app_state": serve_startup_app_state_payload(app_state),
        "host": host,
        "port": port,
        "origin": http_origin(host, port),
        "workdir": startup_workdir,
        "error": error,
        "next_actions": next_actions,
    }
    project_serve_next_action_contract(payload, summary_key="serve_startup_recovery_summary")
    return payload


def serve_startup_actions_with_app_state(
    actions: list[dict[str, object]],
    app_state: dict[str, object],
) -> list[dict[str, object]]:
    blockers = app_state_web_readiness_blockers(app_state)
    if not blockers:
        return list(actions)
    command_blockers = [str(item.get("kind") or "").strip() for item in blockers if item.get("kind")]
    projected: list[dict[str, object]] = []
    recovery_action = serve_app_recovery_archive_action(app_state)
    if recovery_action:
        projected.append(recovery_action)
    reset_action = serve_app_reset_action(app_state)
    if reset_action:
        projected.append(reset_action)
    for action in actions:
        if serve_action_starts_web(action):
            projected.append(
                {
                    **action,
                    "command_ready": False,
                    "command_blockers": command_blockers,
                    "blocked_until": ["app_state_ready"],
                }
            )
        else:
            projected.append(action)
    return projected


def serve_action_starts_web(action: dict[str, object]) -> bool:
    return str(action.get("kind") or "") in {
        "configure_auth_token",
        "use_loopback_web",
        "allow_unsafe_open",
        "retry_web_start",
        "retry_web_start_on_alternate_port",
        "resolve_web_bind",
    }


def serve_app_reset_action(app_state: dict[str, object]) -> dict[str, object]:
    commands = app_state.get("commands") if isinstance(app_state.get("commands"), dict) else {}
    command = str(commands.get("preview_reset") or commands.get("reset") or "").strip()
    if not command:
        return {}
    status = str(app_state.get("status") or "").strip()
    kind = serve_app_state_recovery_action_kind(app_state)
    if status == "future_version":
        note = (
            "Use a matching or newer Loopora version if available. If choosing reset instead, review this App database "
            "reset scope before retrying Web start commands."
        )
    elif kind == "inspect_or_reset_app_state":
        note = (
            "Inspect local App state first. If choosing reset, review this App database reset scope before retrying Web "
            "start commands."
        )
    else:
        note = "Review the local App database reset scope before retrying Web start commands."
    action = {
        "kind": kind,
        "command": command,
        "command_ready": True,
        "command_blockers": [],
        "note": note,
    }
    if str(commands.get("recovery_archive") or "").strip():
        action["after_action"] = "create_recovery_archive"
    return action


def serve_app_recovery_archive_action(app_state: dict[str, object]) -> dict[str, object]:
    commands = app_state.get("commands") if isinstance(app_state.get("commands"), dict) else {}
    command = str(commands.get("recovery_archive") or "").strip()
    return recovery_archive_action(command) if command else {}


def serve_app_state_recovery_action_kind(app_state: dict[str, object]) -> str:
    next_action = str(app_state.get("next_action") or "").strip()
    if next_action in {"use_matching_loopora_version_or_reset", "inspect_or_reset_app_state"}:
        return next_action
    return "preview_app_database_reset"


def serve_startup_app_state_payload(app_state: dict[str, object]) -> dict[str, object]:
    return {
        "status": app_state.get("status"),
        "schema_version": app_state.get("schema_version"),
        "current_schema_version": app_state.get("current_schema_version"),
        "web_ready": app_state.get("web_ready"),
        "needs_attention": app_state.get("needs_attention"),
        "next_action": app_state.get("next_action"),
        "commands": dict(app_state.get("commands") or {}) if isinstance(app_state.get("commands"), dict) else {},
    }


def serve_action_kinds(actions: list[dict[str, object]]) -> list[str]:
    return [str(action.get("kind") or "").strip() for action in actions if str(action.get("kind") or "").strip()]


def project_serve_next_action_contract(payload: dict[str, object], *, summary_key: str) -> None:
    actions = [action for action in list(payload.get("next_actions") or []) if isinstance(action, dict)]
    action_kinds = serve_action_kinds(actions)
    payload["next_action_kinds"] = action_kinds
    readiness = first_use_action_readiness_summary(actions)
    project_first_use_action_readiness_summary(payload, prefix="next_action", readiness=readiness)
    summary = payload.get(summary_key)
    if isinstance(summary, dict):
        summary["next_action_kinds"] = list(action_kinds)
        project_first_use_action_readiness_summary(summary, prefix="next_action", readiness=readiness)
