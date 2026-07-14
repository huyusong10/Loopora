from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from loopora.agent_adapter_command_prefix import rewrite_loopora_help_commands
from loopora.cli_spec_recovery import exit_with_invalid_spec_file_recovery
from loopora.cli_spec_recovery import exit_with_missing_spec_file_recovery
from loopora.cli_spec_recovery import exit_with_missing_spec_init_path_recovery
from loopora.cli_spec_recovery import exit_with_missing_spec_write_source_recovery
from loopora.cli_spec_recovery import exit_with_spec_output_recovery
from loopora.cli_shared import (
    FromFileOption,
    JsonOutputOption,
    LocaleOption,
    OrchestrationIdOption,
    StrategyFileOption,
    StrategyPresetOption,
    echo_json,
    handle_error,
    role_note_sections_for_strategy_source,
    resolve_spec_template_strategy_source,
    spec_document_payload,
)
from loopora.markdown_tools import normalize_markdown_text
from loopora.service import LooporaError
from loopora.specs import (
    SpecError,
    init_spec_file_for_strategy_source,
    load_spec_file,
    read_and_compile,
    render_spec_template_for_strategy_source,
    resolve_spec_file_path,
    save_spec_file,
    spec_file_init_error,
    spec_file_read_error,
    spec_file_save_error,
)
from loopora.strategy_source import StrategySourceError

SPEC_HELP_EPILOG = (
    "Markdown specs are expert/recovery artifacts for direct create/run and reusable handoffs. For a new task, "
    "leave this group: run `loopora start` for route choice, use `loopora fit` when fit is uncertain, then choose "
    "either the Fit Guide/Web choices path through "
    '`loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742` or current-host same-Agent setup by choosing '
    'the matching entry with `loopora init <agent> --workdir "$PWD"` and `loopora doctor --workdir "$PWD"` before `/loopora-plan` and '
    "`/loopora-run`. "
    "Use `spec validate/read/write` to inspect or repair an artifact; these commands do not start runs."
)
SPEC_INIT_HELP_EPILOG = (
    "Creates a starter spec for recovery or expert direct-run paths when a reviewed Markdown contract is needed. "
    "It does not replace first-use review: for a new task, use `loopora start` and `loopora fit` first, then choose "
    "the Fit Guide/Web choices path or current-host same-Agent setup/readiness before `/loopora-plan` and "
    "`/loopora-run`."
)
SPEC_VALIDATE_HELP_EPILOG = (
    "Validation checks the Markdown artifact shape and reports the resolved check mode as JSON. It does not mean "
    "the task judgment has been reviewed, the Loop is READY, or a run can start safely."
)
SPEC_TEMPLATE_HELP_EPILOG = (
    "Template renders a starter Markdown artifact to stdout, or JSON with --json, using the selected Strategy Source. "
    "Use it for recovery, documentation, or piping; for a new task, route through `loopora start`, `loopora fit`, "
    "Fit Guide/Web choices, or same-Agent setup/readiness before `/loopora-plan` and running."
)
SPEC_READ_HELP_EPILOG = (
    "Read is an inspection surface: it returns structured Markdown, rendered HTML, and validation status without changing the spec, Loop, or run state."
)
SPEC_WRITE_HELP_EPILOG = (
    "Write is a repair surface for replacing one spec artifact from another Markdown file. It does not validate that "
    "the task has been reviewed or start a run; use `loopora spec validate`, then review through "
    "Fit Guide/Web choices or same-Agent setup/readiness before execution."
)
SpecFileArgument = Annotated[
    Path | None,
    typer.Argument(
        exists=False,
        file_okay=True,
        dir_okay=True,
        help="Path to a Markdown spec artifact; omit to get recovery guidance.",
    ),
]
SpecInitPathArgument = Annotated[
    Path | None,
    typer.Argument(
        exists=False,
        file_okay=True,
        dir_okay=True,
        help="Where to create the Markdown template; omit to get recovery guidance.",
    ),
]


def register_spec_commands(spec_app: typer.Typer) -> None:
    _register_spec_init_command(spec_app)
    _register_spec_validate_command(spec_app)
    _register_spec_template_command(spec_app)
    _register_spec_read_command(spec_app)
    _register_spec_write_command(spec_app)


def _register_spec_init_command(spec_app: typer.Typer) -> None:
    @spec_app.command("init", epilog=rewrite_loopora_help_commands(SPEC_INIT_HELP_EPILOG))
    def spec_init(
        path: SpecInitPathArgument = None,
        locale: LocaleOption = "zh",
        orchestration_id: OrchestrationIdOption = "",
        strategy_preset: StrategyPresetOption = "",
        strategy_file: StrategyFileOption = None,
    ) -> None:
        """Create a starter Markdown spec."""
        if path is None:
            exit_with_missing_spec_init_path_recovery()
        try:
            strategy_source = resolve_spec_template_strategy_source(
                orchestration_id=orchestration_id,
                strategy_preset=strategy_preset,
                strategy_file=strategy_file,
            )
            created = init_spec_file_for_strategy_source(path, locale=locale, strategy_source=strategy_source)
            typer.echo(f"created: {created}")
        except (LooporaError, StrategySourceError) as exc:
            handle_error(exc)
        except (FileExistsError, OSError) as exc:
            exit_with_spec_output_recovery(
                action="init",
                validation_error=spec_file_init_error(exc),
                json_output=False,
            )


