from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from loopora.cli_shared import ArchetypeOption, LocaleOption, echo_json, handle_error
from loopora.strategy_source import (
    StrategySourceError,
    available_strategy_prompt_templates,
    builtin_strategy_prompt_markdown,
    load_strategy_prompt_file,
    validate_strategy_prompt_markdown,
)


def register_prompt_commands(prompts_app: typer.Typer) -> None:
    @prompts_app.command("list")
    def list_prompts() -> None:
        """List built-in prompt templates."""
        try:
            echo_json(available_strategy_prompt_templates())
        except StrategySourceError as exc:
            handle_error(exc)

    @prompts_app.command("template")
    def prompt_template(
        prompt_ref: Annotated[str, typer.Argument(..., help="Built-in prompt template ref.")],
        locale: LocaleOption = "zh",
    ) -> None:
        """Print one built-in prompt template."""
        try:
            typer.echo(builtin_strategy_prompt_markdown(prompt_ref, locale=locale))
        except StrategySourceError as exc:
            handle_error(exc)

    @prompts_app.command("validate")
    def prompt_validate(
        path: Annotated[Path, typer.Argument(..., exists=True, help="Path to the prompt Markdown file to validate.")],
        archetype: ArchetypeOption = "",
    ) -> None:
        """Validate prompt Markdown and print parsed metadata."""
        try:
            markdown_text = load_strategy_prompt_file(path)
            metadata, body = validate_strategy_prompt_markdown(markdown_text, expected_archetype=archetype or None)
            echo_json({"ok": True, "metadata": metadata, "body": body})
        except (StrategySourceError, OSError) as exc:
            handle_error(exc)
