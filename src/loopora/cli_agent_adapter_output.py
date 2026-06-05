from __future__ import annotations

import typer

from loopora.agent_adapter_check_utils import adapter_label as _adapter_label
from loopora.agent_native_surface import native_surface_plain_lines
from loopora import cli_agent_adapter_check_output as _adapter_check_output
from loopora import cli_agent_adapter_conflict_output as _adapter_conflict_output
from loopora.cli_shared import echo_json

_adapter_check_json_payload = _adapter_check_output.adapter_check_json_payload
_adapter_check_summary = _adapter_check_output.adapter_check_summary
_print_adapter_check_recovery = _adapter_check_output.print_adapter_check_recovery
_print_adapter_check_recovery_summary = _adapter_check_output.print_adapter_check_recovery_summary
handle_adapter_install_conflict = _adapter_conflict_output.handle_adapter_install_conflict
is_adapter_install_conflict = _adapter_conflict_output.is_adapter_install_conflict
_adapter_conflict_paths = _adapter_conflict_output.adapter_conflict_paths


def print_adapter_mutation_result(result: dict, *, action: str, json_output: bool) -> None:
    if json_output:
        echo_json(result)
        return
    label = str(result.get("label") or adapter_label(str(result.get("adapter") or "")))
    if action == "installed":
        typer.echo(f"{label} Loopora entry is installed")
        typer.echo(f"target project: {result['workdir']}")
        _print_adapter_next_steps(label, result.get("next_steps"))
        _print_adapter_first_task_message_example(result)
        _print_adapter_next_commands(result.get("next_commands"))
        _print_adapter_native_surface(result)
    else:
        typer.echo(f"{label} Loopora entry {action}: {result['status']}")
        typer.echo(f"target project: {result['workdir']}")
    _print_adapter_file_details(result)


def print_adapter_check_result(result: dict, *, json_output: bool) -> None:
    if json_output:
        echo_json(_adapter_check_json_payload(result))
        return
    label = str(result.get("label") or adapter_label(str(result.get("adapter") or "")))
    check_status = str(result.get("check_status") or "fail")
    typer.echo(f"{label} Loopora entry check: {check_status}")
    typer.echo(f"target project: {result['workdir']}")
    recovery = result.get("check_recovery") if isinstance(result.get("check_recovery"), dict) else {}
    _print_adapter_check_recovery_summary(recovery)
    if recovery.get("state") == "not_installed":
        _print_adapter_check_recovery(result, recovery)
        return
    checks = [item for item in list(result.get("checks") or []) if isinstance(item, dict)]
    if checks:
        typer.echo("checks:")
        for item in checks:
            suffix = f" ({item.get('path')})" if item.get("path") else ""
            message = f": {item.get('message')}" if item.get("message") else ""
            typer.echo(f"- {item.get('status')}: {item.get('name')}{suffix}{message}")
    if check_status == "pass":
        _print_adapter_next_steps(label, result.get("next_steps"))
        _print_adapter_first_task_message_example(result)
        _print_adapter_next_commands(result.get("next_commands"))
        _print_adapter_native_surface(result)
    if check_status != "pass":
        _print_adapter_check_recovery(result, recovery)


def adapter_label(adapter: str) -> str:
    return _adapter_label(adapter) or "Agent"


def _print_adapter_file_details(result: dict) -> None:
    managed_files = result.get("managed_files")
    if isinstance(managed_files, list):
        typer.echo("managed files:")
        for item in managed_files:
            if isinstance(item, dict):
                typer.echo(f"- {item.get('path')}: {item.get('state', 'managed')}")
    removed_files = result.get("removed_files")
    _print_adapter_plain_list("removed:", removed_files)
    removed_obsolete_files = result.get("removed_obsolete_files")
    _print_adapter_plain_list("removed obsolete managed files:", removed_obsolete_files)
    kept_files = result.get("kept_files")
    if isinstance(kept_files, list) and kept_files:
        typer.echo("kept:")
        for item in kept_files:
            if isinstance(item, dict):
                typer.echo(f"- {item.get('path')}: {item.get('reason')}")


def _print_adapter_plain_list(label: str, items: object) -> None:
    if not isinstance(items, list) or not items:
        return
    typer.echo(label)
    for item in items:
        typer.echo(f"- {item}")


def _print_adapter_next_steps(label: str, steps: object = None) -> None:
    typer.echo("next:")
    if isinstance(steps, list) and steps:
        for step in steps:
            text = str(step or "").strip()
            if text:
                typer.echo(f"- {text}")
        return
    typer.echo(f"- Return to {label} in this project with the task goal, fake-done risk, and required evidence.")
    typer.echo("- Run /loopora-plan to prepare the Loop preview before starting work.")
    typer.echo("- Review the READY Loop preview, then run /loopora-run in the same Agent session.")
    typer.echo(
        f"- If /loopora-plan or /loopora-run is not visible in {label}, "
        f"rerun the diagnostics below and refresh or restart {label}."
    )
    typer.echo("- Use Web to observe evidence, gaps, and verdicts while execution stays in the Agent.")


def _print_adapter_next_commands(commands: object) -> None:
    if not isinstance(commands, dict):
        return
    check_command = str(commands.get("check") or "").strip()
    agent_check_command = str(commands.get("agent_check") or "").strip()
    if not check_command and not agent_check_command:
        return
    typer.echo("diagnostics:")
    if check_command:
        typer.echo(f"- verify install: {check_command}")
    if agent_check_command:
        typer.echo(f"- agent-runtime check: {agent_check_command}")


def _print_adapter_native_surface(result: dict) -> None:
    surface = result.get("native_surface") if isinstance(result.get("native_surface"), dict) else {}
    for line in native_surface_plain_lines(surface, include_role_configs=True):
        typer.echo(line)


def _print_adapter_first_task_message_example(result: dict) -> None:
    example = str(result.get("first_task_message_example") or "").strip()
    if not example:
        return
    typer.echo("first task message example:")
    typer.echo(example)
