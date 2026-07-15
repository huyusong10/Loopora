from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

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
)
from loopora.strategy_source import StrategySourceError


def register_spec_commands(spec_app: typer.Typer) -> None:
    _register_spec_init_command(spec_app)
    _register_spec_validate_command(spec_app)
    _register_spec_template_command(spec_app)
    _register_spec_read_command(spec_app)
    _register_spec_write_command(spec_app)


def _register_spec_init_command(spec_app: typer.Typer) -> None:
    @spec_app.command("init")
    def spec_init(
        path: Annotated[Path, typer.Argument(..., help="Where to create the Markdown template.")],
        locale: LocaleOption = "zh",
        strategy_preset: StrategyPresetOption = "",
    ) -> None:
        """Create a starter Markdown spec."""
        try:
            strategy_source = {"preset": strategy_preset} if strategy_preset else None
            created = init_spec_file_for_strategy_source(path, locale=locale, strategy_source=strategy_source)
            typer.echo(f"created: {created}")
        except (FileExistsError, OSError) as exc:
            handle_error(exc)


def _register_spec_validate_command(spec_app: typer.Typer) -> None:
    @spec_app.command("validate")
    def spec_validate(
        path: Annotated[Path, typer.Argument(..., exists=True, help="Path to the Markdown spec to validate.")],
    ) -> None:
        """Validate a Markdown spec and print the resolved check mode."""
        try:
            _, compiled = read_and_compile(path)
            echo_json(
                {
                    "ok": True,
                    "path": str(path.resolve()),
                    "check_count": len(compiled["checks"]),
                    "check_mode": compiled["check_mode"],
                }
            )
        except (SpecError, FileNotFoundError, OSError) as exc:
            handle_error(exc)


def _register_spec_template_command(spec_app: typer.Typer) -> None:
    @spec_app.command("template")
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
            handle_error(exc)


def _register_spec_read_command(spec_app: typer.Typer) -> None:
    @spec_app.command("read")
    def spec_read(
        path: Annotated[Path, typer.Argument(..., exists=True, help="Path to the Markdown spec to read.")],
    ) -> None:
        """Read a spec document together with rendered HTML and validation status."""
        try:
            markdown_text = load_spec_file(path)
            echo_json(spec_document_payload(path, markdown_text))
        except (SpecError, FileNotFoundError, OSError) as exc:
            handle_error(exc)


def _register_spec_write_command(spec_app: typer.Typer) -> None:
    @spec_app.command("write")
    def spec_write(
        path: Annotated[Path, typer.Argument(..., help="Spec path to overwrite.")],
        from_file: FromFileOption = None,
    ) -> None:
        """Overwrite a spec document from another Markdown file."""
        try:
            if from_file is None:
                raise LooporaError("--from-file is required")
            markdown_text = normalize_markdown_text(load_spec_file(from_file))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(markdown_text, encoding="utf-8")
            echo_json(spec_document_payload(path, markdown_text))
        except (LooporaError, SpecError, OSError) as exc:
            handle_error(exc)
