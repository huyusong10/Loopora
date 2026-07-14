from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from pathlib import Path
import shlex

import typer

from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.db_schema import FUTURE_SCHEMA_ERROR_PREFIX
from loopora.diagnostics import get_logger, log_event
from loopora.cli_runtime import get_service as _runtime_get_service
from loopora.cli_runtime import spawn_background_worker as _runtime_spawn_background_worker
from loopora.cli_recovery_archive_guidance import copyable_recovery_archive_command, recovery_archive_action
from loopora.first_use_action_readiness import (
    first_use_action_readiness_summary,
    project_first_use_action_readiness_summary,
)

logger = get_logger(__name__)

DEVELOPMENT_RESET_PREVIEW_COMMAND = "loopora dev reset --scope app --workdir <project>"
DEVELOPMENT_RESET_APPLY_COMMAND = f"{DEVELOPMENT_RESET_PREVIEW_COMMAND} --yes"
FUTURE_SCHEMA_RECOVERY = "use_matching_loopora_version_or_reset"
DEVELOPMENT_RESET_SCOPE_DESCRIPTION = (
    "app scope resets only local App database files; project .loopora state and managed Agent entries are left alone."
)


def handle_error(
    exc: Exception,
    *,
    json_output: bool = False,
    recovery_workdir: Path | str | None = None,
    extra_recovery_lines: Sequence[str] | None = None,
) -> None:
    log_event(
        logger,
        logging.ERROR,
        "cli.command.failed",
        "CLI command failed",
        error_type=type(exc).__name__,
        error_message=str(exc),
    )
    if json_output and _is_development_reset_error(exc):
        echo_json(
            _development_reset_payload(
                exc,
                recovery_workdir=recovery_workdir,
                extra_recovery_lines=extra_recovery_lines,
            )
        )
        raise typer.Exit(code=1)
    if json_output and _is_future_schema_error(exc):
        echo_json(_future_schema_payload(exc, recovery_workdir=recovery_workdir))
        raise typer.Exit(code=1)
    if json_output:
        echo_json(_json_error_payload(exc))
        raise typer.Exit(code=1)
    typer.secho(
        _error_message(exc, recovery_workdir=recovery_workdir, extra_recovery_lines=extra_recovery_lines),
        fg=typer.colors.RED,
        err=True,
    )
    raise typer.Exit(code=1)


def _is_development_reset_error(exc: Exception) -> bool:
    return str(exc).startswith("Loopora v3 development reset required:")


def _is_future_schema_error(exc: Exception) -> bool:
    return str(exc).startswith(FUTURE_SCHEMA_ERROR_PREFIX)


def _development_reset_preview_command(recovery_workdir: Path | str | None = None) -> str:
    if recovery_workdir is None:
        return copyable_loopora_command(DEVELOPMENT_RESET_PREVIEW_COMMAND)
    command = f"loopora dev reset --scope app --workdir {shlex.quote(str(Path(recovery_workdir).expanduser().resolve()))}"
    return copyable_loopora_command(command)


def _development_reset_apply_command(recovery_workdir: Path | str | None = None) -> str:
    return f"{_development_reset_preview_command(recovery_workdir)} --yes"


def _error_message(
    exc: Exception,
    *,
    recovery_workdir: Path | str | None = None,
    extra_recovery_lines: Sequence[str] | None = None,
) -> str:
    message = str(exc)
    if _is_future_schema_error(exc):
        return _future_schema_plain_message(exc, recovery_workdir=recovery_workdir)
    if not _is_development_reset_error(exc):
        return message
    preview_command = _development_reset_preview_command(recovery_workdir)
    apply_command = _development_reset_apply_command(recovery_workdir)
    recovery_command = copyable_recovery_archive_command(recovery_workdir)
    return "\n".join(
        [
            message.replace(DEVELOPMENT_RESET_PREVIEW_COMMAND, preview_command),
            f"recovery archive before reset: {recovery_command}",
            f"reset preview: {preview_command}",
            f"reset apply after review: {apply_command}",
            f"reset scope: {DEVELOPMENT_RESET_SCOPE_DESCRIPTION}",
            *(line for line in (extra_recovery_lines or []) if str(line).strip()),
        ]
    )


def _future_schema_plain_message(exc: Exception, *, recovery_workdir: Path | str | None = None) -> str:
    preview_command = _development_reset_preview_command(recovery_workdir)
    apply_command = _development_reset_apply_command(recovery_workdir)
    doctor_command = _doctor_command(recovery_workdir)
    recovery_command = copyable_recovery_archive_command(recovery_workdir)
    return "\n".join(
        [
            str(exc),
            f"loop_recovery: {FUTURE_SCHEMA_RECOVERY}",
            f"inspect App state: {doctor_command}",
            f"recovery archive before reset: {recovery_command}",
            f"reset preview: {preview_command}",
            f"reset apply after review: {apply_command}",
            f"reset scope: {DEVELOPMENT_RESET_SCOPE_DESCRIPTION}",
        ]
    )


