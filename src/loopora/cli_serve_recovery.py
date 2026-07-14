from __future__ import annotations

import errno
from collections.abc import Callable
from pathlib import Path
import shlex

from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.app_state_readiness import app_state_report, app_state_web_readiness_blockers
from loopora.cli_recovery_archive_guidance import copyable_recovery_archive_command
from loopora.cli_serve_command_projection import (
    copyable_serve_start_command as _copyable_serve_start_command,
    serve_alternate_port_action as _serve_alternate_port_action,
    serve_development_reset_extra_recovery_lines as serve_development_reset_extra_recovery_lines,
    serve_temporary_app_home_action as _serve_temporary_app_home_action,
)
from loopora.cli_serve_recovery_projection import (
    serve_port_validation_error_payload as serve_port_validation_error_payload,
    serve_startup_actions_with_app_state as _serve_startup_actions_with_app_state,
    serve_startup_recovery_payload as _serve_startup_recovery_payload,
)
from loopora.cli_serve_workdir_recovery import (
    serve_startup_workdir as serve_startup_workdir,
    serve_workdir_recovery_payload as serve_workdir_recovery_payload,
)
from loopora.web_bind_preflight import WEB_BIND_UNAVAILABLE_RECOVERY, WEB_BIND_UNAVAILABLE_SUMMARY
from loopora.web_origins import http_origin
from loopora.web_request_context import _is_loopback_host


ProbeWebBind = Callable[[str, int], None]
NextAvailableWebPort = Callable[..., int | None]


def serve_app_state_report(startup_workdir: str) -> dict[str, object]:
    root = Path(startup_workdir) if startup_workdir else Path.cwd()
    command = copyable_loopora_command(f"loopora dev reset --scope app --workdir {shlex.quote(str(root))}")
    return app_state_report(
        root,
        commands={
            "recovery_archive": copyable_recovery_archive_command(root),
            "reset": command,
            "preview_reset": command,
            "apply_reset": f"{command} --yes",
        },
    )


def serve_network_auth_recovery_payload(
    *,
    host: str,
    port: int,
    startup_workdir: str,
    app_state: dict[str, object],
) -> dict[str, object]:
    error = "refusing to bind a non-loopback host without protection; use --auth-token '<token>' or explicitly pass --allow-unsafe-open"
    next_actions = [
        {
            "kind": "configure_auth_token",
            "command": _copyable_serve_start_command(
                host=host,
                port=port,
                startup_workdir=startup_workdir,
                auth_token_placeholder=True,
            ),
            "note": "Retry with an auth token; token values are never printed.",
        },
        {
            "kind": "use_loopback_web",
            "command": _copyable_serve_start_command(host="127.0.0.1", port=port, startup_workdir=startup_workdir),
        },
        {
            "kind": "allow_unsafe_open",
            "command": _copyable_serve_start_command(
                host=host,
                port=port,
                startup_workdir=startup_workdir,
                allow_unsafe_open=True,
            ),
            "note": "Unsafe opt-in for trusted networks only.",
        },
    ]
    next_actions = _serve_startup_actions_with_app_state(next_actions, app_state)
    return _serve_startup_recovery_payload(
        status="blocked_by_network_auth",
        start_blocked_reason="network_auth_required",
        error=error,
        host=host,
        port=port,
        startup_workdir=startup_workdir,
        next_actions=next_actions,
        network_auth_required=True,
        app_state=app_state,
    )


def serve_bind_recovery_payload(  # noqa: PLR0913 - bind recovery payload preserves attempted serve context.
    *,
    host: str,
    port: int,
    startup_workdir: str,
    allow_unsafe_open: bool,
    auth_token_configured: bool,
    app_state: dict[str, object],
    probe_bind: ProbeWebBind,
    next_available_port: NextAvailableWebPort,
) -> dict[str, object]:
    try:
        probe_bind(host, port)
        return {}
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            return _serve_port_conflict_recovery_payload(
                host=host,
                port=port,
                startup_workdir=startup_workdir,
                allow_unsafe_open=allow_unsafe_open,
                auth_token_configured=auth_token_configured,
                app_state=app_state,
                next_available_port=next_available_port,
            )
        return _serve_bind_unavailable_recovery_payload(host=host, port=port, startup_workdir=startup_workdir, app_state=app_state)


def serve_app_state_recovery_payload(  # noqa: PLR0913 - payload mirrors the attempted serve command context.
    *,
    host: str,
    port: int,
    startup_workdir: str,
    allow_unsafe_open: bool,
    auth_token_configured: bool,
    app_state: dict[str, object],
) -> dict[str, object]:
    retry_action = {
        "kind": "retry_web_start",
        "command": _copyable_serve_start_command(
            host=host,
            port=port,
            startup_workdir=startup_workdir,
            allow_unsafe_open=allow_unsafe_open,
            auth_token_placeholder=auth_token_configured and not _is_loopback_host(host),
        ),
    }
    next_actions = _serve_startup_actions_with_app_state(
        [
            retry_action,
            _serve_temporary_app_home_action(
                host=host,
                port=port,
                startup_workdir=startup_workdir,
                allow_unsafe_open=allow_unsafe_open,
                auth_token_configured=auth_token_configured,
            ),
        ],
        app_state,
    )
    return _serve_startup_recovery_payload(
        status="blocked_by_app_state",
        start_blocked_reason="app_state_not_ready",
        error=_serve_app_state_recovery_error(app_state),
        host=host,
        port=port,
        startup_workdir=startup_workdir,
        next_actions=next_actions,
        network_auth_required=False,
        app_state=app_state,
    )


