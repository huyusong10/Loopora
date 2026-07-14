from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from loopora.agent_adapter_command_prefix import rewrite_loopora_help_commands
from loopora.cli_common import get_service
from loopora.cli_diagnose_doctor_output import print_doctor_report
from loopora.cli_diagnose_source_checkout import exit_if_source_checkout_target_required
from loopora.cli_shared import JsonOutputOption, echo_json, handle_error
from loopora.diagnose_doctor import build_doctor_report, doctor_json_payload, doctor_public_json_payload
from loopora.diagnose_doctor_web_state import DEFAULT_WEB_HOST, DEFAULT_WEB_PORT
from loopora.event_redaction_audit import audit_event_redaction
from loopora.fit_guidance import normalize_fit_guidance_language
from loopora.service import LooporaError

FixOption = Annotated[
    bool,
    typer.Option(
        "--fix",
        help="Rewrite DB and local event files that current redaction rules can safely repair.",
    ),
]
PublicJsonOutputOption = Annotated[
    bool,
    typer.Option(
        "--public-json",
        help="Print a path-free diagnostics payload suitable for public issue reports.",
    ),
]
StrictDoctorOption = Annotated[
    bool,
    typer.Option(
        "--strict",
        help="Exit non-zero unless same-Agent project entry, App state, and Web readiness all pass without warnings.",
    ),
]
DoctorWebHostOption = Annotated[
    str,
    typer.Option("--web-host", help="Web bind host to check and print in readiness guidance."),
]
DoctorWebPortOption = Annotated[
    str,
    typer.Option("--web-port", help="Web bind port to check and print in readiness guidance."),
]
DoctorWorkdirOption = Annotated[
    Path | None,
    typer.Option(
        "--workdir",
        file_okay=True,
        dir_okay=True,
        exists=False,
        show_default=False,
        help="Target project directory where the Coding Agent will work; source checkouts should pass this explicitly.",
    ),
]
DoctorLanguageOption = Annotated[
    str,
    typer.Option(
        "--language",
        help="Plain Doctor language: en or zh; common aliases like en-US and zh-CN are normalized.",
    ),
]
DOCTOR_HELP_EPILOG = (
    "`loopora init current --workdir \"$PWD\"` already runs this read-only readiness checkpoint after installing the detected host. "
    "Use doctor independently after an explicit `loopora init <agent>` fallback, for deeper diagnostics, or in automation; "
    "when checking a custom Web target, pass the same --web-host/--web-port here so recovery and Web start "
    "guidance do not drift. Use --json for automation, --public-json for redacted public issue reports, and "
    "--strict when App/Web warnings should fail automation."
)
DIAGNOSE_HELP_EPILOG = (
    "Use root `loopora doctor --workdir \"$PWD\"` as the ordinary read-only first-use readiness checkpoint; "
    "`loopora diagnose doctor --workdir \"$PWD\"` is the diagnostics-group alias for the same report. "
    "Use event-redaction only as a maintainer diagnostics/audit surface; it prints JSON by default and mutates DB "
    "or local event files only when `--fix` is explicitly passed."
)
EVENT_REDACTION_HELP_EPILOG = (
    "Event redaction is a maintainer audit for stored DB events and local event files. Without `--fix` it only "
    "reports findings as JSON; with `--fix` it rewrites only entries current redaction rules can safely repair."
)


def register_diagnose_commands(app: typer.Typer) -> None:
    @app.command("doctor", epilog=rewrite_loopora_help_commands(DOCTOR_HELP_EPILOG))
    def diagnose_doctor(  # noqa: PLR0913 - Typer callback mirrors the public doctor option boundary.
        workdir: DoctorWorkdirOption = None,
        language: DoctorLanguageOption = "en",
        web_host: DoctorWebHostOption = DEFAULT_WEB_HOST,
        web_port: DoctorWebPortOption = DEFAULT_WEB_PORT,
        *,
        json_output: JsonOutputOption = False,
        public_json_output: PublicJsonOutputOption = False,
        strict: StrictDoctorOption = False,
    ) -> None:
        """Report local first-use readiness without installing or repairing files."""
        run_doctor_command(
            workdir=workdir,
            language=language,
            web_host=web_host,
            web_port=web_port,
            json_output=json_output,
            public_json_output=public_json_output,
            strict=strict,
        )

    @app.command("event-redaction", epilog=EVENT_REDACTION_HELP_EPILOG)
    def diagnose_event_redaction(
        *,
        fix: FixOption = False,
    ) -> None:
        try:
            service = get_service()
            report = audit_event_redaction(service.repository, fix=fix)
        except LooporaError as exc:
            handle_error(exc, json_output=True, recovery_workdir=Path())
            return
        typer.echo(json.dumps(report, ensure_ascii=False, indent=2))


def run_doctor_command(  # noqa: PLR0913 - shared CLI doctor runner keeps root and diagnose options aligned.
    *,
    workdir: Path | None,
    language: str = "en",
    web_host: str = DEFAULT_WEB_HOST,
    web_port: int | str = DEFAULT_WEB_PORT,
    json_output: bool,
    public_json_output: bool = False,
    strict: bool = False,
) -> None:
    try:
        normalized_language = normalize_fit_guidance_language(language)
    except ValueError as exc:
        handle_error(exc, json_output=json_output or public_json_output, recovery_workdir=workdir)
        return
    try:
        normalized_web_port = normalize_web_port(web_port)
    except ValueError as exc:
        if json_output or public_json_output:
            handle_error(ValueError(f"invalid --web-port: {exc}"), json_output=True)
            return
        typer.echo(f"invalid --web-port: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    _exit_if_doctor_json_modes_conflict(json_output=json_output, public_json_output=public_json_output)
    exit_if_source_checkout_target_required(
        workdir=workdir,
        web_host=web_host,
        web_port=normalized_web_port,
        json_output=json_output,
        public_json_output=public_json_output,
        language=normalized_language,
    )
    try:
        report = build_doctor_report(
            workdir=Path() if workdir is None else workdir,
            web_host=web_host,
            web_port=normalized_web_port,
        )
    except LooporaError as exc:
        handle_error(exc, json_output=json_output)
        return
    if public_json_output:
        echo_json(doctor_public_json_payload(report))
    elif json_output:
        echo_json(doctor_json_payload(report))
    else:
        print_doctor_report(report, strict=strict, language=normalized_language)
    if not _doctor_exit_ready(report, strict=strict):
        raise typer.Exit(code=1)


def _exit_if_doctor_json_modes_conflict(*, json_output: bool, public_json_output: bool) -> None:
    if json_output and public_json_output:
        handle_error(ValueError("choose either --json or --public-json, not both"), json_output=True)


def normalize_web_port(value: int | str) -> int:
    try:
        port = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError("must be an integer between 1 and 65535") from exc
    if port < 1 or port > 65535:
        raise ValueError("must be between 1 and 65535")
    return port


def _doctor_exit_ready(report: dict, *, strict: bool) -> bool:
    if strict:
        return report.get("strict_ready") is True
    return report.get("agent_entry_ready", report.get("ready")) is True