def _development_reset_payload(
    exc: Exception,
    *,
    recovery_workdir: Path | str | None = None,
    extra_recovery_lines: Sequence[str] | None = None,
) -> dict[str, object]:
    preview_command = _development_reset_preview_command(recovery_workdir)
    recovery_command = copyable_recovery_archive_command(recovery_workdir)
    next_actions = [
        recovery_archive_action(recovery_command),
        {
            "kind": "preview_app_database_reset",
            "command": preview_command,
            "preview_is_destructive": False,
            "destructive_apply_requires_yes": True,
            "after_action": "create_recovery_archive",
        },
    ]
    payload: dict[str, object] = {
        "ready": False,
        "loop_recovery": "development_reset_required",
        "message": _error_message(
            exc,
            recovery_workdir=recovery_workdir,
            extra_recovery_lines=extra_recovery_lines,
        ),
        "reset_command": preview_command,
        "preview_reset_command": preview_command,
        "apply_reset_command": _development_reset_apply_command(recovery_workdir),
        "recovery_archive_command": recovery_command,
        "recovery_archive_recommended": True,
        "reset_scope": "app",
        "scope_description": DEVELOPMENT_RESET_SCOPE_DESCRIPTION,
        "preview_is_destructive": False,
        "destructive_apply_requires_yes": True,
        "next_step": "Create and inspect a private recovery archive, review the reset preview, then use --yes only if the planned deletions are acceptable.",
        "next_actions": next_actions,
        "delete_home": "Fallback for disposable local development state only; prefer the reset preview before deleting anything.",
    }
    if extra_recovery_lines:
        payload["extra_recovery_lines"] = [str(line) for line in extra_recovery_lines if str(line).strip()]
    _project_app_state_action_contract(payload)
    return payload


def _future_schema_payload(
    exc: Exception,
    *,
    recovery_workdir: Path | str | None = None,
) -> dict[str, object]:
    next_actions = _future_schema_next_actions(recovery_workdir)
    payload = {
        "app_state_recovery_summary": {
            "ready": False,
            "loop_recovery": FUTURE_SCHEMA_RECOVERY,
            "status": "blocked_by_app_state",
            "surface": "cli_command",
            "app_state_status": "future_version",
            "next_action_kinds": _action_kinds(next_actions),
        },
        "ready": False,
        "loop_recovery": FUTURE_SCHEMA_RECOVERY,
        "status": "blocked_by_app_state",
        "surface": "cli_command",
        "app_state_status": "future_version",
        "next_action": FUTURE_SCHEMA_RECOVERY,
        "summary": str(exc),
        "error": str(exc),
        "message": _future_schema_plain_message(exc, recovery_workdir=recovery_workdir),
        "next_actions": next_actions,
        "reset_scope": "app",
        "scope_description": DEVELOPMENT_RESET_SCOPE_DESCRIPTION,
        "preview_is_destructive": False,
        "destructive_apply_requires_yes": True,
    }
    _project_app_state_action_contract(payload)
    return payload


def _project_app_state_action_contract(payload: dict[str, object]) -> None:
    actions = [action for action in list(payload.get("next_actions") or []) if isinstance(action, dict)]
    action_kinds = _action_kinds(actions)
    payload["next_action_kinds"] = action_kinds
    readiness = first_use_action_readiness_summary(actions)
    project_first_use_action_readiness_summary(payload, prefix="next_action", readiness=readiness)
    summary = payload.get("app_state_recovery_summary")
    if isinstance(summary, dict):
        summary["next_action_kinds"] = list(action_kinds)
        project_first_use_action_readiness_summary(summary, prefix="next_action", readiness=readiness)


def _future_schema_next_actions(recovery_workdir: Path | str | None = None) -> list[dict[str, object]]:
    recovery_command = copyable_recovery_archive_command(recovery_workdir)
    return [
        {
            "kind": FUTURE_SCHEMA_RECOVERY,
            "note": (
                "Use the matching or newer Loopora version that created this App database; reset only after "
                "reviewing the app-scope preview."
            ),
        },
        {"kind": "inspect_app_state", "command": _doctor_command(recovery_workdir)},
        recovery_archive_action(recovery_command, after_action="inspect_app_state"),
        {
            "kind": "preview_app_database_reset",
            "command": _development_reset_preview_command(recovery_workdir),
            "preview_is_destructive": False,
            "destructive_apply_requires_yes": True,
            "after_action": "create_recovery_archive",
        },
    ]


def _doctor_command(recovery_workdir: Path | str | None = None) -> str:
    if recovery_workdir is None:
        return copyable_loopora_command("loopora doctor --workdir <project>")
    command = f"loopora doctor --workdir {shlex.quote(str(Path(recovery_workdir).expanduser().resolve()))}"
    return copyable_loopora_command(command)


def _action_kinds(actions: Sequence[Mapping[str, object]]) -> list[str]:
    return [str(action.get("kind") or "").strip() for action in actions if str(action.get("kind") or "").strip()]


def _json_error_payload(exc: Exception) -> dict[str, str]:
    return {"status": "error", "error": str(exc)}


def echo_json(payload: object) -> None:
    import json

    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


def get_service(*, apply_startup_repairs: bool = True, storage_read_only: bool = False):
    return _runtime_get_service(
        apply_startup_repairs=apply_startup_repairs,
        storage_read_only=storage_read_only,
    )


def call_spawn_background_worker(service, run: dict) -> dict:
    return _runtime_spawn_background_worker(service, run)
