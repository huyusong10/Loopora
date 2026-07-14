from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.cli_resource_recovery import echo_resource_recovery_json
from loopora.cli_shared import ArchetypeOption, LocaleOption, echo_json, handle_error
from loopora.strategy_source import (
    StrategySourceError,
    available_strategy_prompt_templates,
    builtin_strategy_prompt_markdown,
    load_strategy_prompt_file,
    validate_strategy_prompt_markdown,
)


PROMPTS_HELP_EPILOG = (
    "Prompt commands are expert Strategy Source asset tools. Use them to list built-in role prompt refs, "
    "render a Markdown template for inspection, or validate a custom role prompt file before attaching it "
    "to a reviewed Loop contract. These commands create no Loops, perform no review, and start no runs. "
    "For first-use planning, leave this group: run `loopora start` for route choice, use `loopora fit` when fit is "
    "uncertain, then choose the Fit Guide/Web choices path through "
    '`loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742` or current-host same-Agent setup by choosing '
    'the matching entry with `loopora init <agent> --workdir "$PWD"` and `loopora doctor --workdir "$PWD"` before '
    "`/loopora-plan` and `/loopora-run`. `loopora spec` remains an expert/recovery artifact surface, not a shortcut "
    "to READY."
)

PROMPTS_LIST_HELP_EPILOG = (
    "Lists reusable built-in role prompt refs for Strategy Source authors and reviewers. This is an inventory "
    "surface only; choose a Loop creation path through fit, Agent planning, Web conversation, import, or an "
    "expert reviewed spec before running work."
)

PROMPTS_TEMPLATE_HELP_EPILOG = (
    "Prints one built-in prompt template as a Markdown artifact so experts can inspect or copy it into a "
    "custom Strategy Source. The rendered template is not a runnable Loop by itself and does not update "
    "saved role definitions."
)

PROMPTS_VALIDATE_HELP_EPILOG = (
    "Validates a prompt Markdown file as an expert asset check. Success means the prompt file shape is usable "
    "for a Strategy Source; it does not prove the overall Loop is reviewed, READY, or safe to run."
)
PromptTemplateRefArgument = Annotated[
    str | None,
    typer.Argument(help="Built-in prompt template ref; omit to get recovery guidance."),
]
PromptFileArgument = Annotated[
    Path | None,
    typer.Argument(
        exists=False,
        file_okay=True,
        dir_okay=True,
        help="Path to the prompt Markdown file to validate; omit to get recovery guidance.",
    ),
]


def register_prompt_commands(prompts_app: typer.Typer) -> None:
    @prompts_app.command("list", epilog=PROMPTS_LIST_HELP_EPILOG)
    def list_prompts() -> None:
        """List built-in prompt templates."""
        try:
            echo_json(available_strategy_prompt_templates())
        except StrategySourceError as exc:
            handle_error(exc, json_output=True)

    @prompts_app.command("template", epilog=PROMPTS_TEMPLATE_HELP_EPILOG)
    def prompt_template(
        prompt_ref: PromptTemplateRefArgument = None,
        locale: LocaleOption = "zh",
    ) -> None:
        """Print one built-in prompt template."""
        if prompt_ref is None or not prompt_ref.strip():
            _exit_with_missing_prompt_template_ref_recovery()
        prompt_ref = prompt_ref.strip()
        try:
            typer.echo(builtin_strategy_prompt_markdown(prompt_ref, locale=locale))
        except StrategySourceError as exc:
            handle_error(exc)

    @prompts_app.command("validate", epilog=PROMPTS_VALIDATE_HELP_EPILOG)
    def prompt_validate(
        path: PromptFileArgument = None,
        archetype: ArchetypeOption = "",
    ) -> None:
        """Validate prompt Markdown and print parsed metadata."""
        if path is None:
            _exit_with_missing_prompt_file_recovery()
        try:
            markdown_text = load_strategy_prompt_file(path)
            metadata, body = validate_strategy_prompt_markdown(markdown_text, expected_archetype=archetype or None)
            echo_json({"ok": True, "metadata": metadata, "body": body})
        except (StrategySourceError, OSError) as exc:
            _exit_with_invalid_prompt_file_recovery(str(exc))


