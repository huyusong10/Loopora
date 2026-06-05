from __future__ import annotations

import logging

import typer

from loopora.diagnostics import get_logger, log_event
from loopora.cli_runtime import get_service as _runtime_get_service
from loopora.cli_runtime import spawn_background_worker as _runtime_spawn_background_worker

logger = get_logger(__name__)


def handle_error(exc: Exception, *, json_output: bool = False) -> None:
    log_event(
        logger,
        logging.ERROR,
        "cli.command.failed",
        "CLI command failed",
        error_type=type(exc).__name__,
        error_message=str(exc),
    )
    if json_output and _is_development_reset_error(exc):
        echo_json(_development_reset_payload(exc))
        raise typer.Exit(code=1)
    typer.secho(str(exc), fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1)


def _is_development_reset_error(exc: Exception) -> bool:
    return str(exc).startswith("Loopora v3 development reset required:")


def _development_reset_payload(exc: Exception) -> dict[str, str | bool]:
    return {
        "ready": False,
        "loop_recovery": "development_reset_required",
        "message": str(exc),
        "reset_command": "loopora dev reset --workdir <project>",
        "delete_home": "Delete LOOPORA_HOME if this is disposable local development state.",
    }


def echo_json(payload: object) -> None:
    import json

    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


def get_service():
    return _runtime_get_service()


def call_spawn_background_worker(service, run: dict) -> dict:
    return _runtime_spawn_background_worker(service, run)
