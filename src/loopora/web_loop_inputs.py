from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from loopora.loop_compose_validation import (
    LoopComposeExecutionOptions,
    LoopComposeRuntimeOptions,
    normalize_loop_compose_execution_options,
    normalize_loop_compose_runtime_options,
    validate_loop_compose_semantic_options,
)
from loopora.numeric_inputs import coerce_integral_number
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
    "executor_kind": "codex",
    "executor_mode": "preset",
    "command_cli": "",
    "command_args_text": "",
    "model": "",
    "reasoning_effort": "",
    "start_immediately": False,
}


def _loop_payload_from_mapping(payload: Mapping[str, object]) -> tuple[dict[str, object], bool]:
    name = str(payload.get("name", "")).strip()
    workdir = str(payload.get("workdir", "")).strip()
    spec_path = str(payload.get("spec_path", "")).strip()
    if not name:
        raise LooporaError("name is required")
    if not workdir:
        raise LooporaError("workdir is required")
    if not spec_path:
        raise LooporaError("spec path is required")

    runtime_options = _loop_runtime_options_from_mapping(payload)
    execution_options = _loop_execution_options_from_mapping(payload)
    _validate_loop_payload_semantic_options(payload)

    loop_kwargs = {
        "name": name,
        "spec_path": Path(spec_path),
        "workdir": Path(workdir),
        "orchestration_id": str(payload.get("orchestration_id", "")).strip() or None,
        "executor_kind": execution_options.executor_kind,
        "executor_mode": execution_options.executor_mode,
        "command_cli": execution_options.command_cli,
        "command_args_text": execution_options.command_args_text,
        "model": execution_options.model,
        "reasoning_effort": execution_options.reasoning_effort,
        "completion_mode": execution_options.completion_mode,
        "iteration_interval_seconds": runtime_options.iteration_interval_seconds,
        "max_iters": runtime_options.max_iters,
        "max_role_retries": runtime_options.max_role_retries,
        "delta_threshold": runtime_options.delta_threshold,
        "trigger_window": runtime_options.trigger_window,
        "regression_window": runtime_options.regression_window,
        "workflow": _loop_strategy_source_from_mapping(payload),
        "prompt_files": _prompt_files_from_mapping(payload),
        "role_models": _role_models_from_mapping(payload),
    }
    return loop_kwargs, _coerce_bool(payload.get("start_immediately"))


def validate_loop_payload_compose_options(payload: Mapping[str, object]) -> None:
    _loop_runtime_options_from_mapping(payload)
    _validate_loop_payload_semantic_options(payload)


def _loop_runtime_options_from_mapping(payload: Mapping[str, object]) -> LoopComposeRuntimeOptions:
    try:
        return normalize_loop_compose_runtime_options(
            iteration_interval_seconds=payload.get("iteration_interval_seconds", 0),
            max_iters=payload.get("max_iters", 8),
            max_role_retries=payload.get("max_role_retries", 2),
            delta_threshold=payload.get("delta_threshold", 0.005),
            trigger_window=payload.get("trigger_window", 4),
            regression_window=payload.get("regression_window", 2),
        )
    except (TypeError, ValueError, OverflowError) as exc:
        raise LooporaError(_web_loop_compose_error_message(str(exc))) from exc


def _loop_execution_options_from_mapping(payload: Mapping[str, object]) -> LoopComposeExecutionOptions:
    try:
        return normalize_loop_compose_execution_options(
            executor_kind=payload.get("executor_kind", "codex"),
            executor_mode=payload.get("executor_mode", "preset"),
            reasoning_effort=payload.get("reasoning_effort", ""),
            completion_mode=payload.get("completion_mode", "gatekeeper"),
            command_cli=payload.get("command_cli", ""),
            command_args_text=payload.get("command_args_text", ""),
            model=payload.get("model", ""),
        )
    except ValueError as exc:
        raise LooporaError(_web_loop_compose_error_message(str(exc))) from exc


