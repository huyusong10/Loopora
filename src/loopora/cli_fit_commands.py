from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from loopora.agent_adapter_command_prefix import rewrite_loopora_help_commands
from loopora.cli_first_use_compact_output import compact_first_use_lines
from loopora.cli_fit_output import fit_cli_entry, print_fit_guidance
from loopora.cli_shared import JsonOutputOption, echo_json, handle_error
from loopora.first_use_web_guidance import (
    WEB_CREATION_CHOICE_LABEL,
    WEB_CREATION_ROUTE_CONTEXTS,
)
from loopora.fit_guidance import fit_guidance_payload, normalize_fit_guidance_language

FIT_HELP_EPILOG = (
    "Fit is a human pre-setup decision, not an automatic classifier. Start with `--task` and `--workdir`; "
    "the default output shows the current decision and next action. Use `--details` for every judgment field, "
    "route, and recovery diagnostic. Use `--prefer-direct --direct-path ...` when direct Agent work, `/goal`, "
    "hard checks, or the project process is enough. Setup remains blocked until a strong-fit review is complete. "
    f"After review, use {WEB_CREATION_CHOICE_LABEL} outside an Agent session for {WEB_CREATION_ROUTE_CONTEXTS}; "
    "inside Codex, Claude Code, or OpenCode, choose the current host entry and run only after READY review."
)


def register_fit_command(app: typer.Typer) -> None:
    @app.command(epilog=rewrite_loopora_help_commands(FIT_HELP_EPILOG))
    def fit(  # noqa: PLR0913 - Fit mirrors the public review input boundary.
        task: Annotated[
            str,
            typer.Option(
                "--task",
                "-t",
                help="Optional task statement to turn into a human fit-review draft without classifying it.",
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
                help=(
                    "User-confirmed Loopora fit reason to carry into the first /loopora-plan message draft; "
                    "alias: --strong-fit-signal."
                ),
            ),
        ] = "",
        evidence: Annotated[
            str,
            typer.Option(
                "--evidence",
                "--required-evidence",
                help="Required evidence to carry into the first /loopora-plan message draft; alias: --required-evidence.",
            ),
        ] = "",
        tradeoffs: Annotated[
            str,
            typer.Option(
                "--tradeoffs",
                "--judgment-tradeoffs",
                help="Judgment tradeoffs or fail-closed rules to carry into the draft; alias: --judgment-tradeoffs.",
            ),
        ] = "",
        direct_path: Annotated[
            str,
            typer.Option(
                "--direct-path",
                "--why-not-direct",
                help=(
                    "Optional direct-path judgment: why direct Agent work, /goal, hard checks, or the project "
                    "workflow is not enough; with --prefer-direct, what direct path is enough. Alias: --why-not-direct."
                ),
            ),
        ] = "",
        language: Annotated[
            str,
            typer.Option(
                "--language",
                help="Plain fit-guide language: en or zh; common aliases like en-US and zh-CN are normalized.",
            ),
        ] = "en",
        workdir: Annotated[
            Path | None,
            typer.Option(
                "--workdir",
                help="Target project directory for concrete Web/init/doctor route commands after a strong fit review.",
            ),
        ] = None,
        *,
        details: Annotated[
            bool,
            typer.Option(
                "--details",
                help="Show the full fit record, every route, alternatives, and recovery diagnostics.",
            ),
        ] = False,
        prefer_direct: Annotated[
            bool,
            typer.Option(
                "--prefer-direct",
                help="Record that direct Agent work, /goal, hard checks, or the project process is enough and block Loopora setup routes.",
            ),
        ] = False,
        json_output: JsonOutputOption = False,
    ) -> None:
        """Show when Loopora fits a task before setup or planning."""
        try:
            fit_language = normalize_fit_guidance_language(language)
        except ValueError as exc:
            if json_output:
                handle_error(ValueError(f"invalid --language: {exc}"), json_output=True)
                return
            typer.echo(f"invalid --language: {exc}", err=True)
            raise typer.Exit(code=2) from exc
        payload = fit_guidance_payload(
            task,
            loopora_fit_reason=fit_reason,
            fake_done_risks=fake_done,
            required_evidence=evidence,
            judgment_tradeoffs=tradeoffs,
            direct_path_check=direct_path,
            prefer_direct=prefer_direct,
            language=fit_language,
            cli_entry=fit_cli_entry(),
            workdir=workdir,
            preflight_web_route=True,
        )
        if json_output:
            echo_json(payload)
            return
        if details:
            print_fit_guidance(payload)
            return
        for line in compact_first_use_lines(payload, surface="fit"):
            typer.echo(line)