def _serve_port_conflict_recovery_payload(  # noqa: PLR0913 - port recovery payload preserves attempted serve context.
    *,
    host: str,
    port: int,
    startup_workdir: str,
    allow_unsafe_open: bool,
    auth_token_configured: bool,
    app_state: dict[str, object],
    next_available_port: NextAvailableWebPort,
) -> dict[str, object]:
    next_actions: list[dict[str, object]] = []
    alternate_action = _serve_alternate_port_action(
        host=host,
        port=port,
        startup_workdir=startup_workdir,
        allow_unsafe_open=allow_unsafe_open,
        auth_token_configured=auth_token_configured,
        next_available_port=next_available_port,
    )
    if alternate_action:
        next_actions.append(alternate_action)
    next_actions.append({"kind": "stop_existing_service"})
    next_actions.append({"kind": "choose_web_port"})
    next_actions = _serve_startup_actions_with_app_state(next_actions, app_state)
    blocked_by_app_state = bool(app_state_web_readiness_blockers(app_state))
    if alternate_action and blocked_by_app_state:
        suggestion = f" After App state is ready, retry with `{alternate_action['command']}`."
    else:
        suggestion = f" Try `{alternate_action['command']}`." if alternate_action else ""
    error = (
        f"cannot start Loopora Web on {http_origin(host, port)}: port {port} is already in use.{suggestion} Stop the existing service or choose another port."
    )
    return _serve_startup_recovery_payload(
        status="blocked_by_port_conflict",
        start_blocked_reason="port_in_use",
        error=error,
        host=host,
        port=port,
        startup_workdir=startup_workdir,
        next_actions=next_actions,
        network_auth_required=False,
        app_state=app_state,
    )


def _serve_bind_unavailable_recovery_payload(
    *,
    host: str,
    port: int,
    startup_workdir: str,
    app_state: dict[str, object],
) -> dict[str, object]:
    next_actions = [
        {
            "kind": "resolve_web_bind",
            "command": _copyable_serve_start_command(host=host, port=port, startup_workdir=startup_workdir),
            "note": "Choose a different --host / --port before retrying.",
        }
    ]
    next_actions = _serve_startup_actions_with_app_state(next_actions, app_state)
    error = f"cannot start Loopora Web on {http_origin(host, port)}: {WEB_BIND_UNAVAILABLE_SUMMARY}. {WEB_BIND_UNAVAILABLE_RECOVERY}"
    return _serve_startup_recovery_payload(
        status="blocked_by_bind",
        start_blocked_reason="bind_failed",
        error=error,
        host=host,
        port=port,
        startup_workdir=startup_workdir,
        next_actions=next_actions,
        network_auth_required=False,
        app_state=app_state,
    )


def _serve_app_state_recovery_error(app_state: dict[str, object]) -> str:
    status = str(app_state.get("status") or "").strip()
    schema_version = app_state.get("schema_version")
    current_version = app_state.get("current_schema_version")
    commands = app_state.get("commands") if isinstance(app_state.get("commands"), dict) else {}
    preview_command = str(commands.get("preview_reset") or commands.get("reset") or "").strip()
    apply_command = str(commands.get("apply_reset") or "").strip()
    recovery_archive = str(commands.get("recovery_archive") or "").strip()
    if status == "development_reset_required":
        version_text = f"version {schema_version}" if schema_version is not None else "an incompatible version"
        message = f"Loopora v3 development reset required: existing local database schema {version_text} is not compatible."
    elif status == "future_version":
        version_text = f"version {schema_version}" if schema_version is not None else "a newer version"
        current_text = f"supported version {current_version}" if current_version is not None else "this Loopora version"
        message = (
            f"App database was created by a newer Loopora schema ({version_text}; {current_text}). "
            "Use a matching or newer Loopora version, or preview an app-scope reset."
        )
    else:
        message = str(app_state.get("summary") or "").strip() or "Local App state is not ready for Web start."
    lines = [message]
    if recovery_archive:
        lines.append(f"recovery archive before reset: {recovery_archive}")
    if preview_command:
        lines.append(f"reset preview: {preview_command}")
    if apply_command:
        lines.append(f"reset apply after review: {apply_command}")
    lines.append("reset scope: app scope resets only local App database files; project .loopora state and managed Agent entries are left alone.")
    return "\n".join(lines)
