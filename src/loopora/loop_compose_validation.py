from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math

from loopora.executor_command_args import coerce_reasoning_effort, normalize_reasoning_effort, validate_command_args_text
from loopora.numeric_inputs import coerce_integral_number
from loopora.providers import executor_profile, normalize_executor_kind, normalize_executor_mode
from loopora.service_types import LooporaError, normalize_completion_mode


@dataclass(frozen=True)
class LoopComposeRuntimeOptions:
    iteration_interval_seconds: float
    max_iters: int
    max_role_retries: int
    delta_threshold: float
    trigger_window: int
    regression_window: int


@dataclass(frozen=True)
class LoopComposeExecutionOptions:
    executor_kind: str
    executor_mode: str
    command_cli: str
    command_args_text: str
    model: str
    reasoning_effort: str
    completion_mode: str


def normalize_loop_compose_runtime_options(  # noqa: PLR0913 - mirrors the public compose numeric option boundary.
    *,
    iteration_interval_seconds: object,
    max_iters: object,
    max_role_retries: object,
    delta_threshold: object,
    trigger_window: object,
    regression_window: object,
) -> LoopComposeRuntimeOptions:
    return LoopComposeRuntimeOptions(
        iteration_interval_seconds=_finite_float(
            iteration_interval_seconds,
            option="--iteration-interval-seconds",
            minimum=0.0,
        ),
        max_iters=_integer(max_iters, option="--max-iters", minimum=0),
        max_role_retries=_integer(max_role_retries, option="--max-role-retries", minimum=0),
        delta_threshold=_finite_float(delta_threshold, option="--delta-threshold", minimum=0.0),
        trigger_window=_integer(trigger_window, option="--trigger-window", minimum=1),
        regression_window=_integer(regression_window, option="--regression-window", minimum=1),
    )


def normalize_loop_compose_execution_options(  # noqa: PLR0913 - mirrors the public compose execution option boundary.
    *,
    executor_kind: object,
    executor_mode: object,
    reasoning_effort: object,
    completion_mode: object,
    command_cli: object = "",
    command_args_text: object = "",
    command_arg: list[str] | None = None,
    model: object = "",
    force_command_mode_for_command_only_executor: bool = False,
    coerce_invalid_reasoning_effort: bool = False,
) -> LoopComposeExecutionOptions:
    normalized_executor = _normalize_option(
        "--executor",
        lambda: normalize_executor_kind(_text_option(executor_kind, default="codex")),
    )
    normalized_executor_mode = _normalize_option(
        "--executor-mode",
        lambda: normalize_executor_mode(_text_option(executor_mode, default="preset")),
    )
    profile = executor_profile(normalized_executor)
    if profile.command_only and force_command_mode_for_command_only_executor:
        normalized_executor_mode = "command"
    if profile.command_only and normalized_executor_mode != "command":
        raise ValueError(f"invalid --executor-mode: {profile.label} only supports command mode")
    normalized_completion_mode = _normalize_option(
        "--completion-mode",
        lambda: normalize_completion_mode(_text_option(completion_mode, default="gatekeeper")),
    )
    normalized_model = str(model or "").strip()
    if normalized_executor_mode == "preset":
        return LoopComposeExecutionOptions(
            executor_kind=normalized_executor,
            executor_mode=normalized_executor_mode,
            command_cli="",
            command_args_text="",
            model=normalized_model or profile.default_model,
            reasoning_effort=_normalize_option(
                "--reasoning-effort",
                lambda: _normalize_reasoning_effort(
                    reasoning_effort,
                    executor_kind=normalized_executor,
                    coerce_invalid=coerce_invalid_reasoning_effort,
                ),
            ),
            completion_mode=normalized_completion_mode,
        )

    normalized_command_args_text = _command_args_text(command_arg=command_arg, command_args_text=command_args_text)
    _normalize_option(
        "--command-arg",
        lambda: validate_command_args_text(
            normalized_command_args_text,
            executor_kind=normalized_executor,
        ),
    )
    return LoopComposeExecutionOptions(
        executor_kind=normalized_executor,
        executor_mode=normalized_executor_mode,
        command_cli=str(command_cli or "").strip() or profile.cli_name,
        command_args_text=normalized_command_args_text,
        model=normalized_model,
        reasoning_effort=str(reasoning_effort or "").strip(),
        completion_mode=normalized_completion_mode,
    )


def default_loop_role_execution_options(
    executor_kind: object = "codex",
    *,
    completion_mode: object = "gatekeeper",
) -> LoopComposeExecutionOptions:
    normalized_executor = _normalize_option(
        "--executor",
        lambda: normalize_executor_kind(_text_option(executor_kind, default="codex")),
    )
    normalized_completion_mode = _normalize_option(
        "--completion-mode",
        lambda: normalize_completion_mode(_text_option(completion_mode, default="gatekeeper")),
    )
    profile = executor_profile(normalized_executor)
    executor_mode = "command" if profile.command_only else "preset"
    return LoopComposeExecutionOptions(
        executor_kind=profile.key,
        executor_mode=executor_mode,
        command_cli=profile.cli_name,
        command_args_text="\n".join(profile.command_args_template) if executor_mode == "command" else "",
        model=profile.default_model,
        reasoning_effort=profile.effort_default,
        completion_mode=normalized_completion_mode,
    )


