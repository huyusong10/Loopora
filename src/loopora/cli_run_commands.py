from __future__ import annotations

import typer

from loopora.agent_adapter_command_prefix import rewrite_loopora_help_commands
from loopora.cli_loop_create_flow import CliLoopCreateFlowOptions, run_cli_loop_create_flow
from loopora.cli_shared import (
    BackgroundOption,
    CommandArgOption,
    CommandCliOption,
    CompletionModeOption,
    DeltaThresholdOption,
    ExecutorModeOption,
    ExecutorOption,
    IterationIntervalOption,
    JsonOutputOption,
    LoopCreateSpecOption,
    LoopCreateWorkdirOption,
    MaxItersOption,
    MaxRoleRetriesOption,
    ModelOption,
    NameOption,
    OrchestrationIdOption,
    ReasoningOption,
    RegressionWindowOption,
    RoleModelOption,
    StrategyFileOption,
    StrategyPresetOption,
    TriggerWindowOption,
)


def register_run_command(app: typer.Typer) -> None:
    @app.command(
        hidden=True,
        epilog=rewrite_loopora_help_commands(
            "Expert direct-run path: use `loopora run` only when you already have a reviewed Markdown spec and "
            "an existing target workdir. For first use, leave this direct-run command: run `loopora start` for "
            "route choice, use `loopora fit` when fit is uncertain, then choose a reviewed creation path. "
            "Fit Guide/Web choices path: open "
            '`loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742`, preview before creating or running, '
            "and continue in Web after READY review. Same-Agent path: choose the same-Agent project entry matching your current host, install it with "
            "`loopora init <agent> --workdir \"$PWD\"`, confirm `loopora doctor --workdir \"$PWD\"`, then review "
            "`/loopora-plan` before `/loopora-run`. "
            "`--json` is for automation; `--background` returns after queuing and keeps retry-start recovery "
            "structured if worker start fails."
        ),
    )
    def run(  # noqa: PLR0913 - Expert direct-run exposes the Loop compose option boundary.
        spec: LoopCreateSpecOption = None,
        workdir: LoopCreateWorkdirOption = None,
        executor_kind: ExecutorOption = "codex",
        executor_mode: ExecutorModeOption = "preset",
        model: ModelOption = "",
        reasoning_effort: ReasoningOption = "",
        completion_mode: CompletionModeOption = "gatekeeper",
        iteration_interval_seconds: IterationIntervalOption = "0.0",
        command_cli: CommandCliOption = "",
        command_arg: CommandArgOption = None,
        max_iters: MaxItersOption = "8",
        max_role_retries: MaxRoleRetriesOption = "2",
        delta_threshold: DeltaThresholdOption = "0.005",
        trigger_window: TriggerWindowOption = "4",
        regression_window: RegressionWindowOption = "2",
        name: NameOption = None,
        role_model: RoleModelOption = None,
        orchestration_id: OrchestrationIdOption = "",
        strategy_preset: StrategyPresetOption = "",
        strategy_file: StrategyFileOption = None,
        *,
        background: BackgroundOption = False,
        json_output: JsonOutputOption = False,
    ) -> None:
        """Expert: create and run a Loop from an existing spec file."""
        run_cli_loop_create_flow(
            CliLoopCreateFlowOptions(
                command_prefix="loopora run",
                action="run",
                spec=spec,
                workdir=workdir,
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
                start=True,
                background=background,
                json_output=json_output,
            )
        )
