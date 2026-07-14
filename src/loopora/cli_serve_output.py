from __future__ import annotations

from pathlib import Path

import typer

from loopora.app_state_readiness import app_state_web_readiness_blockers
from loopora.cli_diagnose_commands import normalize_web_port
from loopora.cli_serve_recovery import (
    serve_app_state_recovery_payload,
    serve_app_state_report,
    serve_bind_recovery_payload as _serve_bind_recovery_payload,
    serve_development_reset_extra_recovery_lines,
    serve_network_auth_recovery_payload,
    serve_port_validation_error_payload as _serve_port_validation_error_payload,
    serve_startup_workdir,
    serve_workdir_recovery_payload as _serve_workdir_recovery_payload,
)
from loopora.cli_serve_terminal import (
    print_serve_existing_web_summary,
    print_serve_startup_recovery as _print_serve_startup_recovery,
    print_serve_startup_summary,
    print_serve_workdir_recovery as _print_serve_workdir_recovery,
)
from loopora.cli_shared import echo_json
from loopora.cli_serve_language import serve_text
from loopora.serve_browser_open import serve_browser_url
from loopora.web_bind_preflight import next_available_web_port, probe_web_bind


__all__ = [
    "exit_if_serve_app_state_not_ready",
    "exit_if_serve_bind_unavailable",
    "exit_with_serve_startup_recovery",
    "exit_with_serve_workdir_recovery",
    "next_available_web_port",
    "normalize_auth_token",
    "normalize_serve_port_or_exit",
    "print_serve_existing_web_summary",
    "print_serve_startup_summary",
    "probe_web_bind",
    "serve_app_state_recovery_payload",
    "serve_app_state_report",
    "serve_browser_url_or_exit",
    "serve_development_reset_extra_recovery_lines",
    "serve_network_auth_recovery_payload",
    "serve_startup_workdir",
]


def normalize_serve_port_or_exit(value: object, *, json_output: bool = False, language: str = "en") -> int:
    try:
        return normalize_web_port(value)
    except ValueError as exc:
        message = f"invalid --port: {exc}"
        if json_output:
            echo_json(_serve_port_validation_error_payload(message))
        else:
            typer.echo(serve_text(language, message, f"无效的 --port：{exc}"), err=True)
        raise typer.Exit(code=2) from exc


def normalize_auth_token(auth_token: object) -> str:
    return str(auth_token or "").strip()


def serve_browser_url_or_exit(  # noqa: PLR0913 - browser target validation mirrors public serve context.
    *,
    open_browser: bool,
    open_path: str,
    host: str,
    port: int,
    startup_workdir: str,
    language: str = "en",
) -> str:
    if open_path and not open_browser:
        typer.echo(
            serve_text(language, "invalid --open-path: use it only with --open", "无效的 --open-path：只能与 --open 一起使用"),
            err=True,
        )
        raise typer.Exit(code=2)
    if not open_browser:
        return ""
    try:
        return serve_browser_url(host=host, port=port, open_path=open_path, workdir=startup_workdir)
    except ValueError as exc:
        typer.echo(serve_text(language, f"invalid --open-path: {exc}", f"无效的 --open-path：{exc}"), err=True)
        raise typer.Exit(code=2) from exc


def exit_with_serve_startup_recovery(payload: dict[str, object], *, json_output: bool, language: str = "en") -> None:
    if json_output:
        echo_json(payload)
        raise typer.Exit(code=1)
    _print_serve_startup_recovery(payload, language=language)
    raise typer.Exit(code=1)


def exit_with_serve_workdir_recovery(  # noqa: PLR0913 - serve recovery preserves public CLI context fields.
    *,
    workdir: Path | None,
    host: str,
    port: int,
    allow_unsafe_open: bool,
    auth_token_configured: bool,
    language: str = "en",
    json_output: bool = False,
) -> None:
    payload = _serve_workdir_recovery_payload(
        workdir=workdir,
        host=host,
        port=port,
        allow_unsafe_open=allow_unsafe_open,
        auth_token_configured=auth_token_configured,
    )
    if json_output:
        echo_json(payload)
    else:
        _print_serve_workdir_recovery(payload, language=language)
    raise typer.Exit(code=1)


def exit_if_serve_bind_unavailable(  # noqa: PLR0913 - bind recovery needs the full attempted serve context.
    *,
    host: str,
    port: int,
    startup_workdir: str,
    allow_unsafe_open: bool,
    auth_token_configured: bool,
    app_state: dict[str, object],
    language: str = "en",
    json_output: bool,
) -> None:
    payload = _serve_bind_recovery_payload(
        host=host,
        port=port,
        startup_workdir=startup_workdir,
        allow_unsafe_open=allow_unsafe_open,
        auth_token_configured=auth_token_configured,
        app_state=app_state,
        probe_bind=probe_web_bind,
        next_available_port=next_available_web_port,
    )
    if payload:
        exit_with_serve_startup_recovery(payload, json_output=json_output, language=language)


def exit_if_serve_app_state_not_ready(  # noqa: PLR0913 - App-state recovery needs the full attempted serve context.
    *,
    host: str,
    port: int,
    startup_workdir: str,
    allow_unsafe_open: bool,
    auth_token_configured: bool,
    app_state: dict[str, object],
    language: str = "en",
    json_output: bool,
) -> None:
    if not app_state_web_readiness_blockers(app_state):
        return
    exit_with_serve_startup_recovery(
        serve_app_state_recovery_payload(
            host=host,
            port=port,
            startup_workdir=startup_workdir,
            allow_unsafe_open=allow_unsafe_open,
            auth_token_configured=auth_token_configured,
            app_state=app_state,
        ),
        language=language,
        json_output=json_output,
    )