def _register_spec_validate_command(spec_app: typer.Typer) -> None:
    @spec_app.command("validate", epilog=rewrite_loopora_help_commands(SPEC_VALIDATE_HELP_EPILOG))
    def spec_validate(
        path: SpecFileArgument = None,
    ) -> None:
        """Validate a Markdown spec and print the resolved check mode."""
        if path is None:
            exit_with_missing_spec_file_recovery(
                action="validate",
                retry_template="loopora spec validate <spec-path>",
                summary="Validate needs an existing Markdown spec artifact; it does not review task judgment or prove READY.",
            )
        try:
            resolved_path = resolve_spec_file_path(path)
            _, compiled = read_and_compile(path)
            echo_json(
                {
                    "ok": True,
                    "path": str(resolved_path),
                    "check_count": len(compiled["checks"]),
                    "check_mode": compiled["check_mode"],
                }
            )
        except (SpecError, FileNotFoundError, OSError) as exc:
            exit_with_invalid_spec_file_recovery(
                action="validate",
                retry_template="loopora spec validate <spec-path>",
                validation_error=spec_file_read_error(exc),
            )


def _register_spec_template_command(spec_app: typer.Typer) -> None:
    @spec_app.command("template", epilog=rewrite_loopora_help_commands(SPEC_TEMPLATE_HELP_EPILOG))
    def spec_template(
        locale: LocaleOption = "zh",
        orchestration_id: OrchestrationIdOption = "",
        strategy_preset: StrategyPresetOption = "",
        strategy_file: StrategyFileOption = None,
        *,
        json_output: JsonOutputOption = False,
    ) -> None:
        """Render a spec template without writing it to disk."""
        try:
            strategy_source = resolve_spec_template_strategy_source(
                orchestration_id=orchestration_id,
                strategy_preset=strategy_preset,
                strategy_file=strategy_file,
            )
            markdown_text = render_spec_template_for_strategy_source(locale=locale, strategy_source=strategy_source)
            if json_output:
                echo_json(
                    {
                        "ok": True,
                        "locale": locale,
                        "markdown": markdown_text,
                        "role_note_sections": role_note_sections_for_strategy_source(strategy_source),
                    }
                )
                return
            typer.echo(markdown_text)
        except (LooporaError, StrategySourceError, OSError) as exc:
            handle_error(exc, json_output=json_output)


def _register_spec_read_command(spec_app: typer.Typer) -> None:
    @spec_app.command("read", epilog=rewrite_loopora_help_commands(SPEC_READ_HELP_EPILOG))
    def spec_read(
        path: SpecFileArgument = None,
    ) -> None:
        """Read a spec document together with rendered HTML and validation status."""
        if path is None:
            exit_with_missing_spec_file_recovery(
                action="read",
                retry_template="loopora spec read <spec-path>",
                summary="Read needs an existing Markdown spec artifact; it only inspects the artifact and does not start work.",
            )
        try:
            resolved_path = resolve_spec_file_path(path)
            markdown_text = load_spec_file(path)
            echo_json(spec_document_payload(resolved_path, markdown_text))
        except (SpecError, FileNotFoundError, OSError) as exc:
            exit_with_invalid_spec_file_recovery(
                action="read",
                retry_template="loopora spec read <spec-path>",
                validation_error=spec_file_read_error(exc),
            )


def _register_spec_write_command(spec_app: typer.Typer) -> None:
    @spec_app.command("write", epilog=rewrite_loopora_help_commands(SPEC_WRITE_HELP_EPILOG))
    def spec_write(
        path: SpecFileArgument = None,
        from_file: FromFileOption = None,
    ) -> None:
        """Overwrite a spec document from another Markdown file."""
        if path is None:
            exit_with_missing_spec_file_recovery(
                action="write",
                retry_template="loopora spec write <spec-path> --from-file <source-spec-path>",
                summary="Write needs a target Markdown spec artifact; it repairs that artifact and does not start work.",
            )
        try:
            if from_file is None:
                exit_with_missing_spec_write_source_recovery()
            markdown_text = normalize_markdown_text(load_spec_file(from_file))
        except (SpecError, FileNotFoundError, OSError) as exc:
            exit_with_invalid_spec_file_recovery(
                action="write",
                retry_template="loopora spec write <spec-path> --from-file <source-spec-path>",
                validation_error=spec_file_read_error(exc),
            )
        try:
            resolved_path = save_spec_file(path, markdown_text)
            echo_json(spec_document_payload(resolved_path, markdown_text))
        except OSError as exc:
            exit_with_spec_output_recovery(
                action="write",
                validation_error=spec_file_save_error(exc),
                json_output=True,
            )
