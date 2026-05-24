from __future__ import annotations

import logging

import typer

from loopora.diagnostics import get_logger, log_event
from loopora.cli_runtime import get_service as _runtime_get_service
from loopora.cli_runtime import spawn_background_worker as _runtime_spawn_background_worker

logger = get_logger(__name__)


def handle_error(exc: Exception) -> None:
    log_event(
        logger,
        logging.ERROR,
        "cli.command.failed",
        "CLI command failed",
        error_type=type(exc).__name__,
        error_message=str(exc),
    )
    typer.secho(str(exc), fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1)


def echo_json(payload: object) -> None:
    import json

    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


def get_service():
    return _runtime_get_service()


def call_spawn_background_worker(service, run: dict) -> dict:
    return _runtime_spawn_background_worker(service, run)
