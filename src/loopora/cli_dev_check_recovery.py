from __future__ import annotations

from pathlib import Path
import shlex

import typer

from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.dev_check_command_projection import copyable_dev_check_command
from loopora.cli_shared import echo_json, handle_error
from loopora.service_types import LooporaError

DEV_COMMAND_ERROR_SCHEMA_VERSION = 1


def handle_dev_command_error(
    exc: Exception,
    *,
    json_output: bool,
    command: str,
    workdir: Path | None = None,
    changed_files: list[str] | None = None,
) -> None:
    if isinstance(exc, (LooporaError, ValueError)):
        payload = _dev_command_error_payload(str(exc), command=command, workdir=workdir, changed_files=changed_files)
        if json_output:
            echo_json(payload)
            raise typer.Exit(code=1)
        typer.secho(_dev_command_error_text(payload), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    handle_error(exc, json_output=False)


def dev_check_cli_result(result: dict) -> dict:
    next_actions = list(result.get("next_actions") or [])
    if not next_actions:
        return result
    updated = {**result}
    updated["next_actions"] = [_dev_check_cli_next_action(action) if isinstance(action, dict) else action for action in next_actions]
    return updated


def dev_check_recovery_command(
    command: str,
    *,
    workdir: Path | None = None,
    changed_files: list[str] | None = None,
    always_include_workdir: bool = False,
) -> str:
    changed_args = _dev_check_changed_file_args(changed_files, workdir=workdir)
    if changed_args:
        command = f"{command} {changed_args}"
    if workdir is None or (not always_include_workdir and workdir.resolve() == Path.cwd().resolve()):
        return command
    return f"{command} --workdir {shlex.quote(str(workdir.resolve()))}"


def _dev_command_error_payload(
    message: str,
    *,
    command: str,
    workdir: Path | None = None,
    changed_files: list[str] | None = None,
) -> dict:
    next_actions = _dev_command_error_next_actions(message, workdir=workdir, changed_files=changed_files)
    payload = {
        "ready": False,
        "status": "error",
        "error": message,
        "dev_command_error": {
            "schema_version": DEV_COMMAND_ERROR_SCHEMA_VERSION,
            "command": command,
            "state": _dev_command_error_state(message),
        },
    }
    if next_actions:
        payload["next_actions"] = next_actions
    return payload


def _dev_command_error_state(message: str) -> str:
    if message.startswith("workdir "):
        return "blocked_by_workdir"
    if message.startswith("unsupported focused check guide:"):
        return "unsupported_focused_check_guide"
    if message.startswith("unsupported dev check profile:"):
        return "unsupported_profile"
    return "error"


def _dev_command_error_next_actions(
    message: str,
    *,
    workdir: Path | None = None,
    changed_files: list[str] | None = None,
) -> list[dict[str, str]]:
    if message.startswith("unsupported focused check guide:"):
        return [
            {
                "kind": "list_focused_check_guides",
                "command": dev_check_recovery_command(
                    copyable_dev_check_command("--list"),
                    workdir=workdir,
                    changed_files=changed_files,
                ),
            },
            {"kind": "show_dev_check_help", "command": copyable_dev_check_command("--help")},
        ]
    if message.startswith("unsupported dev check profile:"):
        return [
            {
                "kind": "run_default_fast_gate",
                "command": dev_check_recovery_command(copyable_dev_check_command(""), workdir=workdir),
            },
            {
                "kind": "run_recommended_focused_checks",
                "command": dev_check_recovery_command(
                    copyable_dev_check_command("--focused recommended"),
                    workdir=workdir,
                    changed_files=changed_files,
                ),
            },
            {"kind": "show_dev_check_help", "command": copyable_dev_check_command("--help")},
        ]
    return []


def _dev_check_cli_next_action(action: dict) -> dict:
    command = str(action.get("command") or "").strip()
    if not command:
        return action
    updated = {**action}
    updated["command"] = _dev_check_cli_command(command)
    return updated


def _dev_check_cli_command(command: str) -> str:
    text = str(command or "").strip()
    if text == "uv run loopora":
        return copyable_loopora_command("loopora")
    if text.startswith("uv run loopora "):
        return copyable_loopora_command(f"loopora {text[len('uv run loopora ') :]}")
    if text == "loopora" or text.startswith("loopora "):
        return copyable_loopora_command(text)
    return text


def _dev_check_changed_file_args(changed_files: list[str] | None, *, workdir: Path | None) -> str:
    paths = sorted(normalized for path in list(changed_files or []) if (normalized := _dev_check_recovery_changed_file(path, workdir=workdir)))
    return " ".join(f"--changed-file {shlex.quote(path)}" for path in paths)


def _dev_check_recovery_changed_file(path: object, *, workdir: Path | None) -> str:
    raw_path = str(path).strip()
    if not raw_path:
        return ""
    candidate = Path(raw_path).expanduser()
    if workdir is not None and candidate.is_absolute():
        try:
            return candidate.resolve(strict=False).relative_to(workdir.resolve(strict=False)).as_posix()
        except (OSError, ValueError):
            return ""
    normalized = raw_path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized == ".." or normalized.startswith("../"):
        return ""
    return normalized


def _dev_command_error_text(payload: dict) -> str:
    lines = [str(payload.get("error") or "").strip()]
    actions = [action for action in list(payload.get("next_actions") or []) if isinstance(action, dict)]
    rendered_actions = [_dev_command_error_action_text(action) for action in actions if str(action.get("command") or "").strip()]
    if rendered_actions:
        lines.append(f"next: {'; '.join(rendered_actions)}")
    return "\n".join(line for line in lines if line)


def _dev_command_error_action_text(action: dict) -> str:
    kind = str(action.get("kind") or "").strip()
    command = str(action.get("command") or "").strip()
    labels = {
        "list_focused_check_guides": "list focused check guides",
        "show_dev_check_help": "show dev check help",
        "run_default_fast_gate": "run the default-fast gate",
        "run_recommended_focused_checks": "run recommended focused checks",
    }
    label = labels.get(kind, "run")
    return f"{label}: {command}"
