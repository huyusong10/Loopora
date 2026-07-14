from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loopora.cli_loop_compose_options import (
    normalize_loop_compose_runtime_options_or_exit,
    validate_loop_compose_semantic_options_or_exit,
)
from loopora.cli_loop_retry_commands import loop_compose_retry_command_or_empty, loop_compose_retry_command_template
from loopora.cli_loop_spec_recovery import exit_if_unusable_loop_spec, exit_if_unusable_loop_strategy_source
from loopora.cli_loop_workdir_recovery import exit_if_unusable_loop_workdir, exit_with_loop_workdir_recovery
from loopora.cli_shared import (
    BackgroundRunStartError,
    LoopCreateRequest,
    create_and_maybe_start_loop,
    echo_json,
    exit_with_background_run_start_failure,
    handle_error,
    loop_create_result_payload,
    print_loop_created,
    print_run_result,
)
from loopora.loop_compose_validation import LoopComposeRuntimeOptions
from loopora.service import LooporaError
from loopora.service_types import LooporaWorkdirUnavailableError
from loopora.spec_recovery_commands import SpecInitStrategyContext
from loopora.specs import SpecError
from loopora.strategy_source import StrategySourceError
from loopora.workdir_inputs import normalize_existing_spec_path, normalize_recoverable_workdir

__all__ = ["CliLoopCreateFlowOptions", "run_cli_loop_create_flow"]


@dataclass(frozen=True)
class CliLoopCreateFlowOptions:
    command_prefix: str
    action: str
    spec: Path | str | None
    workdir: Path | str | None
    executor_kind: str
    executor_mode: str
    model: str
    reasoning_effort: str
    completion_mode: str
    iteration_interval_seconds: object
    command_cli: str
    command_arg: list[str] | None
    max_iters: object
    max_role_retries: object
    delta_threshold: object
    trigger_window: object
    regression_window: object
    name: str | None
    role_model: list[str] | None
    orchestration_id: str
    strategy_preset: str
    strategy_file: Path | None
    start: bool
    include_start: bool = False
    background: bool = False
    json_output: bool = False


def run_cli_loop_create_flow(options: CliLoopCreateFlowOptions) -> None:
    runtime_options = normalize_loop_compose_runtime_options_or_exit(
        iteration_interval_seconds=options.iteration_interval_seconds,
        max_iters=options.max_iters,
        max_role_retries=options.max_role_retries,
        delta_threshold=options.delta_threshold,
        trigger_window=options.trigger_window,
        regression_window=options.regression_window,
        json_output=options.json_output,
    )
    validate_loop_compose_semantic_options_or_exit(
        executor_kind=options.executor_kind,
        executor_mode=options.executor_mode,
        reasoning_effort=options.reasoning_effort,
        completion_mode=options.completion_mode,
        command_arg=options.command_arg,
        role_model=options.role_model,
        strategy_preset=options.strategy_preset,
        orchestration_id=options.orchestration_id,
        strategy_file=options.strategy_file,
        json_output=options.json_output,
    )
    retry_command = _loop_create_retry_command(options, runtime_options)
    retry_command_template = _loop_create_retry_command_template(options, runtime_options)
    strategy_context = _strategy_context(options)
    _preflight_loop_create_inputs(
        options,
        retry_command=retry_command,
        retry_command_template=retry_command_template,
        strategy_context=strategy_context,
    )
    try:
        loop, result = create_and_maybe_start_loop(_loop_create_request(options, runtime_options))
        if options.json_output:
            echo_json(loop_create_result_payload(loop, result))
            return
        print_loop_created(loop)
        if result is not None:
            print_run_result(result)
    except BackgroundRunStartError as exc:
        exit_with_background_run_start_failure(
            exc,
            json_output=options.json_output,
            retry_command=retry_command,
        )
    except LooporaWorkdirUnavailableError as exc:
        exit_with_loop_workdir_recovery(
            workdir=exc.workdir,
            action=options.action,
            retry_command=retry_command,
            json_output=options.json_output,
            retry_before_readiness=True,
            strategy_context=strategy_context,
        )
    except (LooporaError, SpecError, StrategySourceError, FileExistsError) as exc:
        handle_error(exc, json_output=options.json_output, recovery_workdir=options.workdir)


