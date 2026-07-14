from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from loopora.bundle_contract import BUNDLE_DEFAULT_LOOP, BUNDLE_EXECUTION_FIELDS, BundleError
from loopora.loop_compose_validation import normalize_loop_compose_execution_options, normalize_loop_compose_runtime_options
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
    completion_mode = execution.pop("completion_mode")
    return {
        "name": name,
        "workdir": workdir,
        "completion_mode": completion_mode,
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
        execution_options = normalize_loop_compose_execution_options(
            executor_kind=payload.get("executor_kind", "codex"),
            executor_mode=payload.get("executor_mode", "preset"),
            reasoning_effort=payload.get("reasoning_effort", ""),
            completion_mode=payload.get("completion_mode", "gatekeeper"),
            command_cli=payload.get("command_cli", ""),
            command_args_text=payload.get("command_args_text", ""),
            model=payload.get("model", ""),
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
        raise BundleError(_bundle_loop_compose_error_message(str(exc))) from exc


def _normalize_bundle_loop_runtime(payload: Mapping[str, Any]) -> dict[str, int | float]:
    try:
        runtime_options = normalize_loop_compose_runtime_options(
            iteration_interval_seconds=_bundle_numeric_value(payload, "iteration_interval_seconds"),
            max_iters=_bundle_numeric_value(payload, "max_iters"),
            max_role_retries=_bundle_numeric_value(payload, "max_role_retries"),
            delta_threshold=_bundle_numeric_value(payload, "delta_threshold"),
            trigger_window=_bundle_numeric_value(payload, "trigger_window"),
            regression_window=_bundle_numeric_value(payload, "regression_window"),
        )
    except BundleError:
        raise
    except ValueError as exc:
        raise BundleError(_bundle_loop_compose_error_message(str(exc))) from exc
    return {
        "iteration_interval_seconds": runtime_options.iteration_interval_seconds,
        "max_iters": runtime_options.max_iters,
        "max_role_retries": runtime_options.max_role_retries,
        "delta_threshold": runtime_options.delta_threshold,
        "trigger_window": runtime_options.trigger_window,
        "regression_window": runtime_options.regression_window,
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


def _bundle_loop_compose_error_message(message: str) -> str:
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
            suffix = message[len(cli_prefix) :]
            if "must be a finite number" in suffix:
                return "bundle loop settings must use finite numbers"
            return f"bundle loop.{field_name}{suffix}"
    semantic_replacements = {
        "invalid --executor:": "bundle loop.executor_kind:",
        "invalid --executor-mode:": "bundle loop.executor_mode:",
        "invalid --reasoning-effort:": "bundle loop.reasoning_effort:",
        "invalid --completion-mode:": "bundle loop.completion_mode:",
        "invalid --command-arg:": "bundle loop.command_args_text:",
    }
    for cli_prefix, field_prefix in semantic_replacements.items():
        if message.startswith(cli_prefix):
            return f"{field_prefix}{message[len(cli_prefix):]}"
    return message