def normalize_loop_role_execution_options(  # noqa: PLR0913 - mirrors saved role execution settings.
    *,
    executor_kind: object,
    executor_mode: object,
    reasoning_effort: object,
    completion_mode: object = "gatekeeper",
    command_cli: object = "",
    command_args_text: object = "",
    model: object = "",
) -> LoopComposeExecutionOptions:
    execution_options = normalize_loop_compose_execution_options(
        executor_kind=executor_kind,
        executor_mode=executor_mode,
        reasoning_effort=reasoning_effort,
        completion_mode=completion_mode,
        command_cli=command_cli,
        command_args_text=command_args_text,
        model=model,
    )
    if execution_options.executor_mode != "preset":
        return execution_options
    defaults = default_loop_role_execution_options(
        execution_options.executor_kind,
        completion_mode=execution_options.completion_mode,
    )
    return LoopComposeExecutionOptions(
        executor_kind=execution_options.executor_kind,
        executor_mode=execution_options.executor_mode,
        command_cli=defaults.command_cli,
        command_args_text=execution_options.command_args_text,
        model=execution_options.model,
        reasoning_effort=execution_options.reasoning_effort,
        completion_mode=execution_options.completion_mode,
    )


def validate_loop_compose_semantic_options(  # noqa: PLR0913 - mirrors the public compose semantic option boundary.
    *,
    executor_kind: object,
    executor_mode: object,
    reasoning_effort: object,
    completion_mode: object,
    command_args_text: object = "",
    command_arg: list[str] | None = None,
    role_model: list[str] | None = None,
    role_models: Mapping[str, object] | None = None,
    strategy_preset: object = "",
    orchestration_id: object = "",
    strategy_file: object = None,
) -> None:
    normalize_loop_compose_execution_options(
        executor_kind=executor_kind,
        executor_mode=executor_mode,
        reasoning_effort=reasoning_effort,
        completion_mode=completion_mode,
        command_args_text=command_args_text,
        command_arg=command_arg,
    )
    _validate_role_models(role_model=role_model, role_models=role_models)
    _validate_strategy_preset(
        strategy_preset=strategy_preset,
        orchestration_id=orchestration_id,
        strategy_file=strategy_file,
    )


def _integer(value: object, *, option: str, minimum: int) -> int:
    try:
        number = coerce_integral_number(value, field_name=option)
    except ValueError as exc:
        raise ValueError(f"invalid {option}: {_message_without_option_prefix(exc, option)}") from exc
    if number < minimum:
        raise ValueError(f"invalid {option}: must be >= {minimum}")
    return number


def _finite_float(value: object, *, option: str, minimum: float) -> float:
    if isinstance(value, bool):
        raise ValueError(f"invalid {option}: must be a finite number")
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid {option}: must be a finite number") from exc
    if not math.isfinite(number):
        raise ValueError(f"invalid {option}: must be a finite number")
    if number < minimum:
        raise ValueError(f"invalid {option}: must be >= {_format_minimum(minimum)}")
    return number


def _command_args_text(*, command_arg: list[str] | None, command_args_text: object) -> str:
    if command_arg is not None:
        return "\n".join(str(item) for item in command_arg if str(item).strip())
    return str(command_args_text or "")


def _text_option(value: object, *, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _normalize_reasoning_effort(value: object, *, executor_kind: str, coerce_invalid: bool) -> str:
    normalized = _text_option(value, default="")
    if coerce_invalid:
        return coerce_reasoning_effort(normalized, executor_kind)
    return normalize_reasoning_effort(normalized, executor_kind)


def _message_without_option_prefix(exc: ValueError, option: str) -> str:
    message = str(exc)
    prefix = f"{option} "
    if message.startswith(prefix):
        return message[len(prefix) :]
    return message


def _format_minimum(value: float) -> str:
    return str(int(value)) if value.is_integer() else f"{value:g}"


def _normalize_option(option: str, normalize) -> object:
    try:
        return normalize()
    except (LooporaError, ValueError) as exc:
        message = str(exc)
        if message.startswith(f"invalid {option}:"):
            raise ValueError(message) from exc
        raise ValueError(f"invalid {option}: {message}") from exc


def _validate_role_models(
    *,
    role_model: list[str] | None,
    role_models: Mapping[str, object] | None,
) -> None:
    from loopora.strategy_source_roles import normalize_strategy_role_models

    parsed: dict[str, str] = {}
    for key, value in dict(role_models or {}).items():
        parsed[str(key).strip()] = str(value).strip()
    for item in role_model or ():
        if "=" not in item:
            raise ValueError("invalid --role-model: expected ROLE=MODEL")
        role, model = item.split("=", 1)
        parsed[role.strip()] = model.strip()
    _normalize_option("--role-model", lambda: normalize_strategy_role_models(parsed))


def _validate_strategy_preset(*, strategy_preset: object, orchestration_id: object, strategy_file: object) -> None:
    from loopora.strategy_source_presets import strategy_source_preset_names

    if strategy_file is not None or str(orchestration_id or "").strip():
        return
    preset = str(strategy_preset or "").strip()
    if not preset:
        return
    supported = strategy_source_preset_names(include_hidden=True)
    if preset not in supported:
        raise ValueError(
            "invalid --strategy-preset: unknown workflow preset: "
            f"{preset}. Expected one of: {', '.join(supported)}"
        )
