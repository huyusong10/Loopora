from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
import shlex


def loop_compose_retry_command(  # noqa: PLR0913 - mirrors the public compose CLI option surface.
    prefix: str,
    *,
    spec: Path | str,
    workdir: Path | str,
    executor_kind: str = "codex",
    executor_mode: str = "preset",
    model: str = "",
    reasoning_effort: str = "",
    completion_mode: str = "gatekeeper",
    iteration_interval_seconds: float = 0.0,
    command_cli: str = "",
    command_arg: Sequence[str] | None = None,
    max_iters: int = 8,
    max_role_retries: int = 2,
    delta_threshold: float = 0.005,
    trigger_window: int = 4,
    regression_window: int = 2,
    name: str | None = None,
    role_model: Sequence[str] | None = None,
    orchestration_id: str = "",
    strategy_preset: str = "",
    strategy_file: Path | None = None,
    include_start: bool = False,
    start: bool = False,
    background: bool = False,
    json_output: bool = False,
) -> str:
    parts = _loop_compose_retry_command_parts(
        prefix,
        spec_arg=_quote_path(spec),
        workdir_arg=_quote_path(workdir),
        executor_kind=executor_kind,
        executor_mode=executor_mode,
        model=model,
        reasoning_effort=reasoning_effort,
        completion_mode=completion_mode,
        iteration_interval_seconds=iteration_interval_seconds,
        command_cli=command_cli,
        command_arg=command_arg,
        max_iters=max_iters,
        max_role_retries=max_role_retries,
        delta_threshold=delta_threshold,
        trigger_window=trigger_window,
        regression_window=regression_window,
        name=name,
        role_model=role_model,
        orchestration_id=orchestration_id,
        strategy_preset=strategy_preset,
        strategy_file=strategy_file,
        include_start=include_start,
        start=start,
        background=background,
        json_output=json_output,
    )
    return " ".join(parts)


def loop_compose_retry_command_template(  # noqa: PLR0913 - mirrors the public compose CLI option surface.
    prefix: str,
    *,
    workdir: Path | str | None,
    spec_placeholder: str = "<spec-path>",
    executor_kind: str = "codex",
    executor_mode: str = "preset",
    model: str = "",
    reasoning_effort: str = "",
    completion_mode: str = "gatekeeper",
    iteration_interval_seconds: float = 0.0,
    command_cli: str = "",
    command_arg: Sequence[str] | None = None,
    max_iters: int = 8,
    max_role_retries: int = 2,
    delta_threshold: float = 0.005,
    trigger_window: int = 4,
    regression_window: int = 2,
    name: str | None = None,
    role_model: Sequence[str] | None = None,
    orchestration_id: str = "",
    strategy_preset: str = "",
    strategy_file: Path | None = None,
    include_start: bool = False,
    start: bool = False,
    background: bool = False,
    json_output: bool = False,
) -> str:
    if not str(workdir or "").strip():
        return ""
    try:
        parts = _loop_compose_retry_command_parts(
            prefix,
            spec_arg=spec_placeholder,
            workdir_arg=_quote_path(str(workdir)),
            executor_kind=executor_kind,
            executor_mode=executor_mode,
            model=model,
            reasoning_effort=reasoning_effort,
            completion_mode=completion_mode,
            iteration_interval_seconds=iteration_interval_seconds,
            command_cli=command_cli,
            command_arg=command_arg,
            max_iters=max_iters,
            max_role_retries=max_role_retries,
            delta_threshold=delta_threshold,
            trigger_window=trigger_window,
            regression_window=regression_window,
            name=name,
            role_model=role_model,
            orchestration_id=orchestration_id,
            strategy_preset=strategy_preset,
            strategy_file=strategy_file,
            include_start=include_start,
            start=start,
            background=background,
            json_output=json_output,
        )
    except (OSError, RuntimeError, ValueError):
        return ""
    return " ".join(parts)


