from __future__ import annotations

import errno
import os
from collections.abc import Callable
from pathlib import Path
import shlex
from typing import Any

from loopora.agent_adapter_command_prefix import (
    copyable_loopora_command,
    current_project_file_loopora_cli_entry,
    rewrite_loopora_command_entry,
)
from loopora.app_state_readiness import app_state_report
from loopora.branding import APP_AUTH_ENV, APP_HOME_ENV
from loopora.cli_recovery_archive_guidance import copyable_recovery_archive_command
from loopora.local_web_service import matching_configured_web_service
from loopora.web_bind_preflight import WEB_BIND_UNAVAILABLE_SUMMARY, next_available_web_port, probe_web_bind
from loopora.web_origins import (
    http_origin,
    is_wildcard_bind_host,
    open_origin_for_bind_host,
    remote_origin_hint_for_wildcard,
)
from loopora.web_request_context import _is_loopback_host

DEFAULT_WEB_HOST = "127.0.0.1"
DEFAULT_WEB_PORT = 8742
ProbeWebBind = Callable[[str, int], None]
NextAvailableWebPort = Callable[..., int | None]


def doctor_target_required_app_state() -> dict[str, Any]:
    return {
        "status": "target_required",
        "schema_version": None,
        "current_schema_version": None,
        "web_ready": None,
        "needs_attention": True,
        "next_action": "choose_workdir",
        "summary": "App state is checked only after a target project directory is selected.",
        "commands": {},
    }


def doctor_app_state_report(root: Path, *, include_commands: bool = True) -> dict[str, Any]:
    commands = _doctor_app_state_commands(root) if include_commands else {}
    return app_state_report(root, commands=commands)


def doctor_app_state_with_web_recovery(app_state: dict[str, Any], web: dict[str, Any]) -> dict[str, Any]:
    if app_state.get("web_ready") is not False:
        return app_state
    temporary_serve = _temporary_app_home_serve_command(web)
    if not temporary_serve:
        return app_state
    commands = app_state.get("commands") if isinstance(app_state.get("commands"), dict) else {}
    return {
        **app_state,
        "commands": {
            **commands,
            "temporary_serve": temporary_serve,
        },
    }


def doctor_app_state_command(app_state: dict[str, Any], key: str) -> str:
    commands = app_state.get("commands") if isinstance(app_state.get("commands"), dict) else {}
    return str(commands.get(key) or "").strip()


def doctor_workdir_command(workdir_state: dict[str, Any], key: str) -> str:
    commands = workdir_state.get("commands") if isinstance(workdir_state.get("commands"), dict) else {}
    return str(commands.get(key) or "").strip()


def doctor_web_option_args(web: dict[str, Any]) -> str:
    requested_host = str(web.get("requested_host") or web.get("host") or DEFAULT_WEB_HOST).strip() or DEFAULT_WEB_HOST
    requested_port = _coerce_port(web.get("requested_port") or web.get("port"), DEFAULT_WEB_PORT)
    args = []
    if requested_host != DEFAULT_WEB_HOST:
        args.append(f"--web-host {shlex.quote(requested_host)}")
    if requested_port != DEFAULT_WEB_PORT:
        args.append(f"--web-port {requested_port}")
    return f" {' '.join(args)}" if args else ""


def doctor_web_report(  # noqa: PLR0913 - probe injection preserves the doctor compatibility patch point.
    host: str,
    port: int,
    *,
    startup_workdir: Path | None = None,
    web_already_running: bool = False,
    web_auth_enabled: bool | None = None,
    probe_bind: ProbeWebBind = probe_web_bind,
    next_available_port: NextAvailableWebPort = next_available_web_port,
) -> dict[str, Any]:
    requested = _web_endpoint_report(host, port, startup_workdir=startup_workdir)
    auth_token_configured = _doctor_auth_token_configured() if web_auth_enabled is None else bool(web_auth_enabled)
    report = {
        **requested,
        "requested_host": requested["host"],
        "requested_port": requested["port"],
        "requested_origin": requested["origin"],
        "requested_bind_origin": requested["bind_origin"],
        "requested_remote_origin_hint": requested["remote_origin_hint"],
        "requested_start_command": requested["start_command"],
        "start_available": True,
        "start_blocked_reason": "",
        "start_error": "",
        "already_running": web_already_running,
        "access_mode": "open_existing" if web_already_running else "start_or_open",
        "auth_required": requested["auth_required"],
        "auth_enabled": auth_token_configured,
        "auth_token_env_var": APP_AUTH_ENV,
        "auth_token_configured": auth_token_configured,
        "auth_token_printed": False,
        "auth_start_command": _web_auth_start_command(host, port, startup_workdir=startup_workdir),
        "unsafe_start_command": _web_unsafe_start_command(host, port, startup_workdir=startup_workdir),
        "suggested_port": None,
        "suggested_origin": "",
        "suggested_start_command": "",
    }
    if web_already_running:
        return report
    if report["auth_required"] and not report["auth_token_configured"]:
        report.update(
            {
                "start_available": False,
                "start_blocked_reason": "auth_required",
                "access_mode": "recovery_required",
            }
        )
        return report
    try:
        probe_bind(host, port)
    except OSError as exc:
        reason = "port_in_use" if exc.errno == errno.EADDRINUSE else "bind_failed"
        start_error = "port is already in use" if reason == "port_in_use" else WEB_BIND_UNAVAILABLE_SUMMARY
        report.update(
            {
                "start_available": False,
                "start_blocked_reason": reason,
                "start_error": start_error,
                "access_mode": "recovery_required",
            }
        )
        if reason != "port_in_use":
            return report
        if matching_configured_web_service(host, port):
            report.update(
                {
                    **requested,
                    "start_available": True,
                    "start_blocked_reason": "",
                    "start_error": "",
                    "already_running": True,
                    "access_mode": "open_existing",
                }
            )
            return report
        suggested_port = next_available_port(host=host, port=port)
        if suggested_port is None:
            return report
        suggested = _web_endpoint_report(host, suggested_port, startup_workdir=startup_workdir)
        report.update(
            {
                **suggested,
                "suggested_port": suggested_port,
                "suggested_origin": suggested["origin"],
                "suggested_start_command": suggested["start_command"],
            }
        )
    return report


