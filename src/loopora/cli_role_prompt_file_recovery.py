from __future__ import annotations

import typer

from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.cli_resource_recovery import echo_resource_recovery_json


def role_prompt_file_input_error(exc: BaseException) -> str:
    error = str(exc).strip()
    return error if error.startswith("prompt file ") else ""


def exit_with_role_prompt_file_recovery(error: str, *, action: str) -> None:
    echo_resource_recovery_json(
        {
            "resource_recovery": "invalid_prompt_file_input",
            "status": "blocked_by_prompt_file",
            "resource": "Strategy Source prompt file",
            "action": action,
            "validation_error": error,
            "summary": (
                "Role asset changes need a readable custom prompt Markdown file; repair the selected file or "
                "choose another prompt file before changing the reusable role library."
            ),
            "next_actions": [
                {
                    "kind": "repair_prompt_file",
                    "label": "Repair the selected prompt file",
                    "validation_error": error,
                },
                {
                    "kind": "choose_prompt_file",
                    "label": "Choose another prompt file",
                    "command_template": copyable_loopora_command(_role_prompt_file_retry_template(action)),
                },
                {
                    "kind": "validate_prompt_file",
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
                {
                    "kind": "start_route_chooser",
                    "label": "Choose the safe route for a new task",
                    "command": copyable_loopora_command("loopora start"),
                },
            ],
        }
    )
    raise typer.Exit(code=1)


def _role_prompt_file_retry_template(action: str) -> str:
    if action == "update":
        return "loopora roles update <role-definition-id> --prompt-file <prompt-file>"
    if action == "derive":
        return "loopora roles derive <role-definition-id> --name '<role-name>' --prompt-file <prompt-file>"
    return "loopora roles create --name '<role-name>' --prompt-file <prompt-file>"
