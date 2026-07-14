from __future__ import annotations

import logging

import typer

from loopora.agent_adapter_command_prefix import rewrite_loopora_help_commands
from loopora.cli_loop_create_flow import CliLoopCreateFlowOptions, run_cli_loop_create_flow
from loopora.cli_loop_export_commands import register_loop_export_command
from loopora.cli_loop_saved_work import (
    cli_loop_delete_preview_payload as _cli_loop_delete_preview_payload,
    cli_loop_list_item as _cli_loop_list_item,
    cli_loop_status_payload as _cli_loop_status_payload,
    copyable_loop_rerun_retry_command as _copyable_loop_rerun_retry_command,
    exit_with_loop_identifier_recovery as _exit_with_loop_identifier_recovery,
    loop_rerun_retry_command as _loop_rerun_retry_command,
    normalize_loop_identifier as _normalize_loop_identifier,
)
from loopora.cli_shared import (
    BackgroundOption,
    BackgroundRunStartError,
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
    StartOption,
    StrategyFileOption,
    StrategyPresetOption,
    TriggerWindowOption,
    echo_json,
    exit_with_background_run_start_failure,
    handle_error,
    logger,
    get_service,
    print_run_result,
    run_result_payload,
    start_run,
)
from loopora.cli_loop_workdir_recovery import exit_with_loop_workdir_recovery
from loopora.diagnostics import log_event
from loopora.service import LooporaError
from loopora.service_types import LooporaWorkdirUnavailableError

LOOPS_HELP_EPILOG = (
    "Saved Loops are the library and operations surface after a Loop has been reviewed. Use "
    "`loops list/status/rerun` to inspect evidence, verdict, residual risk, next action, and retry-start state for "
    "existing Loops; use `loops export-run` to carry one private review package. For a new task, leave this group: run "
    "`loopora start` for the read-only route chooser, use "
    "`loopora fit` when fit is uncertain, then choose either the Fit Guide/Web choices path with "
    '`loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742`, or the same-Agent path by choosing the '
    "same-Agent project entry matching your current host, then using "
    '`loopora init <agent> --workdir "$PWD"` plus `loopora doctor --workdir "$PWD"` before '
    "`/loopora-plan` and `/loopora-run`."
)
LOOPS_CREATE_HELP_EPILOG = (
    "Expert saved-Loop creation path: use `loopora loops create` only when you already have a reviewed Markdown spec "
    "and an existing target workdir. Without `--start` it only saves the Loop; with `--start` it starts a run, and "
    "`--background` queues that run. For first use, leave this direct-create command: run `loopora start` for route "
    "choice, use `loopora fit` when fit is uncertain, then choose a reviewed creation path. Fit Guide/Web choices "
    'path: open `loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742`, preview '
    "before creating or running, and continue in Web after READY review. Same-Agent path: choose the same-Agent project "
    'entry matching your current host, install it with `loopora init <agent> --workdir "$PWD"`, confirm '
    '`loopora doctor --workdir "$PWD"`, then review `/loopora-plan` before `/loopora-run`.'
)
LOOPS_LIST_HELP_EPILOG = (
    "List is the scan surface for existing work. Plain output shows each saved Loop with its latest status and the "
    "first copyable next command when Loopora knows one; `--json` returns the full listed projections for automation. "
    "Use `loopora loops status <loop-or-run-id>` before continuing when you need evidence, verdict, residual-risk, or "
    "retry-start detail."
)
LOOPS_STATUS_HELP_EPILOG = (
    "Status is the inspection surface before continuing existing work. It always prints structured JSON for a Loop ID "
    "or Run ID, including latest run state, task-verdict projection, residual-risk detail, and next actions when "
    "available. Loop status also includes `run_progress`, which compares stable coverage targets across the latest two "
    "Runs without treating extra evidence count or a changed contract as proof of progress. Run status includes the "
    "frozen `continuation` action mode and prior-run trajectory when this Run follows unresolved work. It does not "
    "start, stop, delete, or rewrite work; use Web for a readable review or "
    "`loopora loops rerun <loop-id>` when a reviewed Loop needs another run."
)
LOOPS_STOP_HELP_EPILOG = (
    "Stop is a lifecycle request for an existing Run. It asks Loopora to stop queued/running work and reports the "
    "resulting run state; it is not task proof and does not delete Loop artifacts."
)
LOOPS_RERUN_HELP_EPILOG = (
    "Rerun starts the next Run from a saved reviewed Loop definition. An unresolved latest Run or lifecycle failure "
    "seeds the next Run with its evidence gaps; a recorded result stays closed. It reuses the saved workdir and "
    "recovery boundary, and does not rewrite the Loop definition, replace earlier run history, or resume an exact "
    "same-Agent session. "
    "Use `loopora loops status <loop-id>` or Web first when you need to inspect evidence, verdict, residual risk, or "
    "retry-start state; use `/loopora-run` to resume through the current Agent binding. Use --background to queue the "
    "new run."
)
LOOPS_DELETE_HELP_EPILOG = (
    "Delete removes one saved Loop definition and its Loopora-managed run artifacts from local state. It does not "
    "delete the target project workdir, source spec file, exported Plan Files, or external provider history. Use "
    "--dry-run to preview the delete scope and active-run blockers without deleting anything."
)

