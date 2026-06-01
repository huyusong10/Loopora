from __future__ import annotations

import math
from collections.abc import Mapping
from pathlib import Path

from loopora.numeric_inputs import coerce_integral_number
from loopora.providers import executor_profile
from loopora.service import LooporaError
from loopora.web_common_inputs import _coerce_bool
from loopora.web_strategy_inputs import (
    DEFAULT_STRATEGY_SOURCE_PRESET,
    _prompt_files_from_mapping,
    _role_models_from_mapping,
    _strategy_source_from_mapping,
)

DEFAULT_LOOP_FORM = {
    "name": "",
    "workdir": "",
    "spec_path": "",
    "orchestration_id": f"builtin:{DEFAULT_STRATEGY_SOURCE_PRESET}",
    "completion_mode": "gatekeeper",
    "iteration_interval_seconds": 0,
    "max_iters": 8,
    "max_role_retries": 2,
    "delta_threshold": 0.005,
    "trigger_window": 4,
    "regression_window": 2,
    "start_immediately": True,
}


def _loop_payload_from_mapping(payload: Mapping[str, object]) -> tuple[dict[str, object], bool]:
    name = str(payload.get("name", "")).strip()
    workdir = str(payload.get("workdir", "")).strip()
    spec_path = str(payload.get("spec_path", "")).strip()
    executor_kind = str(payload.get("executor_kind", "codex")).strip() or "codex"
    executor_mode = str(payload.get("executor_mode", "preset")).strip() or "preset"
    try:
        profile = executor_profile(executor_kind)
    except ValueError as exc:
        raise LooporaError(str(exc)) from exc
    model = str(payload.get("model", "")).strip()
    reasoning_effort = str(payload.get("reasoning_effort", "")).strip()
    command_cli = str(payload.get("command_cli", "")).strip()
    command_args_text = str(payload.get("command_args_text", ""))
    if not name:
        raise LooporaError("name is required")
    if not workdir:
        raise LooporaError("workdir is required")
    if not spec_path:
        raise LooporaError("spec path is required")

    try:
        iteration_interval_seconds = _loop_payload_number(payload, "iteration_interval_seconds", default=0, integer_only=False)
        max_iters = _loop_payload_number(payload, "max_iters", default=8, integer_only=True)
        max_role_retries = _loop_payload_number(payload, "max_role_retries", default=2, integer_only=True)
        delta_threshold = _loop_payload_number(payload, "delta_threshold", default=0.005, integer_only=False)
        trigger_window = _loop_payload_number(payload, "trigger_window", default=4, integer_only=True)
        regression_window = _loop_payload_number(payload, "regression_window", default=2, integer_only=True)
    except (TypeError, ValueError, OverflowError) as exc:
        raise LooporaError("numeric loop settings must use valid numbers") from exc
    if not math.isfinite(iteration_interval_seconds) or not math.isfinite(delta_threshold):
        raise LooporaError("numeric loop settings must use finite numbers")

    loop_kwargs = {
        "name": name,
        "spec_path": Path(spec_path),
        "workdir": Path(workdir),
        "orchestration_id": str(payload.get("orchestration_id", "")).strip() or None,
        "executor_kind": executor_kind,
        "executor_mode": executor_mode,
        "command_cli": command_cli if command_cli else profile.cli_name,
        "command_args_text": command_args_text,
        "model": model if model or profile.default_model == "" else profile.default_model,
        "reasoning_effort": reasoning_effort if reasoning_effort or profile.effort_default == "" else profile.effort_default,
        "completion_mode": str(payload.get("completion_mode", "gatekeeper")).strip() or "gatekeeper",
        "iteration_interval_seconds": iteration_interval_seconds,
        "max_iters": max_iters,
        "max_role_retries": max_role_retries,
        "delta_threshold": delta_threshold,
        "trigger_window": trigger_window,
        "regression_window": regression_window,
        "workflow": _strategy_source_from_mapping(payload, default_to_preset=False),
        "prompt_files": _prompt_files_from_mapping(payload),
        "role_models": _role_models_from_mapping(payload),
    }
    return loop_kwargs, _coerce_bool(payload.get("start_immediately"))


def _loop_payload_number(
    payload: Mapping[str, object],
    key: str,
    *,
    default: int | float,
    integer_only: bool,
) -> int | float:
    value = payload.get(key, default)
    if isinstance(value, bool):
        raise ValueError(f"{key} must be numeric")
    return coerce_integral_number(value, field_name=key) if integer_only else float(value)


def _normalize_loop_form(values: Mapping[str, object] | None) -> dict[str, object]:
    normalized = dict(DEFAULT_LOOP_FORM)
    if not values:
        return normalized
    for key in normalized:
        if key in values:
            normalized[key] = values[key]
    normalized["start_immediately"] = _coerce_bool(normalized.get("start_immediately", True))
    return normalized


def _loop_form_is_pristine(values: Mapping[str, object] | None) -> bool:
    return _canonicalize_loop_form_for_comparison(values) == _canonicalize_loop_form_for_comparison(None)


def _canonicalize_loop_form_for_comparison(values: Mapping[str, object] | None) -> dict[str, object]:
    normalized = _normalize_loop_form(values)
    canonical = dict(normalized)
    for key in canonical:
        value = canonical[key]
        if key == "start_immediately":
            canonical[key] = _coerce_bool(value)
            continue
        if key in {"max_iters", "max_role_retries", "trigger_window", "regression_window"}:
            canonical[key] = _coerce_loop_form_number(value, integer_only=True)
            continue
        if key in {"delta_threshold", "iteration_interval_seconds"}:
            canonical[key] = _coerce_loop_form_number(value, integer_only=False)
            continue
        if isinstance(value, str):
            canonical[key] = value.strip()
    return canonical


def _coerce_loop_form_number(value: object, *, integer_only: bool) -> object:
    if isinstance(value, str) and not value.strip():
        return ""
    try:
        return coerce_integral_number(value, field_name="loop setting") if integer_only else float(value)
    except (TypeError, ValueError):
        return value