def _loop_create_retry_command(options: CliLoopCreateFlowOptions, runtime_options: LoopComposeRuntimeOptions) -> str:
    return loop_compose_retry_command_or_empty(
        options.command_prefix,
        spec=options.spec,
        workdir=options.workdir,
        executor_kind=options.executor_kind,
        executor_mode=options.executor_mode,
        model=options.model,
        reasoning_effort=options.reasoning_effort,
        completion_mode=options.completion_mode,
        iteration_interval_seconds=runtime_options.iteration_interval_seconds,
        command_cli=options.command_cli,
        command_arg=options.command_arg,
        max_iters=runtime_options.max_iters,
        max_role_retries=runtime_options.max_role_retries,
        delta_threshold=runtime_options.delta_threshold,
        trigger_window=runtime_options.trigger_window,
        regression_window=runtime_options.regression_window,
        name=options.name,
        role_model=options.role_model,
        orchestration_id=options.orchestration_id,
        strategy_preset=options.strategy_preset,
        strategy_file=options.strategy_file,
        include_start=options.include_start,
        start=options.start,
        background=options.background,
        json_output=options.json_output,
    )


def _loop_create_retry_command_template(
    options: CliLoopCreateFlowOptions,
    runtime_options: LoopComposeRuntimeOptions,
) -> str:
    return loop_compose_retry_command_template(
        options.command_prefix,
        workdir=options.workdir,
        executor_kind=options.executor_kind,
        executor_mode=options.executor_mode,
        model=options.model,
        reasoning_effort=options.reasoning_effort,
        completion_mode=options.completion_mode,
        iteration_interval_seconds=runtime_options.iteration_interval_seconds,
        command_cli=options.command_cli,
        command_arg=options.command_arg,
        max_iters=runtime_options.max_iters,
        max_role_retries=runtime_options.max_role_retries,
        delta_threshold=runtime_options.delta_threshold,
        trigger_window=runtime_options.trigger_window,
        regression_window=runtime_options.regression_window,
        name=options.name,
        role_model=options.role_model,
        orchestration_id=options.orchestration_id,
        strategy_preset=options.strategy_preset,
        strategy_file=options.strategy_file,
        include_start=options.include_start,
        start=options.start,
        background=options.background,
        json_output=options.json_output,
    )


def _strategy_context(options: CliLoopCreateFlowOptions) -> SpecInitStrategyContext:
    return SpecInitStrategyContext(
        orchestration_id=options.orchestration_id,
        strategy_preset=options.strategy_preset,
        strategy_file=options.strategy_file,
    )


def _preflight_loop_create_inputs(
    options: CliLoopCreateFlowOptions,
    *,
    retry_command: str,
    retry_command_template: str,
    strategy_context: SpecInitStrategyContext,
) -> None:
    exit_if_unusable_loop_workdir(
        workdir=options.workdir,
        action=options.action,
        retry_command=retry_command,
        json_output=options.json_output,
        retry_before_readiness=True,
        strategy_context=strategy_context,
    )
    exit_if_unusable_loop_spec(
        spec=options.spec,
        action=options.action,
        retry_command=retry_command,
        retry_command_template=retry_command_template,
        strategy_context=strategy_context,
        json_output=options.json_output,
    )
    exit_if_unusable_loop_strategy_source(
        action=options.action,
        strategy_context=strategy_context,
        json_output=options.json_output,
    )


def _loop_create_request(
    options: CliLoopCreateFlowOptions,
    runtime_options: LoopComposeRuntimeOptions,
) -> LoopCreateRequest:
    spec_path = normalize_existing_spec_path(options.spec)
    workdir_path = normalize_recoverable_workdir(options.workdir, action="compose")
    return LoopCreateRequest(
        spec=spec_path,
        workdir=workdir_path,
        executor_kind=options.executor_kind,
        executor_mode=options.executor_mode,
        model=options.model,
        reasoning_effort=options.reasoning_effort,
        completion_mode=options.completion_mode,
        iteration_interval_seconds=runtime_options.iteration_interval_seconds,
        command_cli=options.command_cli,
        command_arg=options.command_arg,
        max_iters=runtime_options.max_iters,
        max_role_retries=runtime_options.max_role_retries,
        delta_threshold=runtime_options.delta_threshold,
        trigger_window=runtime_options.trigger_window,
        regression_window=runtime_options.regression_window,
        name=options.name,
        role_model=options.role_model,
        orchestration_id=options.orchestration_id,
        strategy_preset=options.strategy_preset,
        strategy_file=options.strategy_file,
        start=options.start,
        background=options.background,
    )