def commandless_doctor_web_report(web: dict[str, Any]) -> dict[str, Any]:
    command_keys = {
        "start_command",
        "requested_start_command",
        "auth_start_command",
        "unsafe_start_command",
        "suggested_start_command",
    }
    return {
        **{key: value for key, value in web.items() if key not in command_keys},
        "readiness_blockers": list(web.get("readiness_blockers") or []),
    }


def _doctor_app_state_commands(root: Path) -> dict[str, str]:
    return {
        "recovery_archive": copyable_recovery_archive_command(root),
        "reset": copyable_loopora_command(f"loopora dev reset --scope app --workdir {shlex.quote(str(root))}"),
        "preview_reset": copyable_loopora_command(f"loopora dev reset --scope app --workdir {shlex.quote(str(root))}"),
        "apply_reset": copyable_loopora_command(
            f"loopora dev reset --scope app --workdir {shlex.quote(str(root))} --yes"
        ),
    }


def _temporary_app_home_serve_command(web: dict[str, Any]) -> str:
    if web.get("start_available") is False and str(web.get("start_blocked_reason") or "") in {
        "bind_failed",
        "port_in_use",
    }:
        return ""
    host = str(web.get("host") or DEFAULT_WEB_HOST).strip() or DEFAULT_WEB_HOST
    port = _coerce_port(web.get("port"), DEFAULT_WEB_PORT)
    startup_workdir = str(web.get("startup_workdir") or "").strip()
    parts = [
        f'{APP_HOME_ENV}="$(mktemp -d)"',
        "loopora",
        "serve",
        "--open",
        "--host",
        shlex.quote(host),
        "--port",
        str(port),
    ]
    if web.get("auth_required") is True and web.get("auth_token_configured") is not True:
        parts.extend(["--auth-token", shlex.quote("<token>")])
    if startup_workdir:
        parts.extend(["--workdir", shlex.quote(startup_workdir)])
    return rewrite_loopora_command_entry(" ".join(parts), cli_entry=current_project_file_loopora_cli_entry())


def _web_endpoint_report(host: str, port: int, *, startup_workdir: Path | None) -> dict[str, Any]:
    loopback = _is_loopback_host(host)
    wildcard_bind = is_wildcard_bind_host(host)
    bind_origin = http_origin(host, port)
    workdir_arg = _serve_workdir_arg(startup_workdir)
    return {
        "default": host == DEFAULT_WEB_HOST and port == DEFAULT_WEB_PORT,
        "host": host,
        "port": port,
        "origin": open_origin_for_bind_host(host, port),
        "bind_origin": bind_origin,
        "wildcard_bind": wildcard_bind,
        "remote_origin_hint": remote_origin_hint_for_wildcard(port) if wildcard_bind else "",
        "loopback": loopback,
        "auth_required": not loopback,
        "requires_token_when_non_loopback": True,
        "startup_workdir": str(startup_workdir or ""),
        "start_command": copyable_loopora_command(f"loopora serve --open --host {shlex.quote(host)} --port {port}{workdir_arg}"),
    }


def _doctor_auth_token_configured() -> bool:
    return bool(str(os.environ.get(APP_AUTH_ENV) or "").strip())


def _web_auth_start_command(host: str, port: int, *, startup_workdir: Path | None = None) -> str:
    return copyable_loopora_command(
        f"loopora serve --open --host {shlex.quote(host)} --port {port} --auth-token {shlex.quote('<token>')}{_serve_workdir_arg(startup_workdir)}"
    )


def _web_unsafe_start_command(host: str, port: int, *, startup_workdir: Path | None = None) -> str:
    return copyable_loopora_command(
        f"loopora serve --open --host {shlex.quote(host)} --port {port} --allow-unsafe-open{_serve_workdir_arg(startup_workdir)}"
    )


def _serve_workdir_arg(startup_workdir: Path | None) -> str:
    return f" --workdir {shlex.quote(str(startup_workdir))}" if startup_workdir else ""


def _coerce_port(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