def register_loop_commands(loops_app: typer.Typer) -> None:
    _register_loop_create_command(loops_app)
    _register_loop_list_command(loops_app)
    _register_loop_status_command(loops_app)
    register_loop_export_command(loops_app)
    _register_loop_stop_command(loops_app)
    _register_loop_rerun_command(loops_app)
    _register_loop_delete_command(loops_app)


def _register_loop_create_command(loops_app: typer.Typer) -> None:
    @loops_app.command("create", epilog=rewrite_loopora_help_commands(LOOPS_CREATE_HELP_EPILOG))
    def create_loop(
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
        start: StartOption = False,
        background: BackgroundOption = False,
        json_output: JsonOutputOption = False,
    ) -> None:
        """Create a saved loop definition, optionally starting a run immediately."""
        run_cli_loop_create_flow(
            CliLoopCreateFlowOptions(
                command_prefix="loopora loops create",
                action="create",
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
                start=start,
                include_start=True,
                background=background,
                json_output=json_output,
            )
        )


def _register_loop_list_command(loops_app: typer.Typer) -> None:
    @loops_app.command("list", epilog=rewrite_loopora_help_commands(LOOPS_LIST_HELP_EPILOG))
    def list_loops(*, json_output: JsonOutputOption = False) -> None:
        """List known loop definitions."""
        try:
            service = get_service()
            loops = service.list_loops()
            projected_loops = [_cli_loop_list_item(loop) for loop in loops]
            if json_output:
                echo_json({"status": "ok", "count": len(projected_loops), "loops": projected_loops})
                return
            if not projected_loops:
                typer.echo("No loops found.")
                return
            for loop in projected_loops:
                status = loop.get("latest_status_label") or loop.get("latest_status") or "draft"
                next_actions = loop.get("next_actions") if isinstance(loop.get("next_actions"), list) else []
                next_command = str(next_actions[0].get("command") or "").strip() if next_actions and isinstance(next_actions[0], dict) else ""
                next_text = f"  next={next_command}" if next_command else ""
                typer.echo(
                    f"{loop['id']}  {loop['name']}  [{status}]  "
                    f"{loop['workdir']}  executor={loop.get('executor_kind', 'codex')}  model={loop['model'] or '-'}{next_text}"
                )
        except LooporaError as exc:
            handle_error(exc, json_output=json_output)


def _register_loop_status_command(loops_app: typer.Typer) -> None:
    @loops_app.command("status", epilog=rewrite_loopora_help_commands(LOOPS_STATUS_HELP_EPILOG))
    def loop_status(identifier: str | None = typer.Argument(None, help="Loop ID or run ID.")) -> None:
        """Show status for a loop or a specific run."""
        identifier_value = _normalize_loop_identifier(identifier)
        if not identifier_value:
            _exit_with_loop_identifier_recovery(action="status", identifier_kind="loop_or_run_id")
        try:
            service = get_service()
            _kind, payload = service.get_status(identifier_value)
            echo_json(_cli_loop_status_payload(_kind, payload))
        except LooporaError as exc:
            handle_error(exc, json_output=True)


