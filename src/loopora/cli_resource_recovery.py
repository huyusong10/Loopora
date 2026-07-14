from __future__ import annotations

from dataclasses import dataclass

import typer

from loopora.action_readiness_projection import project_next_action_readiness_contract
from loopora.agent_adapter_command_prefix import copyable_loopora_command, rewrite_loopora_help_commands
from loopora.cli_common import echo_json


@dataclass(frozen=True)
class MissingResourceIdentifierRecovery:
    resource_label: str
    action: str
    required_identifier: str
    required_identifier_label: str
    list_command: str
    list_label: str
    retry_template: str
    web_label: str
    json_output: bool


@dataclass(frozen=True)
class MissingResourceNameRecovery:
    resource_label: str
    required_identifier_label: str
    list_command: str
    list_label: str
    retry_template: str
    web_label: str
    json_output: bool


def normalize_cli_identifier(identifier: str | None) -> str:
    return str(identifier or "").strip()


def echo_resource_recovery_json(payload: dict[str, object]) -> None:
    echo_json(project_resource_recovery_action_contract(payload))


def project_resource_recovery_action_contract(payload: dict[str, object]) -> dict[str, object]:
    return project_next_action_readiness_contract(payload)


def exit_with_missing_resource_identifier_recovery(recovery: MissingResourceIdentifierRecovery) -> None:
    payload = project_resource_recovery_action_contract({
        "resource_recovery": "missing_resource_identifier",
        "status": "blocked_by_missing_identifier",
        "resource": recovery.resource_label,
        "action": recovery.action,
        "required_identifier": recovery.required_identifier,
        "required_identifier_label": recovery.required_identifier_label,
        "summary": f"Choose a {recovery.resource_label} before continuing this resource command.",
        "next_actions": [
            {
                "kind": "list_resources",
                "label": recovery.list_label,
                "command": copyable_loopora_command(recovery.list_command),
            },
            {
                "kind": "open_web_catalog",
                "label": recovery.web_label,
                "command": copyable_loopora_command('loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742'),
            },
            {
                "kind": "retry_after_choice",
                "label": "Retry after choosing an identifier",
                "command_template": rewrite_loopora_help_commands(recovery.retry_template),
            },
        ],
    })
    if recovery.json_output:
        echo_json(payload)
    else:
        _print_missing_resource_identifier_recovery(payload)
    raise typer.Exit(code=1)


def exit_with_missing_resource_name_recovery(recovery: MissingResourceNameRecovery) -> None:
    payload = project_resource_recovery_action_contract({
        "resource_recovery": "missing_resource_name",
        "status": "blocked_by_missing_name",
        "resource": recovery.resource_label,
        "action": "create",
        "required_identifier": "name",
        "required_identifier_label": recovery.required_identifier_label,
        "summary": f"Choose a name for the new {recovery.resource_label} before creating this reusable asset.",
        "next_actions": [
            {
                "kind": "retry_after_name_choice",
                "label": "Retry after choosing a name",
                "command_template": copyable_loopora_command(recovery.retry_template),
            },
            {
                "kind": "list_resources",
                "label": recovery.list_label,
                "command": copyable_loopora_command(recovery.list_command),
            },
            {
                "kind": "open_web_catalog",
                "label": recovery.web_label,
                "command": copyable_loopora_command('loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742'),
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
    })
    if recovery.json_output:
        echo_json(payload)
    else:
        _print_missing_resource_identifier_recovery(payload)
    raise typer.Exit(code=1)


def _print_missing_resource_identifier_recovery(payload: dict) -> None:
    typer.echo("Loopora resource command needs an id")
    typer.echo(f"resource: {payload['resource']}")
    typer.echo(f"action: {payload['action']}")
    typer.echo(f"required identifier: {payload['required_identifier_label']}")
    typer.echo(f"summary: {payload['summary']}")
    typer.echo("next actions:")
    for action in payload["next_actions"]:
        detail = action.get("command") or action.get("command_template") or ""
        suffix = f": {detail}" if detail else ""
        typer.echo(f"- {action['label']}{suffix}")
