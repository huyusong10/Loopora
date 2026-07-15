from __future__ import annotations

import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from loopora.bundle_contract import BUNDLE_DEFAULT_LOOP, BUNDLE_EXECUTION_FIELDS, BundleError
from loopora.executor_command_args import normalize_reasoning_effort, validate_command_args_text
from loopora.numeric_inputs import coerce_integral_number
from loopora.providers import executor_profile, normalize_executor_kind, normalize_executor_mode
from loopora.service_types import LooporaError, normalize_completion_mode


def normalize_bundle_loop(raw_loop: object) -> dict[str, Any]:
    if not isinstance(raw_loop, Mapping):
        raise BundleError("bundle loop must be an object")
    payload = {**BUNDLE_DEFAULT_LOOP, **dict(raw_loop)}
    workdir = str(payload.get("workdir", "") or "").strip()
    if not workdir:
        raise BundleError("bundle loop.workdir is required")
    name = str(payload.get("name", "") or "").strip() or Path(workdir).expanduser().resolve().name
    runtime = _normalize_bundle_loop_runtime(payload)
    execution = _normalize_bundle_loop_execution(payload)
    return {
        "name": name,
        "workdir": workdir,
        "completion_mode": normalize_bundle_completion_mode(payload.get("completion_mode")),
        **execution,
        **runtime,
    }


def normalize_bundle_completion_mode(value: object) -> str:
    try:
        if value is None:
            return normalize_completion_mode(None)
        return normalize_completion_mode(str(value))
    except LooporaError as exc:
        raise BundleError(str(exc)) from exc


def bundle_loop_role_execution_defaults(loop: Mapping[str, Any]) -> dict[str, str]:
    return {field: str(loop.get(field, "") or "") for field in BUNDLE_EXECUTION_FIELDS}


def _normalize_bundle_loop_execution(payload: Mapping[str, Any]) -> dict[str, str]:
    try:
        executor_kind = normalize_executor_kind(str(payload.get("executor_kind", "codex") or "codex").strip())
        executor_mode = normalize_executor_mode(str(payload.get("executor_mode", "preset") or "preset").strip())
        profile = executor_profile(executor_kind)
        if profile.command_only and executor_mode != "command":
            raise ValueError(f"{profile.label} only supports command mode")
        command_cli = str(payload.get("command_cli", "") or "").strip()
        command_args_text = str(payload.get("command_args_text", "") or "")
        model = str(payload.get("model", "") or "").strip()
        reasoning_effort = str(payload.get("reasoning_effort", "") or "").strip()
        if executor_mode == "preset":
            return {
                "executor_kind": executor_kind,
                "executor_mode": executor_mode,
                "command_cli": "",
                "command_args_text": "",
                "model": model if model or profile.default_model == "" else profile.default_model,
                "reasoning_effort": normalize_reasoning_effort(reasoning_effort, executor_kind),
            }
        validate_command_args_text(command_args_text, executor_kind=executor_kind)
        return {
            "executor_kind": executor_kind,
            "executor_mode": executor_mode,
            "command_cli": command_cli or profile.cli_name,
            "command_args_text": command_args_text,
            "model": model,
            "reasoning_effort": reasoning_effort,
        }
    except ValueError as exc:
        raise BundleError(str(exc)) from exc


def _normalize_bundle_loop_runtime(payload: Mapping[str, Any]) -> dict[str, int | float]:
    try:
        iteration_interval_seconds = float(_bundle_numeric_value(payload, "iteration_interval_seconds"))
        max_iters = _bundle_integer_value(payload, "max_iters")
        max_role_retries = _bundle_integer_value(payload, "max_role_retries")
        delta_threshold = float(_bundle_numeric_value(payload, "delta_threshold"))
        trigger_window = _bundle_integer_value(payload, "trigger_window")
        regression_window = _bundle_integer_value(payload, "regression_window")
    except BundleError:
        raise
    except (TypeError, ValueError, OverflowError) as exc:
        raise BundleError("bundle loop settings must use valid numbers") from exc
    if not math.isfinite(iteration_interval_seconds) or not math.isfinite(delta_threshold):
        raise BundleError("bundle loop settings must use finite numbers")
    if max_iters < 0:
        raise BundleError("bundle loop.max_iters must be >= 0")
    if max_role_retries < 0:
        raise BundleError("bundle loop.max_role_retries must be >= 0")
    if delta_threshold < 0:
        raise BundleError("bundle loop.delta_threshold must be >= 0")
    if trigger_window < 1:
        raise BundleError("bundle loop.trigger_window must be >= 1")
    if regression_window < 1:
        raise BundleError("bundle loop.regression_window must be >= 1")
    if iteration_interval_seconds < 0:
        raise BundleError("bundle loop.iteration_interval_seconds must be >= 0")
    return {
        "iteration_interval_seconds": iteration_interval_seconds,
        "max_iters": max_iters,
        "max_role_retries": max_role_retries,
        "delta_threshold": delta_threshold,
        "trigger_window": trigger_window,
        "regression_window": regression_window,
    }


def _bundle_numeric_value(payload: Mapping[str, Any], key: str) -> object:
    value = payload.get(key, BUNDLE_DEFAULT_LOOP[key])
    if value is None:
        return BUNDLE_DEFAULT_LOOP[key]
    if isinstance(value, str) and not value.strip():
        return BUNDLE_DEFAULT_LOOP[key]
    if isinstance(value, bool):
        raise BundleError("bundle loop settings must use valid numbers")
    return value


def _bundle_integer_value(payload: Mapping[str, Any], key: str) -> int:
    value = _bundle_numeric_value(payload, key)
    try:
        return coerce_integral_number(value, field_name=f"bundle loop.{key}")
    except ValueError as exc:
        raise BundleError(str(exc)) from exc