def _register_loop_stop_command(loops_app: typer.Typer) -> None:
    @loops_app.command("stop", epilog=LOOPS_STOP_HELP_EPILOG)
    def stop_run(
        run_id: str | None = typer.Argument(None, help="Run ID."),
        *,
        json_output: JsonOutputOption = False,
    ) -> None:
        """Request a running loop to stop."""
        run_id_value = _normalize_loop_identifier(run_id)
        if not run_id_value:
            _exit_with_loop_identifier_recovery(action="stop", identifier_kind="run_id", json_output=json_output)
        try:
            service = get_service()
            run = service.stop_run(run_id_value)
            log_event(
                logger,
                logging.INFO,
                "cli.run.stop_requested",
                "Requested run stop from the CLI",
                run_id=run["id"],
                loop_id=run.get("loop_id"),
                status=run.get("status"),
            )
            if json_output:
                echo_json(run)
                return
            typer.echo(f"stop requested for {run['id']} ({run['status']})")
        except LooporaError as exc:
            handle_error(exc, json_output=json_output)


def _register_loop_rerun_command(loops_app: typer.Typer) -> None:
    @loops_app.command("rerun", epilog=rewrite_loopora_help_commands(LOOPS_RERUN_HELP_EPILOG))
    def rerun_loop(
        loop_id: str | None = typer.Argument(None, help="Loop definition ID."),
        *,
        background: BackgroundOption = False,
        json_output: JsonOutputOption = False,
    ) -> None:
        """Start the next run from a saved loop definition."""
        loop_id_value = _normalize_loop_identifier(loop_id)
        if not loop_id_value:
            _exit_with_loop_identifier_recovery(action="rerun", identifier_kind="loop_id", json_output=json_output)
        try:
            service = get_service()
            result = start_run(
                service,
                loop_id_value,
                background=background,
                continue_saved_loop=True,
            )
            log_event(
                logger,
                logging.INFO,
                "cli.run.rerun_requested",
                "Started a rerun from the CLI",
                loop_id=loop_id_value,
                run_id=result["id"],
                background=background,
                status=result["status"],
            )
            if json_output:
                echo_json(
                    run_result_payload(
                        result,
                        json_output=json_output,
                        retry_command=_copyable_loop_rerun_retry_command(
                            loop_id_value,
                            background=background,
                            json_output=json_output,
                        ),
                    )
                )
                return
            print_run_result(result)
        except BackgroundRunStartError as exc:
            exit_with_background_run_start_failure(
                exc,
                json_output=json_output,
                retry_command=_loop_rerun_retry_command(loop_id_value, background=background, json_output=json_output),
            )
        except LooporaWorkdirUnavailableError as exc:
            exit_with_loop_workdir_recovery(
                workdir=exc.workdir,
                action="rerun",
                retry_command=_loop_rerun_retry_command(loop_id_value, background=background, json_output=json_output),
                json_output=json_output,
            )
        except LooporaError as exc:
            handle_error(exc, json_output=json_output)


def _register_loop_delete_command(loops_app: typer.Typer) -> None:
    @loops_app.command("delete", epilog=LOOPS_DELETE_HELP_EPILOG)
    def delete_loop(
        loop_id: str | None = typer.Argument(None, help="Loop definition ID."),
        *,
        dry_run: bool = typer.Option(default=False, help="Preview delete scope without deleting local state."),
    ) -> None:
        """Delete a saved loop definition and its run artifacts."""
        loop_id_value = _normalize_loop_identifier(loop_id)
        if not loop_id_value:
            _exit_with_loop_identifier_recovery(action="delete", identifier_kind="loop_id")
        try:
            service = get_service()
            if dry_run:
                payload = _cli_loop_delete_preview_payload(service.preview_loop_delete(loop_id_value), loop_id_value)
                echo_json(payload)
                return
            result = service.delete_loop(loop_id_value)
            log_event(
                logger,
                logging.INFO,
                "cli.loop.deleted",
                "Deleted loop from the CLI",
                loop_id=result["id"],
                workdir=result.get("workdir"),
                deleted_run_count=result.get("deleted_runs"),
            )
            echo_json(result)
        except LooporaError as exc:
            handle_error(exc, json_output=True)
