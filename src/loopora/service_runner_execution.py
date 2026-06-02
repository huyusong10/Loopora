from __future__ import annotations

import itertools
import logging
import os
from pathlib import Path

from loopora.diagnostics import get_logger, log_event
from loopora.engine import (
    RepositoryRunEngine,
    RunEngineStartIterationRequest,
)
from loopora.engine.runner_context import RunnerRunContext
from loopora.engine.runner_runtime import RunnerRunProgress
from loopora.executor_types import ExecutionStopped
from loopora.runners import headless_runner_actor
from loopora.service_types import (
    LooporaConflictError,
    LooporaNotFoundError,
    RoleExecutionError,
    StopRequestedError,
    WorkspaceSafetyError,
)
from loopora.service_runner_control_execution import ServiceRunnerControlExecutionMixin
from loopora.service_runner_context_preparation import ServiceRunnerContextPreparationMixin
from loopora.service_runner_failure_handling import ServiceRunnerFailureHandlingMixin
from loopora.service_runner_iteration_progress import ServiceRunnerIterationProgressMixin
from loopora.service_runner_iteration_state import ServiceRunnerIterationStateMixin
from loopora.service_runner_step_artifacts import ServiceRunnerStepArtifactsMixin
from loopora.service_runner_step_commit import ServiceRunnerStepCommitMixin
from loopora.service_runner_step_execution import ServiceRunnerStepExecutionMixin
from loopora.service_run_finalization import TerminalRunFinalizationRequest
from loopora.runner_run_requests import RunnerExhaustionRequest
from loopora.runner_support_requests import RunnerSummaryRequest

logger = get_logger(__name__)


