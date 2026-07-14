from __future__ import annotations

import typer

from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.cli_resource_recovery import echo_resource_recovery_json


def exit_with_orchestration_strategy_file_recovery(validation_error: str, *, action: str) -> None:
    echo_resource_recovery_json(
        {
            "resource_recovery": "invalid_strategy_source_file_input",
            "status": "blocked_by_strategy_source_file",
            "resource": "Strategy Source file",
            "action": action,
            "validation_error": validation_error,
            "summary": (
                "Flow asset changes need a readable Strategy Source file; repair the selected file, choose another "
                "file, or use a built-in workflow preset before changing the reusable Flow library."
            ),
            "next_actions": [
                {
                    "kind": "repair_strategy_source_file",
                    "label": "Repair the selected Strategy Source file",
                    "validation_error": validation_error,
                },
                {
                    "kind": "choose_strategy_source_file",
                    "label": "Choose another Strategy Source file",
                    "command_template": copyable_loopora_command(_orchestration_strategy_file_retry_template(action)),
                },
                {
                    "kind": "choose_workflow_preset",
                    "label": "Use a built-in workflow preset",
                    "command_template": copyable_loopora_command(_orchestration_preset_retry_template(action)),
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
            ],
        }
    )
    raise typer.Exit(code=1)


def _orchestration_strategy_file_retry_template(action: str) -> str:
    if action == "update":
        return "loopora orchestrations update <flow-id> --strategy-file <strategy-file>"
    if action == "derive":
        return "loopora orchestrations derive <flow-id> --name '<flow-name>' --strategy-file <strategy-file>"
    return "loopora orchestrations create --name '<flow-name>' --strategy-file <strategy-file>"


def _orchestration_preset_retry_template(action: str) -> str:
    if action == "update":
        return "loopora orchestrations update <flow-id> --workflow-preset <preset>"
    if action == "derive":
        return "loopora orchestrations derive <flow-id> --name '<flow-name>' --workflow-preset <preset>"
    return "loopora orchestrations create --name '<flow-name>' --workflow-preset <preset>"
