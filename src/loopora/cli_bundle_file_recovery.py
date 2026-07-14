from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer

from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.bundle_contract import BundleError
from loopora.bundle_io import load_bundle_file, resolve_bundle_file_path
from loopora.cli_resource_recovery import echo_resource_recovery_json, project_resource_recovery_action_contract
from loopora.service import LooporaError
from loopora.service_bundle_export import PLAN_FILE_EXPORT_ERROR, PLAN_FILE_OUTPUT_DIRECTORY_ERROR

BundleImportFileArgument = Annotated[
    Path | None,
    typer.Argument(
        exists=False,
        file_okay=True,
        dir_okay=True,
        help="Path to a Loop plan file (YAML); omit to get recovery guidance.",
    ),
]


@dataclass(frozen=True)
class PlanFileOutputRecovery:
    action: str
    retry_template: str
    stream_template: str
    list_command: str
    list_label: str


def validated_bundle_import_file(bundle_file: Path) -> Path:
    try:
        resolved = resolve_bundle_file_path(bundle_file)
        load_bundle_file(resolved)
        return resolved
    except (BundleError, OSError) as exc:
        exit_with_invalid_plan_file_import_recovery(str(exc))


def exit_with_missing_plan_file_import_recovery() -> None:
    echo_resource_recovery_json(
        {
            "resource_recovery": "missing_plan_file_input",
            "status": "blocked_by_missing_plan_file",
            "resource": "Plan File",
            "action": "import",
            "required_identifier": "bundle_file",
            "required_identifier_label": "Path to a reviewed Loop plan file",
            "summary": ("Import needs an existing reviewed Loop plan file; it does not create or review a new task."),
            "next_actions": [
                {
                    "kind": "retry_after_file_choice",
                    "label": "Import a reviewed Plan File",
                    "command_template": copyable_loopora_command("loopora bundles import <plan-file>"),
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


def exit_with_invalid_plan_file_import_recovery(validation_error: str) -> None:
    echo_resource_recovery_json(
        {
            "resource_recovery": "invalid_plan_file_input",
            "status": "blocked_by_invalid_plan_file",
            "resource": "Plan File",
            "action": "import",
            "required_identifier": "bundle_file",
            "required_identifier_label": "Path to a reviewed Loop plan file",
            "validation_error": validation_error,
            "summary": ("Import needs a readable reviewed Loop plan file before Loopora opens local App state or mutates assets."),
            "next_actions": [
                {
                    "kind": "choose_readable_plan_file",
                    "label": "Choose a readable reviewed Plan File",
                    "command_template": copyable_loopora_command("loopora bundles import <plan-file>"),
                },
                {
                    "kind": "repair_plan_file",
                    "label": "Repair the Plan File YAML, then retry import",
                },
                {
                    "kind": "start_route_chooser",
                    "label": "Choose the safe route for a new task",
                    "command": copyable_loopora_command("loopora start"),
                },
            ],
        }
    )
    raise typer.Exit(code=1)


def validated_plan_file_output_path(
    output: Path,
    recovery: PlanFileOutputRecovery,
) -> Path:
    try:
        target = output.expanduser()
        is_directory = target.is_dir()
    except (OSError, RuntimeError, ValueError):
        exit_with_plan_file_output_recovery(
            recovery,
            output_state="unavailable",
            validation_error="plan file output could not be inspected",
        )
    if is_directory:
        exit_with_plan_file_output_recovery(
            recovery,
            output_state="directory",
            validation_error=PLAN_FILE_OUTPUT_DIRECTORY_ERROR,
        )
    return target


def exit_with_plan_file_output_recovery(
    recovery: PlanFileOutputRecovery,
    *,
    output_state: str,
    validation_error: str,
) -> None:
    payload = {
        "resource_recovery": "invalid_plan_file_output_target",
        "status": "blocked_by_plan_file_output",
        "resource": "Plan File output",
        "action": recovery.action,
        "output_state": output_state,
        "validation_error": validation_error,
        "summary": "Choose a writable Plan File output path, or omit --output to print the YAML artifact stream.",
        "next_actions": [
            {
                "kind": "choose_output_file",
                "label": "Choose a Plan File output path",
                "command_template": copyable_loopora_command(recovery.retry_template),
            },
            {
                "kind": "print_artifact_stream",
                "label": "Print the Plan File YAML artifact stream",
                "command_template": copyable_loopora_command(recovery.stream_template),
            },
            {
                "kind": "list_resources",
                "label": recovery.list_label,
                "command": copyable_loopora_command(recovery.list_command),
            },
        ],
    }
    payload = project_resource_recovery_action_contract(payload)
    print_plan_file_output_recovery(payload)
    raise typer.Exit(code=1)


def exit_with_plan_file_output_write_recovery_if_known(
    exc: LooporaError,
    recovery: PlanFileOutputRecovery,
) -> None:
    error = str(exc)
    if error == PLAN_FILE_OUTPUT_DIRECTORY_ERROR:
        exit_with_plan_file_output_recovery(
            recovery,
            output_state="directory",
            validation_error=PLAN_FILE_OUTPUT_DIRECTORY_ERROR,
        )
    if error == PLAN_FILE_EXPORT_ERROR:
        exit_with_plan_file_output_recovery(
            recovery,
            output_state="write_failed",
            validation_error=PLAN_FILE_EXPORT_ERROR,
        )


def print_plan_file_output_recovery(payload: dict[str, object]) -> None:
    typer.echo("Loopora Plan File output target is blocked")
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
