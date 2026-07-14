from __future__ import annotations

from collections.abc import Callable
import shlex

from loopora.agent_adapter_command_prefix import (
    copyable_loopora_command,
    current_project_file_loopora_cli_entry,
    rewrite_loopora_command_entry,
)
from loopora.branding import APP_HOME_ENV
from loopora.cli_serve_language import localized_serve_command, serve_text
from loopora.web_request_context import _is_loopback_host


def serve_development_reset_extra_recovery_lines(  # noqa: PLR0913 - recovery text preserves the attempted serve context.
    *,
    host: str,
    port: int,
    startup_workdir: str,
    allow_unsafe_open: bool,
    auth_token_configured: bool,
    language: str = "en",
) -> list[str]:
    if auth_token_configured and not _is_loopback_host(host):
        serve_command = rewrite_loopora_command_entry(
            serve_start_command(
                host=host,
                port=port,
                startup_workdir=startup_workdir,
                allow_unsafe_open=allow_unsafe_open,
                auth_token_placeholder=True,
            ),
            cli_entry=current_project_file_loopora_cli_entry(),
        )
        serve_command = localized_serve_command(serve_command, language=language)
        return [
            serve_text(
                language,
                f'temporary Web preview: {APP_HOME_ENV}="$(mktemp -d)" {serve_command}',
                f'临时 Web 预览：{APP_HOME_ENV}="$(mktemp -d)" {serve_command}',
            ),
            serve_text(
                language,
                "temporary Web note: replace <token> locally; the real auth token is not printed. This uses a new empty "
                "App home for preview or troubleshooting and does not delete, migrate, or repair the blocked App database.",
                "临时 Web 说明：请在本地替换 <token>；真实 token 不会被打印。此命令使用新的空 App home 做预览或排障，"
                "不会删除、迁移或修复被阻止的 App 数据库。",
            ),
        ]
    serve_parts = [
        "loopora",
        "serve",
        "--open",
        "--host",
        shlex.quote(str(host)),
        "--port",
        str(port),
    ]
    if allow_unsafe_open:
        serve_parts.append("--allow-unsafe-open")
    if startup_workdir:
        serve_parts.extend(["--workdir", shlex.quote(startup_workdir)])
    serve_command = rewrite_loopora_command_entry(" ".join(serve_parts), cli_entry=current_project_file_loopora_cli_entry())
    serve_command = localized_serve_command(serve_command, language=language)
    return [
        serve_text(
            language,
            f'temporary Web preview: {APP_HOME_ENV}="$(mktemp -d)" {serve_command}',
            f'临时 Web 预览：{APP_HOME_ENV}="$(mktemp -d)" {serve_command}',
        ),
        serve_text(
            language,
            "temporary Web note: uses a new empty App home for preview or troubleshooting; it does not delete, migrate, or repair the blocked App database.",
            "临时 Web 说明：使用新的空 App home 做预览或排障；不会删除、迁移或修复被阻止的 App 数据库。",
        ),
    ]


def copyable_serve_start_command(
    *,
    host: str,
    port: int,
    startup_workdir: str,
    allow_unsafe_open: bool = False,
    auth_token_placeholder: bool = False,
) -> str:
    return copyable_loopora_command(
        serve_start_command(
            host=host,
            port=port,
            startup_workdir=startup_workdir,
            allow_unsafe_open=allow_unsafe_open,
            auth_token_placeholder=auth_token_placeholder,
        )
    )


def serve_start_command(
    *,
    host: str,
    port: int,
    startup_workdir: str,
    allow_unsafe_open: bool = False,
    auth_token_placeholder: bool = False,
) -> str:
    parts = ["loopora", "serve", "--open", "--host", shlex.quote(str(host)), "--port", str(port)]
    if auth_token_placeholder:
        parts.extend(["--auth-token", shlex.quote("<token>")])
    if allow_unsafe_open:
        parts.append("--allow-unsafe-open")
    if startup_workdir:
        parts.extend(["--workdir", shlex.quote(startup_workdir)])
    return " ".join(parts)


def serve_retry_command(*, workdir: str, host: str, port: int, allow_unsafe_open: bool) -> str:
    parts = [
        "loopora",
        "serve",
        "--open",
        "--host",
        shlex.quote(str(host)),
        "--port",
        str(port),
        "--workdir",
        shlex.quote(workdir),
    ]
    if allow_unsafe_open:
        parts.append("--allow-unsafe-open")
    return " ".join(parts)


def serve_alternate_port_action(  # noqa: PLR0913 - injected port probe preserves the CLI compatibility patch point.
    *,
    host: str,
    port: int,
    startup_workdir: str,
    allow_unsafe_open: bool,
    auth_token_configured: bool,
    next_available_port: Callable[..., int | None],
) -> dict[str, str]:
    next_port = next_available_port(host=host, port=port)
    if next_port is None:
        return {}
    return {
        "kind": "retry_web_start_on_alternate_port",
        "command": copyable_serve_start_command(
            host=host,
            port=next_port,
            startup_workdir=startup_workdir,
            allow_unsafe_open=allow_unsafe_open,
            auth_token_placeholder=auth_token_configured,
        ),
    }


def serve_temporary_app_home_action(
    *,
    host: str,
    port: int,
    startup_workdir: str,
    allow_unsafe_open: bool,
    auth_token_configured: bool,
) -> dict[str, object]:
    note = "Uses a new empty App home for preview or troubleshooting; it does not delete, migrate, or repair the blocked App database."
    if auth_token_configured and not _is_loopback_host(host):
        note = "Replace <token> locally; the real auth token is not printed. " + note
    return {
        "kind": "use_temporary_app_home",
        "command": serve_temporary_app_home_command(
            host=host,
            port=port,
            startup_workdir=startup_workdir,
            allow_unsafe_open=allow_unsafe_open,
            auth_token_placeholder=auth_token_configured and not _is_loopback_host(host),
        ),
        "command_ready": True,
        "command_blockers": [],
        "note": note,
    }


def serve_temporary_app_home_command(
    *,
    host: str,
    port: int,
    startup_workdir: str,
    allow_unsafe_open: bool,
    auth_token_placeholder: bool,
) -> str:
    serve_command = rewrite_loopora_command_entry(
        serve_start_command(
            host=host,
            port=port,
            startup_workdir=startup_workdir,
            allow_unsafe_open=allow_unsafe_open,
            auth_token_placeholder=auth_token_placeholder,
        ),
        cli_entry=current_project_file_loopora_cli_entry(),
    )
    return f'{APP_HOME_ENV}="$(mktemp -d)" {serve_command}'
