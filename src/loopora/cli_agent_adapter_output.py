from __future__ import annotations

import shlex
from pathlib import Path

import typer

from loopora.agent_adapters import prefix_loopora_command, resolve_adapter_project_root
from loopora.agent_native_surface import native_surface_plain_lines
from loopora.agent_native_v3 import agent_v3_envelope
from loopora.agent_native_v3 import agent_v3_legacy_raw
from loopora.cli_shared import echo_json
from loopora.service_types import LooporaConflictError


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


def handle_adapter_install_conflict(adapter: str, *, workdir: Path, exc: LooporaConflictError, json_output: bool) -> None:
    label = adapter_label(adapter)
    root = resolve_adapter_project_root(workdir)
    conflicts = _adapter_conflict_paths(str(exc))
    recovery = {
        "state": "install_conflict",
        "summary": "Loopora found existing Agent entry files or host config that it does not own, so it left the project unchanged.",
        "inspect": "Inspect the listed file or config before changing it.",
        "user_owned_action": "If it is yours, move or rename it, or choose another target project directory.",
        "install_command": prefix_loopora_command(f"loopora init {adapter} --workdir {shlex.quote(str(root))}"),
    }
    if json_output:
        echo_json(
            {
                "adapter": adapter,
                "label": label,
                "workdir": str(root),
                "status": "not_installed",
                "install_status": "conflict",
                "loop_recovery": "adapter_install_conflict",
                "message": f"{label} Loopora entry was not installed.",
                "conflicting_files": conflicts,
                "raw_conflict": str(exc),
                "recovery": recovery,
            }
        )
        raise typer.Exit(code=1)
    typer.secho(f"{label} Loopora entry was not installed.", fg=typer.colors.RED, err=True)
    typer.echo(f"target project: {root}", err=True)
    typer.echo(recovery["summary"], err=True)
    if conflicts:
        typer.echo("conflicting files:", err=True)
        for path in conflicts:
            typer.echo(f"- {path}", err=True)
    else:
        typer.echo(f"details: {exc}", err=True)
    typer.echo("recovery:", err=True)
    typer.echo(f"- {recovery['inspect']}", err=True)
    typer.echo(f"- {recovery['user_owned_action']}", err=True)
    typer.echo(f"- Then rerun: {recovery['install_command']}", err=True)
    raise typer.Exit(code=1)


def _adapter_check_json_payload(result: dict) -> dict:
    summary = _adapter_check_summary(result)
    return agent_v3_envelope(
        kind="agent_check",
        status=str(result.get("check_status") or "fail"),
        summary=summary,
        extras={
            "diagnostics": {"legacy_summary_key": "agent_check_summary"},
            "raw": agent_v3_legacy_raw(summary_key="agent_check_summary", summary=summary, payload=result),
        },
    )


def _adapter_check_summary(result: dict) -> dict:
    recovery = result.get("check_recovery") if isinstance(result.get("check_recovery"), dict) else {}
    summary: dict[str, object] = {
        "schema_version": 3,
        "adapter": str(result.get("adapter") or "").strip(),
        "label": str(result.get("label") or "").strip(),
        "workdir": str(result.get("workdir") or "").strip(),
        "check_status": str(result.get("check_status") or "fail").strip(),
    }
    if recovery:
        summary["check_recovery"] = recovery
    surface = result.get("native_surface") if isinstance(result.get("native_surface"), dict) else {}
    if surface:
        summary["native_surface"] = surface
        capabilities = surface.get("experience_capabilities") if isinstance(surface.get("experience_capabilities"), dict) else {}
        if capabilities:
            summary["experience_capabilities"] = capabilities
    return {key: value for key, value in summary.items() if value not in ("", [], {})}


def adapter_label(adapter: str) -> str:
    return {
        "codex": "Codex",
        "claude": "Claude Code",
        "opencode": "OpenCode",
    }.get(adapter, adapter or "Agent")


def _print_adapter_check_recovery_summary(recovery: dict) -> None:
    state = str(recovery.get("state") or "").strip()
    summary = str(recovery.get("summary") or "").strip()
    if state:
        typer.echo(f"install_state: {state}")
    if summary:
        typer.echo(f"summary: {summary}")


def _print_adapter_check_recovery(result: dict, recovery: dict) -> None:
    install_command = str(recovery.get("install_command") or "").strip()
    if not install_command:
        install_command = prefix_loopora_command(
            f"loopora init {result.get('adapter')} --workdir {shlex.quote(str(result.get('workdir')))}"
        )
    check_command = str(recovery.get("check_command") or "").strip()
    if not check_command:
        check_command = f"{install_command} --check"
    typer.echo("recovery:")
    typer.echo(f"- Run: {install_command}")
    typer.echo(f"- Then verify: {check_command}")
    if recovery.get("state") != "not_installed":
        typer.echo("- If a file is unmanaged, inspect it before replacing or moving it.")


def _adapter_conflict_paths(message: str) -> list[str]:
    marker = "adapter files:"
    if marker not in message:
        return []
    return [part.strip() for part in message.split(marker, 1)[1].split(",") if part.strip()]


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
