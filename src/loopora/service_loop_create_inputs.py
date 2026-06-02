from __future__ import annotations

import math
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from loopora.executor_command_args import normalize_reasoning_effort, validate_command_args_text
from loopora.numeric_inputs import coerce_integral_number
from loopora.providers import executor_profile, normalize_executor_kind, normalize_executor_mode
from loopora.service_types import LooporaError, normalize_completion_mode


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
    workdir, spec_path = _normalize_loop_paths(request.workdir, request.spec_path)
    runtime_limits = _normalize_loop_limits(request)
    return replace(
        request,
        workdir=workdir,
        spec_path=spec_path,
        **runtime_limits,
        **_normalize_loop_executor_settings(request),
    )


def _normalize_loop_paths(workdir: Path, spec_path: Path) -> tuple[Path, Path]:
    normalized_workdir = workdir.expanduser().resolve()
    normalized_spec_path = spec_path.expanduser()
    if normalized_spec_path.exists():
        normalized_spec_path = normalized_spec_path.resolve()
    if not normalized_workdir.exists() or not normalized_workdir.is_dir():
        raise LooporaError(f"workdir does not exist: {normalized_workdir}")
    if not normalized_spec_path.exists():
        raise LooporaError(f"spec does not exist: {normalized_spec_path}")
    return normalized_workdir, normalized_spec_path


def _normalize_loop_limits(request: LoopCreateRequest) -> dict[str, int | float]:
    for field_name in (
        "iteration_interval_seconds",
        "max_iters",
        "max_role_retries",
        "delta_threshold",
        "trigger_window",
        "regression_window",
    ):
        _validate_finite_loop_number(getattr(request, field_name), field_name=field_name)
    try:
        max_iters = coerce_integral_number(request.max_iters, field_name="max_iters")
        max_role_retries = coerce_integral_number(request.max_role_retries, field_name="max_role_retries")
        trigger_window = coerce_integral_number(request.trigger_window, field_name="trigger_window")
        regression_window = coerce_integral_number(request.regression_window, field_name="regression_window")
    except ValueError as exc:
        raise LooporaError(str(exc)) from exc
    iteration_interval_seconds = float(request.iteration_interval_seconds)
    delta_threshold = float(request.delta_threshold)
    if max_iters < 0:
        raise LooporaError("max_iters must be >= 0")
    if max_role_retries < 0:
        raise LooporaError("max_role_retries must be >= 0")
    if iteration_interval_seconds < 0:
        raise LooporaError("iteration_interval_seconds must be >= 0")
    if delta_threshold < 0:
        raise LooporaError("delta_threshold must be >= 0")
    if trigger_window < 1:
        raise LooporaError("trigger_window must be >= 1")
    if regression_window < 1:
        raise LooporaError("regression_window must be >= 1")
    return {
        "iteration_interval_seconds": iteration_interval_seconds,
        "max_iters": max_iters,
        "max_role_retries": max_role_retries,
        "delta_threshold": delta_threshold,
        "trigger_window": trigger_window,
        "regression_window": regression_window,
    }


def _validate_finite_loop_number(value: object, *, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise LooporaError(f"{field_name} must be a finite number")


def _normalize_loop_executor_settings(request: LoopCreateRequest) -> dict[str, str]:
    try:
        executor_kind = normalize_executor_kind(request.executor_kind)
        executor_mode = normalize_executor_mode(request.executor_mode)
        profile = executor_profile(executor_kind)
        if profile.command_only and executor_mode != "command":
            raise ValueError(f"{profile.label} only supports command mode")
        model = request.model.strip()
        if executor_mode == "preset":
            return {
                "executor_kind": executor_kind,
                "executor_mode": executor_mode,
                "command_cli": "",
                "command_args_text": "",
                "model": model or profile.default_model,
                "reasoning_effort": normalize_reasoning_effort(request.reasoning_effort, executor_kind),
                "completion_mode": normalize_completion_mode(request.completion_mode),
            }
        command_cli = request.command_cli.strip() or profile.cli_name
        validate_command_args_text(request.command_args_text, executor_kind=executor_kind)
        return {
            "executor_kind": executor_kind,
            "executor_mode": executor_mode,
            "command_cli": command_cli,
            "command_args_text": request.command_args_text,
            "model": model,
            "reasoning_effort": request.reasoning_effort.strip(),
            "completion_mode": normalize_completion_mode(request.completion_mode),
        }
    except ValueError as exc:
        raise LooporaError(str(exc)) from exc
