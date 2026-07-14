from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer

from loopora.agent_adapter_command_prefix import (
    rewrite_loopora_help_commands,
)
from loopora.cli_diagnose_commands import (
    DOCTOR_HELP_EPILOG,
    DoctorLanguageOption,
    DoctorWorkdirOption,
    DoctorWebHostOption,
    DoctorWebPortOption,
    PublicJsonOutputOption,
    StrictDoctorOption,
    run_doctor_command,
)
from loopora.cli_demo_commands import register_demo_command as _register_demo_command
from loopora.cli_fit_commands import register_fit_command as _register_fit_command
from loopora.cli_group_help import print_help_when_no_subcommand
from loopora.cli_run_commands import register_run_command as _register_run_command
from loopora.cli_serve_commands import register_serve_command as _register_serve_command
from loopora.cli_shared import JsonOutputOption, get_service, echo_json, handle_error, logger, print_run_result
from loopora.cli_start_commands import register_start_command as _register_start_command
from loopora.cli_status_commands import register_status_command as _register_status_command
from loopora.cli_support_output import print_public_support_command_output
from loopora.diagnostics import log_event
from loopora.diagnose_doctor_identity import package_identity_report, package_source_label
from loopora.service import LooporaError
from loopora.settings import configure_logging
from loopora.specs import SpecError
from loopora.support_guidance import (
    SUPPORT_HELP_EPILOG,
)

SupportWorkdirOption = Annotated[
    Path | None,
    typer.Option(
        "--workdir",
        file_okay=True,
        dir_okay=True,
        exists=False,
        help="Project directory to use in the copyable public doctor command.",
    ),
]
SupportLanguageOption = Annotated[
    str,
    typer.Option(
        "--language",
        help="Plain support-guide language: en or zh; common aliases like en-US and zh-CN are normalized.",
    ),
]
SupportWebHostOption = Annotated[
    str | None,
    typer.Option("--web-host", help="Web bind host to pass through to the redacted public doctor command."),
]
SupportWebPortOption = Annotated[
    str | None,
    typer.Option("--web-port", help="Web bind port to pass through to the redacted public doctor command."),
]
SupportPublicIssueBundleOption = Annotated[
    bool,
    typer.Option(
        "--public-issue-bundle",
        help=("Run redacted public diagnostics for --workdir and print one pasteable public issue support bundle. Cannot be combined with --json."),
    ),
]


def register_root_commands(app: typer.Typer) -> None:
    _register_main_callback(app)
    _register_version_command(app)
    _register_start_command(app)
    _register_status_command(app)
    _register_fit_command(app)
    _register_demo_command(app)
    _register_doctor_command(app)
    _register_support_command(app)
    _register_run_command(app)
    _register_serve_command(app)
    _register_execute_run_worker_command(app)


def _register_main_callback(app: typer.Typer) -> None:
    @app.callback(invoke_without_command=True)
    def main(
        ctx: typer.Context,
        *,
        version_requested: Annotated[
            bool,
            typer.Option(
                "--version",
                callback=_version_callback,
                is_eager=True,
                help="Show the installed Loopora version and exit.",
            ),
        ] = False,
    ) -> None:
        _ = version_requested
        if ctx.invoked_subcommand not in {"demo", "status"}:
            configure_logging()
        print_help_when_no_subcommand(ctx)


def _version_callback(value: object) -> None:
    if not value:
        return
    typer.echo(version_identity_text())
    raise typer.Exit


def version_identity_text() -> str:
    package = package_identity_report()
    source = package_source_label(package)
    source_note = f" ({source})" if source else ""
    return f"loopora {package.get('version')}{source_note}"


def version_identity_payload() -> dict[str, object]:
    package = package_identity_report()
    source = package_source_label(package)
    payload = {
        "schema_version": 1,
        "redacted": True,
        "name": package.get("name"),
        "version": package.get("version"),
        "source_revision": package.get("source_revision"),
        "source_tree_status": package.get("source_tree_status"),
        "source_label": source,
    }
    return {"version_identity_summary": dict(payload), **payload}


def _register_version_command(app: typer.Typer) -> None:
    @app.command()
    def version(
        *,
        json_output: JsonOutputOption = False,
    ) -> None:
        """Show compact package/source identity without readiness diagnostics."""
        if json_output:
            echo_json(version_identity_payload())
            return
        typer.echo(version_identity_text())


def _register_doctor_command(app: typer.Typer) -> None:
    @app.command(epilog=rewrite_loopora_help_commands(DOCTOR_HELP_EPILOG))
    def doctor(
        workdir: DoctorWorkdirOption = None,
        language: DoctorLanguageOption = "en",
        web_host: DoctorWebHostOption = "127.0.0.1",
        web_port: DoctorWebPortOption = 8742,
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


def _register_support_command(app: typer.Typer) -> None:
    @app.command(epilog=rewrite_loopora_help_commands(SUPPORT_HELP_EPILOG))
    def support(
        workdir: SupportWorkdirOption = None,
        language: SupportLanguageOption = "en",
        web_host: SupportWebHostOption = None,
        web_port: SupportWebPortOption = None,
        *,
        json_output: JsonOutputOption = False,
        public_issue_bundle: SupportPublicIssueBundleOption = False,
    ) -> None:
        """Show safe public support and reporting guidance."""
        print_public_support_command_output(
            workdir=workdir,
            language=language,
            web_host=web_host,
            web_port=web_port,
            json_output=json_output,
            public_issue_bundle=public_issue_bundle,
        )


def _register_execute_run_worker_command(app: typer.Typer) -> None:
    @app.command("_execute-run", hidden=True)
    def execute_run_worker(run_id: str = typer.Argument(..., help="Run ID.")) -> None:
        """Internal helper that executes a queued run in a dedicated background process."""
        try:
            service = get_service()
            result = service.execute_run(run_id)
            log_event(
                logger,
                logging.INFO,
                "cli.background_worker.completed",
                "Background worker finished run execution",
                run_id=result["id"],
                loop_id=result.get("loop_id"),
                status=result["status"],
            )
            print_run_result(result)
        except (LooporaError, SpecError) as exc:
            handle_error(exc)