def _exit_with_missing_prompt_template_ref_recovery() -> None:
    echo_resource_recovery_json(
        {
            "resource_recovery": "missing_prompt_template_ref",
            "status": "blocked_by_missing_prompt_template_ref",
            "resource": "Strategy Source prompt template",
            "action": "template",
            "required_identifier": "prompt_ref",
            "required_identifier_label": "Built-in prompt template ref",
            "summary": "Template needs a built-in prompt ref; list prompt refs first, or leave prompts for normal start/fit planning.",
            "next_actions": [
                {
                    "kind": "list_prompt_templates",
                    "label": "List built-in prompt refs",
                    "command": copyable_loopora_command("loopora prompts list"),
                },
                {
                    "kind": "retry_after_prompt_ref_choice",
                    "label": "Render a built-in prompt template",
                    "command_template": copyable_loopora_command("loopora prompts template <prompt-ref>"),
                },
                *_prompt_first_use_recovery_actions(),
            ],
        }
    )
    raise typer.Exit(code=1)


def _exit_with_missing_prompt_file_recovery() -> None:
    echo_resource_recovery_json(
        {
            "resource_recovery": "missing_prompt_file_input",
            "status": "blocked_by_missing_prompt_file",
            "resource": "Strategy Source prompt file",
            "action": "validate",
            "required_identifier": "prompt_path",
            "required_identifier_label": "Path to a prompt Markdown file",
            "summary": "Validate needs a custom prompt Markdown file; it checks an expert asset and does not prove READY.",
            "next_actions": [
                {
                    "kind": "retry_after_prompt_file_choice",
                    "label": "Validate a custom prompt file",
                    "command_template": copyable_loopora_command("loopora prompts validate <prompt-file>"),
                },
                {
                    "kind": "list_prompt_templates",
                    "label": "List built-in prompt refs",
                    "command": copyable_loopora_command("loopora prompts list"),
                },
                {
                    "kind": "render_prompt_template",
                    "label": "Render a built-in prompt template",
                    "command_template": copyable_loopora_command("loopora prompts template <prompt-ref>"),
                },
                *_prompt_first_use_recovery_actions(),
            ],
        }
    )
    raise typer.Exit(code=1)


def _exit_with_invalid_prompt_file_recovery(validation_error: str) -> None:
    echo_resource_recovery_json(
        {
            "resource_recovery": "invalid_prompt_file_input",
            "status": "blocked_by_prompt_file",
            "resource": "Strategy Source prompt file",
            "action": "validate",
            "validation_error": validation_error,
            "summary": "Prompt validation needs a readable custom prompt Markdown file; repair it or choose another prompt file.",
            "next_actions": [
                {
                    "kind": "repair_prompt_file",
                    "label": "Repair the selected prompt file",
                    "validation_error": validation_error,
                },
                {
                    "kind": "choose_prompt_file",
                    "label": "Choose another prompt file",
                    "command_template": copyable_loopora_command("loopora prompts validate <prompt-file>"),
                },
                {
                    "kind": "list_prompt_templates",
                    "label": "List built-in prompt refs",
                    "command": copyable_loopora_command("loopora prompts list"),
                },
                {
                    "kind": "render_prompt_template",
                    "label": "Render a built-in prompt template",
                    "command_template": copyable_loopora_command("loopora prompts template <prompt-ref>"),
                },
                *_prompt_first_use_recovery_actions(),
            ],
        }
    )
    raise typer.Exit(code=1)


def _prompt_first_use_recovery_actions() -> list[dict[str, str]]:
    return [
        {
            "kind": "start_route_chooser",
            "label": "Choose the safe route for a new task",
            "command": copyable_loopora_command("loopora start"),
        },
        {
            "kind": "check_fit_first",
            "label": "Check Loopora fit when uncertain",
            "command": copyable_loopora_command("loopora fit"),
        },
        {
            "kind": "open_web_creation_choices",
            "label": "Open Fit Guide/Web choices",
            "command": copyable_loopora_command('loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742'),
        },
    ]
