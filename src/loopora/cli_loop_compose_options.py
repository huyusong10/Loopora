from __future__ import annotations

from typing import NoReturn

import typer

from loopora.cli_common import handle_error
from loopora.loop_compose_validation import (
    LoopComposeRuntimeOptions,
    normalize_loop_compose_runtime_options,
    validate_loop_compose_semantic_options,
)


def normalize_loop_compose_runtime_options_or_exit(  # noqa: PLR0913 - mirrors the public compose numeric option boundary.
    *,
    iteration_interval_seconds: object,
    max_iters: object,
    max_role_retries: object,
    delta_threshold: object,
    trigger_window: object,
    regression_window: object,
    json_output: bool,
) -> LoopComposeRuntimeOptions:
    try:
        return normalize_loop_compose_runtime_options(
            iteration_interval_seconds=iteration_interval_seconds,
            max_iters=max_iters,
            max_role_retries=max_role_retries,
            delta_threshold=delta_threshold,
            trigger_window=trigger_window,
            regression_window=regression_window,
        )
    except ValueError as exc:
        _exit_invalid_loop_compose_option(exc, json_output=json_output)


def validate_loop_compose_semantic_options_or_exit(  # noqa: PLR0913 - mirrors the public compose semantic option boundary.
    *,
    executor_kind: object,
    executor_mode: object,
    reasoning_effort: object,
    completion_mode: object,
    command_arg: list[str] | None,
    role_model: list[str] | None,
    strategy_preset: object,
    orchestration_id: object,
    strategy_file: object,
    json_output: bool,
) -> None:
    try:
        validate_loop_compose_semantic_options(
            executor_kind=executor_kind,
            executor_mode=executor_mode,
            reasoning_effort=reasoning_effort,
            completion_mode=completion_mode,
            command_arg=command_arg,
            role_model=role_model,
            strategy_preset=strategy_preset,
            orchestration_id=orchestration_id,
            strategy_file=strategy_file,
        )
    except ValueError as exc:
        _exit_invalid_loop_compose_option(exc, json_output=json_output)


def _exit_invalid_loop_compose_option(exc: ValueError, *, json_output: bool) -> NoReturn:
    if json_output:
        handle_error(exc, json_output=True)
    typer.echo(str(exc), err=True)
    raise typer.Exit(code=2) from exc
