from __future__ import annotations

import shlex
from pathlib import Path

import typer

from loopora.agent_adapter_check_utils import adapter_label as _adapter_label
from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.agent_adapters import resolve_adapter_project_root
from loopora.cli_agent_adapter_language import agent_entry_text, localized_agent_entry_command
from loopora.cli_shared import echo_json
from loopora.service_types import LooporaConflictError


def is_adapter_install_conflict(exc: LooporaConflictError) -> bool:
    message = str(exc)
    return (
        ("non-Loopora" in message and "adapter files:" in message)
        or message.startswith(
            (
                "refusing to update Claude Code settings because ",
                "Claude Code settings could not be read:",
                "Claude Code settings must be valid JSON:",
                "Claude Code settings must be a JSON object:",
            )
        )
    )


def handle_adapter_install_conflict(
    adapter: str,
    *,
    workdir: Path,
    exc: LooporaConflictError,
    json_output: bool,
    language: str = "en",
) -> None:
    label = _adapter_label(adapter) or "Agent"
    root = resolve_adapter_project_root(workdir)
    conflicts = adapter_conflict_paths(str(exc))
    recovery = {
        "state": "install_conflict",
        "summary": "Loopora found existing Agent entry files or host config that it does not own, so it left the project unchanged.",
        "inspect": "Inspect the listed file or config before changing it.",
        "user_owned_action": "If it is yours, move or rename it, or choose another target project directory.",
        "install_command": copyable_loopora_command(f"loopora init {adapter} --workdir {shlex.quote(str(root))}"),
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
    typer.secho(
        agent_entry_text(language, f"{label} Loopora entry was not installed.", f"{label} Loopora 项目入口未安装。"),
        fg=typer.colors.RED,
        err=True,
    )
    typer.echo(agent_entry_text(language, f"target project: {root}", f"目标项目：{root}"), err=True)
    typer.echo(
        agent_entry_text(
            language,
            recovery["summary"],
            "Loopora 发现了不由它托管的现有 Agent 项目入口文件或宿主配置，因此未改动项目。",
        ),
        err=True,
    )
    if conflicts:
        typer.echo(agent_entry_text(language, "conflicting files:", "冲突文件："), err=True)
        for path in conflicts:
            typer.echo(f"- {path}", err=True)
    else:
        typer.echo(agent_entry_text(language, f"details: {exc}", f"详情：{exc}"), err=True)
    typer.echo(agent_entry_text(language, "recovery:", "恢复："), err=True)
    typer.echo(
        agent_entry_text(
            language,
            f"- {recovery['inspect']}",
            "- 修改前先检查列出的文件或配置。",
        ),
        err=True,
    )
    typer.echo(
        agent_entry_text(
            language,
            f"- {recovery['user_owned_action']}",
            "- 如果它属于你，请移动或重命名它，或者选择其他目标项目目录。",
        ),
        err=True,
    )
    install_command = localized_agent_entry_command(str(recovery["install_command"]), language=language)
    typer.echo(agent_entry_text(language, f"- Then rerun: {install_command}", f"- 然后重跑：{install_command}"), err=True)
    raise typer.Exit(code=1)


def adapter_conflict_paths(message: str) -> list[str]:
    marker = "adapter files:"
    if marker not in message:
        return [".claude/settings.json"] if message.startswith("Claude Code settings ") else []
    return [part.strip() for part in message.split(marker, 1)[1].split(",") if part.strip()]
