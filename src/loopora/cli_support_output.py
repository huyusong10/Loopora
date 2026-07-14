from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import shlex

import typer

from loopora.cli_diagnose_commands import DEFAULT_WEB_HOST, DEFAULT_WEB_PORT, normalize_web_port
from loopora.cli_shared import echo_json, handle_error
from loopora.diagnose_doctor import build_doctor_report, doctor_public_json_payload
from loopora.service import LooporaError
from loopora.support_guidance import (
    SUPPORT_WORKDIR_PLACEHOLDER,
    normalize_support_guidance_language,
    public_support_guidance_lines,
    public_support_payload,
    support_public_issue_bundle_text,
    support_text,
)


def print_public_support_command_output(  # noqa: PLR0913 - Support CLI mirrors the public option boundary.
    *,
    workdir: Path | None,
    language: str,
    web_host: str | None,
    web_port: str | None,
    json_output: bool,
    public_issue_bundle: bool,
) -> None:
    try:
        support_language = normalize_support_guidance_language(language)
    except ValueError as exc:
        if json_output:
            handle_error(ValueError(f"invalid --language: {exc}"), json_output=True)
            return
        typer.echo(f"invalid --language: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    try:
        normalized_web_port = normalize_web_port(web_port) if web_port is not None else None
    except ValueError as exc:
        if json_output:
            handle_error(ValueError(f"invalid --web-port: {exc}"), json_output=True)
            return
        typer.echo(f"invalid --web-port: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    payload = public_support_payload(
        workdir=workdir,
        language=support_language,
        web_host=web_host,
        web_port=normalized_web_port,
    )
    if public_issue_bundle:
        _print_support_public_issue_bundle(
            workdir=workdir,
            language=support_language,
            web_host=web_host,
            web_port=normalized_web_port,
            payload=payload,
            json_output=json_output,
        )
        return
    if json_output:
        echo_json(payload)
        return
    for line in public_support_guidance_lines(payload):
        typer.echo(line)


def _print_support_public_issue_bundle(  # noqa: PLR0913 - Bundle recovery needs the normalized support context.
    *,
    workdir: Path | None,
    language: str,
    web_host: str | None,
    web_port: int | None,
    payload: Mapping[str, object],
    json_output: bool,
) -> None:
    if json_output:
        handle_error(ValueError("choose either --json or --public-issue-bundle, not both"), json_output=True)
        return
    if bool(payload.get("target_project_required")):
        rerun_command = _support_public_issue_bundle_target_rerun_command(payload)
        typer.echo(
            support_text(
                language,
                'public issue support bundle requires a target project; rerun from the target project with --workdir "$PWD".',
                '公开 issue 支持包需要目标项目；请先从目标项目使用 --workdir "$PWD" 重新运行。',
            ),
            err=True,
        )
        if rerun_command:
            typer.echo(
                support_text(
                    language,
                    f"from the target project, run: {rerun_command}",
                    f"请在目标项目中运行：{rerun_command}",
                ),
                err=True,
            )
        raise typer.Exit(code=2)
    report_workdir = Path(workdir).expanduser().resolve(strict=False) if workdir is not None else Path()
    try:
        report = build_doctor_report(
            workdir=report_workdir,
            web_host=web_host or DEFAULT_WEB_HOST,
            web_port=web_port if web_port is not None else DEFAULT_WEB_PORT,
        )
    except LooporaError as exc:
        handle_error(exc, recovery_workdir=report_workdir)
        return
    typer.echo(support_public_issue_bundle_text(doctor_public_json_payload(report), language=language))


def _support_public_issue_bundle_target_rerun_command(payload: Mapping[str, object]) -> str:
    commands = payload.get("commands") if isinstance(payload.get("commands"), Mapping) else {}
    command = str(commands.get("public_issue_bundle") or "").strip()
    if not command:
        return ""
    placeholder = shlex.quote(SUPPORT_WORKDIR_PLACEHOLDER)
    if f"--workdir {placeholder}" in command:
        return command.replace(f"--workdir {placeholder}", '--workdir "$PWD"', 1)
    if f"--workdir {SUPPORT_WORKDIR_PLACEHOLDER}" in command:
        return command.replace(f"--workdir {SUPPORT_WORKDIR_PLACEHOLDER}", '--workdir "$PWD"', 1)
    return ""
