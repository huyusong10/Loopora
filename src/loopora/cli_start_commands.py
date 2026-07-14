from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from loopora.agent_adapter_command_prefix import rewrite_loopora_help_commands
from loopora.cli_first_use_compact_output import compact_first_use_lines
from loopora.cli_fit_output import fit_cli_entry
from loopora.cli_shared import JsonOutputOption, echo_json, handle_error
from loopora.fit_guidance import normalize_fit_guidance_language
from loopora.start_guidance import START_HELP_EPILOG, start_guidance_lines, start_guidance_payload

StartWorkdirOption = Annotated[
    Path | None,
    typer.Option(
        "--workdir",
        file_okay=True,
        dir_okay=True,
        exists=False,
        help="Target project directory for readiness gating and route commands.",
    ),
]
StartLanguageOption = Annotated[
    str,
    typer.Option(
        "--language",
        help="Start guide output language: en or zh; common aliases like en-US and zh-CN are normalized.",
    ),
]


def register_start_command(app: typer.Typer) -> None:
    @app.command(epilog=rewrite_loopora_help_commands(START_HELP_EPILOG))
    def start(  # noqa: PLR0913 - Start mirrors the fit-review input boundary.
        task: Annotated[
            str,
            typer.Option(
                "--task",
                "-t",
                help="Optional task statement for a first-use route and /loopora-plan handoff preview.",
            ),
        ] = "",
        fake_done: Annotated[
            str,
            typer.Option(
                "--fake-done",
                "--fake-done-risks",
                help="Fake-done risk to carry into the first /loopora-plan message draft; alias: --fake-done-risks.",
            ),
        ] = "",
        fit_reason: Annotated[
            str,
            typer.Option(
                "--fit-reason",
                "--strong-fit-signal",
                help="User-confirmed Loopora fit reason to carry into the first /loopora-plan message draft.",
            ),
        ] = "",
        evidence: Annotated[
            str,
            typer.Option(
                "--evidence",
                "--required-evidence",
                help="Required evidence to carry into the first /loopora-plan message draft.",
            ),
        ] = "",
        tradeoffs: Annotated[
            str,
            typer.Option(
                "--tradeoffs",
                "--judgment-tradeoffs",
                help="Judgment tradeoffs or fail-closed rules to carry into the first /loopora-plan draft.",
            ),
        ] = "",
        direct_path: Annotated[
            str,
            typer.Option(
                "--direct-path",
                "--why-not-direct",
                help=(
                    "Optional direct-path judgment: why direct work is not enough for a strong-fit review, "
                    "or what direct path is enough with --prefer-direct."
                ),
            ),
        ] = "",
        workdir: StartWorkdirOption = None,
        language: StartLanguageOption = "en",
        *,
        details: Annotated[
            bool,
            typer.Option(
                "--details",
                help="Show the full fit record, route readiness, alternatives, and recovery diagnostics.",
            ),
        ] = False,
        prefer_direct: Annotated[
            bool,
            typer.Option(
                "--prefer-direct",
                help="Record that the human fit review chose direct Agent work, /goal, hard checks, or the project process instead of Loopora setup.",
            ),
        ] = False,
        json_output: JsonOutputOption = False,
    ) -> None:
        """Choose the first safe Loopora route without mutating local state."""
        try:
            start_language = normalize_fit_guidance_language(language)
        except ValueError as exc:
            if json_output:
                handle_error(ValueError(f"invalid --language: {exc}"), json_output=True)
                return
            typer.echo(f"invalid --language: {exc}", err=True)
            raise typer.Exit(code=2) from exc
        payload = start_guidance_payload(
            {
                "task": task,
                "fit_reason": fit_reason,
                "fake_done": fake_done,
                "evidence": evidence,
                "tradeoffs": tradeoffs,
                "direct_path": direct_path,
                "prefer_direct": prefer_direct,
            },
            workdir=workdir,
            language=start_language,
            cli_entry=fit_cli_entry(),
            preflight_web_route=True,
        )
        if json_output:
            echo_json(payload)
            return
        lines = start_guidance_lines(payload) if details else compact_first_use_lines(payload, surface="start")
        for line in lines:
            typer.echo(line)
