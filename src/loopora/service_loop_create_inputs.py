from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from loopora.loop_compose_validation import (
    normalize_loop_compose_execution_options,
    normalize_loop_compose_runtime_options,
    validate_loop_compose_semantic_options,
)
from loopora.service_types import LooporaError
from loopora.workdir_inputs import normalize_existing_spec_path, normalize_recoverable_workdir


@dataclass(frozen=True, kw_only=True)
class LoopCreateRequest:
    name: str
    spec_path: Path
    workdir: Path
    model: str
    reasoning_effort: str
    max_iters: int
    max_role_retries: int
    delta_threshold: float
    trigger_window: int
    regression_window: int
    executor_kind: str = "codex"
    executor_mode: str = "preset"
    command_cli: str = ""
    command_args_text: str = ""
    workflow: dict | None = None
    prompt_files: dict | None = None
    orchestration_id: str | None = None
    role_models: dict | None = None
    completion_mode: str = "gatekeeper"
    iteration_interval_seconds: float = 0.0


def coerce_loop_create_request(
    request: LoopCreateRequest | None,
    raw_request: dict[str, Any],
) -> LoopCreateRequest:
    if request is not None and raw_request:
        raise TypeError("loop create request cannot mix object and keyword fields")
    return request or LoopCreateRequest(**raw_request)


def normalize_loop_create_request(request: LoopCreateRequest) -> LoopCreateRequest:
    runtime_limits = _normalize_loop_limits(request)
    _validate_loop_semantic_options(request)
    workdir, spec_path = _normalize_loop_paths(request.workdir, request.spec_path)
    return replace(
        request,
        workdir=workdir,
        spec_path=spec_path,
        **runtime_limits,
        **_normalize_loop_executor_settings(request),
    )


def _normalize_loop_paths(workdir: Path, spec_path: Path) -> tuple[Path, Path]:
    return normalize_recoverable_workdir(workdir, action="compose"), normalize_existing_spec_path(spec_path)


def _normalize_loop_limits(request: LoopCreateRequest) -> dict[str, int | float]:
    try:
        runtime_options = normalize_loop_compose_runtime_options(
            iteration_interval_seconds=request.iteration_interval_seconds,
            max_iters=request.max_iters,
            max_role_retries=request.max_role_retries,
            delta_threshold=request.delta_threshold,
            trigger_window=request.trigger_window,
            regression_window=request.regression_window,
        )
    except ValueError as exc:
        raise LooporaError(_service_loop_compose_error_message(str(exc))) from exc
    return {
        "iteration_interval_seconds": runtime_options.iteration_interval_seconds,
        "max_iters": runtime_options.max_iters,
        "max_role_retries": runtime_options.max_role_retries,
        "delta_threshold": runtime_options.delta_threshold,
        "trigger_window": runtime_options.trigger_window,
        "regression_window": runtime_options.regression_window,
    }


def _validate_loop_semantic_options(request: LoopCreateRequest) -> None:
    try:
        validate_loop_compose_semantic_options(
            executor_kind=request.executor_kind,
            executor_mode=request.executor_mode,
            reasoning_effort=request.reasoning_effort,
            completion_mode=request.completion_mode,
            command_args_text=request.command_args_text,
            role_models=request.role_models,
            strategy_preset="",
            orchestration_id=request.orchestration_id,
            strategy_file=request.workflow,
        )
    except ValueError as exc:
        raise LooporaError(_service_loop_compose_error_message(str(exc))) from exc


def _normalize_loop_executor_settings(request: LoopCreateRequest) -> dict[str, str]:
    try:
        execution_options = normalize_loop_compose_execution_options(
            executor_kind=request.executor_kind,
            executor_mode=request.executor_mode,
            reasoning_effort=request.reasoning_effort,
            completion_mode=request.completion_mode,
            command_cli=request.command_cli,
            command_args_text=request.command_args_text,
            model=request.model,
        )
        return {
            "executor_kind": execution_options.executor_kind,
            "executor_mode": execution_options.executor_mode,
            "command_cli": execution_options.command_cli,
            "command_args_text": execution_options.command_args_text,
            "model": execution_options.model,
            "reasoning_effort": execution_options.reasoning_effort,
            "completion_mode": execution_options.completion_mode,
        }
    except ValueError as exc:
        raise LooporaError(_service_loop_compose_error_message(str(exc))) from exc


def _service_loop_compose_error_message(message: str) -> str:
    runtime_replacements = {
        "invalid --iteration-interval-seconds:": "iteration_interval_seconds",
        "invalid --max-iters:": "max_iters",
        "invalid --max-role-retries:": "max_role_retries",
        "invalid --delta-threshold:": "delta_threshold",
        "invalid --trigger-window:": "trigger_window",
        "invalid --regression-window:": "regression_window",
    }
    for cli_prefix, field_name in runtime_replacements.items():
        if message.startswith(cli_prefix):
            return f"{field_name}{message[len(cli_prefix):]}"
    semantic_replacements = {
        "invalid --executor:": "invalid executor_kind:",
        "invalid --executor-mode:": "invalid executor_mode:",
        "invalid --reasoning-effort:": "invalid reasoning_effort:",
        "invalid --completion-mode:": "invalid completion_mode:",
        "invalid --command-arg:": "invalid command_args_text:",
        "invalid --role-model:": "invalid role_models:",
        "invalid --strategy-preset:": "invalid strategy_preset:",
    }
    for cli_prefix, field_prefix in semantic_replacements.items():
        if message.startswith(cli_prefix):
            return f"{field_prefix}{message[len(cli_prefix):]}"
    return message