def _loop_compose_retry_command_parts(  # noqa: PLR0913 - mirrors the public compose CLI option surface.
    prefix: str,
    *,
    spec_arg: str,
    workdir_arg: str,
    executor_kind: str,
    executor_mode: str,
    model: str,
    reasoning_effort: str,
    completion_mode: str,
    iteration_interval_seconds: float,
    command_cli: str,
    command_arg: Sequence[str] | None,
    max_iters: int,
    max_role_retries: int,
    delta_threshold: float,
    trigger_window: int,
    regression_window: int,
    name: str | None,
    role_model: Sequence[str] | None,
    orchestration_id: str,
    strategy_preset: str,
    strategy_file: Path | None,
    include_start: bool,
    start: bool,
    background: bool,
    json_output: bool,
) -> list[str]:
    parts = [prefix, "--spec", spec_arg, "--workdir", workdir_arg]
    _append_non_default(parts, "--executor", executor_kind, default="codex")
    _append_non_default(parts, "--executor-mode", executor_mode, default="preset")
    _append_text(parts, "--model", model)
    _append_text(parts, "--reasoning-effort", reasoning_effort)
    _append_non_default(parts, "--completion-mode", completion_mode, default="gatekeeper")
    _append_non_default_number(parts, "--iteration-interval-seconds", iteration_interval_seconds, default=0.0)
    _append_text(parts, "--command-cli", command_cli)
    for item in command_arg or ():
        _append_text(parts, "--command-arg", item)
    _append_non_default_number(parts, "--max-iters", max_iters, default=8)
    _append_non_default_number(parts, "--max-role-retries", max_role_retries, default=2)
    _append_non_default_number(parts, "--delta-threshold", delta_threshold, default=0.005)
    _append_non_default_number(parts, "--trigger-window", trigger_window, default=4)
    _append_non_default_number(parts, "--regression-window", regression_window, default=2)
    _append_text(parts, "--name", name or "")
    for item in role_model or ():
        _append_text(parts, "--role-model", item)
    _append_effective_strategy_options(
        parts,
        orchestration_id=orchestration_id,
        strategy_preset=strategy_preset,
        strategy_file=strategy_file,
    )
    if include_start and start:
        parts.append("--start")
    if background:
        parts.append("--background")
    if json_output:
        parts.append("--json")
    return parts


def loop_compose_retry_command_or_empty(  # noqa: PLR0913 - mirrors the public compose CLI option surface.
    prefix: str,
    *,
    spec: Path | str | None,
    workdir: Path | str | None,
    executor_kind: str = "codex",
    executor_mode: str = "preset",
    model: str = "",
    reasoning_effort: str = "",
    completion_mode: str = "gatekeeper",
    iteration_interval_seconds: float = 0.0,
    command_cli: str = "",
    command_arg: Sequence[str] | None = None,
    max_iters: int = 8,
    max_role_retries: int = 2,
    delta_threshold: float = 0.005,
    trigger_window: int = 4,
    regression_window: int = 2,
    name: str | None = None,
    role_model: Sequence[str] | None = None,
    orchestration_id: str = "",
    strategy_preset: str = "",
    strategy_file: Path | None = None,
    include_start: bool = False,
    start: bool = False,
    background: bool = False,
    json_output: bool = False,
) -> str:
    if not str(spec or "").strip() or not str(workdir or "").strip():
        return ""
    try:
        return loop_compose_retry_command(
            prefix,
            spec=str(spec),
            workdir=str(workdir),
            executor_kind=executor_kind,
            executor_mode=executor_mode,
            model=model,
            reasoning_effort=reasoning_effort,
            completion_mode=completion_mode,
            iteration_interval_seconds=iteration_interval_seconds,
            command_cli=command_cli,
            command_arg=command_arg,
            max_iters=max_iters,
            max_role_retries=max_role_retries,
            delta_threshold=delta_threshold,
            trigger_window=trigger_window,
            regression_window=regression_window,
            name=name,
            role_model=role_model,
            orchestration_id=orchestration_id,
            strategy_preset=strategy_preset,
            strategy_file=strategy_file,
            include_start=include_start,
            start=start,
            background=background,
            json_output=json_output,
        )
    except (OSError, RuntimeError, ValueError):
        return ""


def _append_text(parts: list[str], option: str, value: str) -> None:
    if str(value).strip():
        parts.extend([option, shlex.quote(str(value))])


def _append_effective_strategy_options(
    parts: list[str],
    *,
    orchestration_id: str,
    strategy_preset: str,
    strategy_file: Path | None,
) -> None:
    if strategy_file is not None:
        parts.extend(["--strategy-file", _quote_path(strategy_file)])
        return
    if str(orchestration_id or "").strip():
        _append_text(parts, "--orchestration-id", orchestration_id)
        return
    _append_text(parts, "--strategy-preset", strategy_preset)


def _append_non_default(parts: list[str], option: str, value: str, *, default: str) -> None:
    if value != default:
        _append_text(parts, option, value)


def _append_non_default_number(parts: list[str], option: str, value: float, *, default: float) -> None:
    if value != default:
        parts.extend([option, _format_number(value)])


def _format_number(value: float) -> str:
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _quote_path(path: Path | str) -> str:
    return shlex.quote(str(Path(path).expanduser().resolve(strict=False)))