def _validate_loop_payload_semantic_options(payload: Mapping[str, object]) -> None:
    try:
        validate_loop_compose_semantic_options(
            executor_kind=payload.get("executor_kind", "codex"),
            executor_mode=payload.get("executor_mode", "preset"),
            reasoning_effort=payload.get("reasoning_effort", ""),
            completion_mode=payload.get("completion_mode", "gatekeeper"),
            command_args_text=payload.get("command_args_text", ""),
            role_models=_raw_role_models_from_mapping(payload),
            strategy_preset=_loop_strategy_preset_from_mapping(payload),
            orchestration_id=payload.get("orchestration_id", ""),
            strategy_file=_strategy_source_from_mapping(payload, default_to_preset=False),
        )
    except ValueError as exc:
        raise LooporaError(_web_loop_compose_error_message(str(exc))) from exc


def _loop_strategy_source_from_mapping(payload: Mapping[str, object]) -> dict | None:
    strategy_source = _strategy_source_from_mapping(payload, default_to_preset=False)
    if strategy_source is not None:
        return strategy_source
    if str(payload.get("orchestration_id") or "").strip():
        return None
    preset = _loop_strategy_preset_from_mapping(payload)
    return {"preset": preset} if preset else None


def _loop_strategy_preset_from_mapping(payload: Mapping[str, object]) -> str:
    return str(payload.get("strategy_preset") or payload.get("workflow_preset") or "").strip()


def _raw_role_models_from_mapping(payload: Mapping[str, object]) -> dict[str, str]:
    role_models = payload.get("role_models")
    if isinstance(role_models, Mapping):
        return {str(key): str(value) for key, value in dict(role_models).items()}
    extracted = {}
    for role in ("builder", "inspector", "gatekeeper", "guide", "generator", "tester", "verifier", "challenger"):
        value = str(payload.get(f"role_model_{role}", "")).strip()
        if value:
            extracted[role] = value
    return extracted


def _web_loop_compose_error_message(message: str) -> str:
    replacements = {
        "invalid --iteration-interval-seconds:": "invalid iteration_interval_seconds:",
        "invalid --max-iters:": "invalid max_iters:",
        "invalid --max-role-retries:": "invalid max_role_retries:",
        "invalid --delta-threshold:": "invalid delta_threshold:",
        "invalid --trigger-window:": "invalid trigger_window:",
        "invalid --regression-window:": "invalid regression_window:",
        "invalid --executor:": "invalid executor_kind:",
        "invalid --executor-mode:": "invalid executor_mode:",
        "invalid --reasoning-effort:": "invalid reasoning_effort:",
        "invalid --completion-mode:": "invalid completion_mode:",
        "invalid --command-arg:": "invalid command_args_text:",
        "invalid --role-model:": "invalid role_models:",
        "invalid --strategy-preset:": "invalid strategy_preset:",
    }
    for cli_prefix, web_prefix in replacements.items():
        if message.startswith(cli_prefix):
            return f"{web_prefix}{message[len(cli_prefix):]}"
    return message


def _normalize_loop_form(values: Mapping[str, object] | None) -> dict[str, object]:
    normalized = dict(DEFAULT_LOOP_FORM)
    if not values:
        return normalized
    for key in normalized:
        if key in values:
            normalized[key] = values[key]
    normalized["start_immediately"] = _coerce_bool(normalized.get("start_immediately", False))
    return normalized


def _loop_form_is_pristine(values: Mapping[str, object] | None) -> bool:
    return _canonicalize_loop_form_for_comparison(values) == _canonicalize_loop_form_for_comparison(None)


def _canonicalize_loop_form_for_comparison(values: Mapping[str, object] | None) -> dict[str, object]:
    normalized = _normalize_loop_form(values)
    canonical = dict(normalized)
    for key, value in canonical.items():
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
