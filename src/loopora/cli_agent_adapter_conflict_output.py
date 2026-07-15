from __future__ import annotations

import shlex
from pathlib import Path

import typer

from loopora.agent_adapter_manifest import adapter_label as _adapter_label
from loopora.agent_adapters import prefix_loopora_command, resolve_adapter_project_root
from loopora.cli_shared import echo_json
from loopora.service_types import LooporaConflictError


def is_adapter_install_conflict(exc: LooporaConflictError) -> bool:
    message = str(exc)
    return (
        ("non-Loopora" in message and "adapter files:" in message)
        or message.startswith(
            (
                "refusing to update Claude Code settings because ",
                "Claude Code settings must be a JSON object:",
            )
        )
    )


def handle_adapter_install_conflict(adapter: str, *, workdir: Path, exc: LooporaConflictError, json_output: bool) -> None:
    label = _adapter_label(adapter) or "Agent"
    root = resolve_adapter_project_root(workdir)
    conflicts = adapter_conflict_paths(str(exc))
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


def adapter_conflict_paths(message: str) -> list[str]:
    marker = "adapter files:"
    if marker not in message:
        return []
    return [part.strip() for part in message.split(marker, 1)[1].split(",") if part.strip()]
