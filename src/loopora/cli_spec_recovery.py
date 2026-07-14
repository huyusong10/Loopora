from __future__ import annotations

import typer

from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.cli_resource_recovery import echo_resource_recovery_json
from loopora.cli_resource_recovery import project_resource_recovery_action_contract
from loopora.cli_shared import echo_json
from loopora.specs import (
    SPEC_FILE_DIRECTORY_ERROR,
    SPEC_FILE_EXISTS_ERROR,
    SPEC_FILE_INIT_ERROR,
    SPEC_FILE_SAVE_ERROR,
)


def exit_with_missing_spec_init_path_recovery() -> None:
    echo_resource_recovery_json(
        {
            "resource_recovery": "missing_spec_target_path",
            "status": "blocked_by_missing_spec_target_path",
            "resource": "Markdown spec",
            "action": "init",
            "required_identifier": "spec_path",
            "required_identifier_label": "Target path for a Markdown spec artifact",
            "summary": "Spec init needs a target Markdown file path; it creates a starter artifact and does not review task judgment or prove READY.",
            "next_actions": [
                {
                    "kind": "retry_after_spec_target_choice",
                    "label": "Choose where to create the starter spec",
                    "command_template": copyable_loopora_command("loopora spec init <spec-path>"),
                },
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
            ],
        }
    )
    raise typer.Exit(code=1)


def exit_with_missing_spec_file_recovery(*, action: str, retry_template: str, summary: str) -> None:
    echo_resource_recovery_json(
        {
            "resource_recovery": "missing_spec_file_input",
            "status": "blocked_by_missing_spec_file",
            "resource": "Markdown spec",
            "action": action,
            "required_identifier": "spec_path",
            "required_identifier_label": "Path to a Markdown spec artifact",
            "summary": summary,
            "next_actions": [
                {
                    "kind": "retry_after_spec_choice",
                    "label": "Choose an existing Markdown spec",
                    "command_template": copyable_loopora_command(retry_template),
                },
                {
                    "kind": "create_starter_spec",
                    "label": "Create a starter spec for recovery or expert direct-run",
                    "command_template": copyable_loopora_command("loopora spec init <spec-path>"),
                },
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
            ],
        }
    )
    raise typer.Exit(code=1)


def exit_with_missing_spec_write_source_recovery() -> None:
    echo_resource_recovery_json(
        {
            "resource_recovery": "missing_spec_source_file_input",
            "status": "blocked_by_missing_spec_source_file",
            "resource": "Markdown spec source",
            "action": "write",
            "required_identifier": "source_spec_path",
            "required_identifier_label": "Source Markdown spec path for --from-file",
            "summary": "Spec write needs a source Markdown spec artifact to copy from before it can repair the target spec.",
            "next_actions": [
                {
                    "kind": "choose_source_spec_file",
                    "label": "Choose a source Markdown spec",
                    "command_template": copyable_loopora_command("loopora spec write <spec-path> --from-file <source-spec-path>"),
                },
                {
                    "kind": "create_starter_source_spec",
                    "label": "Create a starter source spec",
                    "command_template": copyable_loopora_command("loopora spec init <source-spec-path>"),
                },
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
            ],
        }
    )
    raise typer.Exit(code=1)


def exit_with_invalid_spec_file_recovery(*, action: str, retry_template: str, validation_error: str) -> None:
    echo_resource_recovery_json(
        {
            "resource_recovery": "invalid_spec_file_input",
            "status": "blocked_by_spec_file",
            "resource": "Markdown spec",
            "action": action,
            "validation_error": validation_error,
            "summary": (
                "Spec artifact commands need a readable Markdown spec; repair the artifact or choose another spec before relying on validate/read/write."
            ),
            "next_actions": [
                {
                    "kind": "repair_spec_file",
                    "label": "Repair the selected Markdown spec",
                    "validation_error": validation_error,
                },
                {
                    "kind": "choose_spec_file",
                    "label": "Choose another Markdown spec",
                    "command_template": copyable_loopora_command(retry_template),
                },
                {
                    "kind": "create_starter_spec",
                    "label": "Create a starter spec for recovery or expert direct-run",
                    "command_template": copyable_loopora_command("loopora spec init <spec-path>"),
                },
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
            ],
        }
    )
    raise typer.Exit(code=1)


def exit_with_spec_output_recovery(
    *,
    action: str,
    validation_error: str,
    json_output: bool,
) -> None:
    payload = project_resource_recovery_action_contract(
        {
            "resource_recovery": "invalid_spec_output_target",
            "status": "blocked_by_spec_output",
            "resource": "Markdown spec",
            "action": action,
            "output_state": _spec_output_state(validation_error),
            "validation_error": validation_error,
            "summary": _spec_output_recovery_summary(action),
            "next_actions": _spec_output_recovery_actions(action),
        }
    )
    if json_output:
        echo_json(payload)
    else:
        _print_spec_output_recovery(payload)
    raise typer.Exit(code=1)


def _spec_output_state(validation_error: str) -> str:
    if validation_error == SPEC_FILE_DIRECTORY_ERROR:
        return "directory"
    if validation_error == SPEC_FILE_EXISTS_ERROR:
        return "exists"
    if validation_error in {SPEC_FILE_INIT_ERROR, SPEC_FILE_SAVE_ERROR}:
        return "write_failed"
    return "unavailable"


def _spec_output_recovery_summary(action: str) -> str:
    if action == "write":
        return "Choose a writable Markdown spec target path before replacing the artifact."
    return "Choose a writable Markdown spec target path, or print the starter template instead of writing it."


def _spec_output_recovery_actions(action: str) -> list[dict[str, str]]:
    if action == "write":
        return [
            {
                "kind": "choose_spec_output_file",
                "label": "Choose a writable target Markdown spec",
                "command_template": copyable_loopora_command("loopora spec write <spec-path> --from-file <source-spec-path>"),
            },
            {
                "kind": "validate_source_spec",
                "label": "Validate the source Markdown spec before retrying",
                "command_template": copyable_loopora_command("loopora spec validate <source-spec-path>"),
            },
            {
                "kind": "create_starter_spec",
                "label": "Create a starter spec at another path",
                "command_template": copyable_loopora_command("loopora spec init <spec-path>"),
            },
            {
                "kind": "start_route_chooser",
                "label": "Choose the safe route for a new task",
                "command": copyable_loopora_command("loopora start"),
            },
        ]
    return [
        {
            "kind": "choose_spec_output_file",
            "label": "Choose a writable target Markdown spec",
            "command_template": copyable_loopora_command("loopora spec init <spec-path>"),
        },
        {
            "kind": "print_spec_template",
            "label": "Print the starter spec template instead",
            "command": copyable_loopora_command("loopora spec template"),
        },
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
    ]


def _print_spec_output_recovery(payload: dict[str, object]) -> None:
    typer.echo("Loopora Markdown spec output target is blocked")
    typer.echo(f"resource: {payload['resource']}")
    typer.echo(f"action: {payload['action']}")
    typer.echo(f"output_state: {payload['output_state']}")
    typer.echo(f"validation_error: {payload['validation_error']}")
    typer.echo(f"summary: {payload['summary']}")
    typer.echo("next actions:")
    for action in [item for item in payload["next_actions"] if isinstance(item, dict)]:
        detail = action.get("command") or action.get("command_template") or ""
        suffix = f": {detail}" if detail else ""
        typer.echo(f"- {action['label']}{suffix}")