class ServiceRunnerExecutionMixin(
    ServiceRunnerControlExecutionMixin,
    ServiceRunnerContextPreparationMixin,
    ServiceRunnerIterationStateMixin,
    ServiceRunnerIterationProgressMixin,
    ServiceRunnerStepArtifactsMixin,
    ServiceRunnerFailureHandlingMixin,
    ServiceRunnerStepCommitMixin,
    ServiceRunnerStepExecutionMixin,
):
    def _execute_preclaimed_run(self, run_id: str) -> dict:
        try:
            return self.execute_run(run_id, _active_already_claimed=True)
        except Exception:
            self._mark_run_inactive(run_id)
            self._threads.pop(run_id, None)
            raise

    def execute_run(self, run_id: str, *, _active_already_claimed: bool = False) -> dict:
        run = self.repository.get_run(run_id)
        if not run:
            raise LooporaNotFoundError(f"unknown run: {run_id}")

        if not _active_already_claimed and not self._try_mark_run_active(run_id):
            raise LooporaConflictError(f"run {run_id} is already executing in this process")

        log_event(
            logger,
            logging.INFO,
            "service.run.execution.started",
            "Starting runner run execution",
            **self._run_log_context(
                run,
                completion_mode=run.get("completion_mode"),
                max_iters=run.get("max_iters"),
            ),
        )
        run_dir = Path(run["runs_dir"])
        try:
            strategy_source = self._strategy_source_snapshot_from_record(run)
        except Exception:
            self._mark_run_inactive(run_id)
            self._threads.pop(run_id, None)
            raise

        if not strategy_source:
            return self._fail_run_without_strategy_snapshot(run_id, run, run_dir)

        result = self._execute_runner_run(run_id, run, run_dir, strategy_source)
        return self._execution_result_after_cleanup(run_id, result)

    def _execution_result_after_cleanup(self, run_id: str, result: dict) -> dict:
        if str(result.get("status") or "") not in {"succeeded", "failed", "stopped"}:
            return result
        try:
            return self.get_run(run_id)
        except Exception:  # noqa: BLE001 - execution already produced a terminal result; preserve it if refresh fails.
            return result

    def _fail_run_without_strategy_snapshot(self, run_id: str, run: dict, run_dir: Path) -> dict:
        error_text = "Run has no strategy snapshot; legacy execution runtime has been removed."
        summary = f"# Loopora Run Summary\n\nExecution failed before starting.\n\nReason: `{error_text}`.\n"
        try:
            failed = self._finalize_terminal_run(
                TerminalRunFinalizationRequest(
                    run_id=run_id,
                    run_dir=run_dir,
                    status="failed",
                    summary=summary,
                    error_message=error_text,
                    final_reason="missing_strategy_snapshot",
                )
            )
            self._append_run_aborted_event(
                run_id,
                role=None,
                attempts=0,
                degraded=False,
                error_text=error_text,
            )
            self.append_run_event(
                run_id,
                "run_finished",
                self._run_finished_event_payload(failed, status="failed", reason="missing_strategy_snapshot"),
            )
            return failed
        finally:
            self._cleanup_run_execution(run_id, run, phase="runner")

    def _run_runner_iteration(
        self,
        context: RunnerRunContext,
        progress: RunnerRunProgress,
        iter_id: int,
    ) -> dict | None:
        progress.last_iter_id = iter_id
        self._ensure_not_stopped(context.run_id)
        self.repository.update_run(context.run_id, current_iter=iter_id)
        RepositoryRunEngine(self.repository).start_iteration(
            RunEngineStartIterationRequest(
                run_id=context.run_id,
                iteration=iter_id,
                actor=headless_runner_actor(),
                step_count=len(context.strategy_steps),
            )
        )
        iteration = self._build_runner_iteration_state(context, progress, iter_id)
        self._log_runner_iteration_started(context, iteration)
        finish_result = self._run_runner_iteration_steps(context, iteration)
        if finish_result is not None:
            return finish_result
        self._run_strategy_iteration_controls(context, iteration)
        self._checkpoint_runner_iteration_progress(context, progress, iteration)
        return None

    def _handle_runner_execution_exception(
        self,
        run_id: str,
        run: dict,
        run_dir: Path,
        exc: BaseException,
    ) -> dict:
        if isinstance(exc, (StopRequestedError, ExecutionStopped)):
            return self._handle_runner_stop(run_id, run, run_dir)
        if isinstance(exc, RoleExecutionError):
            return self._handle_runner_role_execution_error(run_id, run, run_dir, exc)
        if isinstance(exc, WorkspaceSafetyError):
            return self._handle_runner_workspace_safety_error(run_id, run, run_dir, exc)
        if isinstance(exc, Exception):
            return self._handle_runner_unexpected_error(run_id, run, run_dir, exc)
        raise exc

    def _execute_runner_run(self, run_id: str, run: dict, run_dir: Path, strategy_source: dict) -> dict:
        try:
            self.repository.update_run(run_id, runner_pid=os.getpid())
            self._wait_for_slot(run_id)
            run = self.repository.get_run(run_id)
            if not run:
                raise LooporaNotFoundError(f"unknown run after queue wait: {run_id}")
            if run["status"] == "stopped":
                return self._hydrate_run_files(run)

            context = self._prepare_runner_run_context(run_id, run, run_dir, strategy_source)
            progress = self._new_runner_run_progress(context)
            iteration_interval_seconds = float(context.run.get("iteration_interval_seconds", 0.0) or 0.0)
            iteration_source = itertools.count() if context.run["max_iters"] == 0 else range(context.run["max_iters"])

            for iter_id in iteration_source:
                finish_result = self._run_runner_iteration(context, progress, iter_id)
                if finish_result is not None:
                    return finish_result
                if iteration_interval_seconds > 0 and (context.run["max_iters"] == 0 or iter_id < context.run["max_iters"] - 1):
                    self._pause_between_iterations(context.run_id, iteration_interval_seconds, iter_id)

            summary = self._build_runner_summary(
                RunnerSummaryRequest(
                    run=context.run,
                    strategy_source=context.strategy_source,
                    compiled_spec=context.compiled_spec,
                    iter_id=progress.last_iter_id,
                    step_results=progress.last_step_results,
                    stagnation=progress.stagnation,
                    exhausted=True,
                    previous_composite=None,
                )
            )
            return self._handle_runner_exhaustion(
                RunnerExhaustionRequest(
                    run_id=context.run_id,
                    run=context.run,
                    run_dir=context.run_dir,
                    completion_mode=context.completion_mode,
                    last_iter_id=progress.last_iter_id,
                    summary=summary,
                )
            )
        except (StopRequestedError, ExecutionStopped, RoleExecutionError, WorkspaceSafetyError) as exc:
            return self._handle_runner_execution_exception(run_id, run, run_dir, exc)
        except Exception as exc:  # noqa: BLE001 - runner crash boundary must persist failed run state.
            return self._handle_runner_execution_exception(run_id, run, run_dir, exc)
        finally:
            self._cleanup_run_execution(run_id, run, phase="runner")
