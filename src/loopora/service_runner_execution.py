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
from loopora.service_runner_failure_handling import ServiceRunnerFailureHandlingMixin
from loopora.service_runner_iteration_progress import ServiceRunnerIterationProgressMixin
from loopora.service_runner_iteration_state import ServiceRunnerIterationStateMixin
from loopora.service_runner_step_artifacts import ServiceRunnerStepArtifactsMixin
from loopora.service_runner_step_commit import ServiceRunnerStepCommitMixin
from loopora.service_runner_step_execution import ServiceRunnerStepExecutionMixin
from loopora.service_run_finalization import TerminalRunFinalizationRequest
from loopora.runner_run_requests import RunnerExhaustionRequest
from loopora.runner_summary_projection import RunnerSummaryRequest

import time

from loopora.context_flow import evidence_entry_id

from loopora.engine.runner_context import RunnerIterationState

from loopora.engine.runner_runtime import RunnerStepRunRequest

from loopora.strategy_controls import (
    StrategyControlPayloadRequest,
    StrategyControlStepRequest,
    build_strategy_control_payload,
    build_strategy_control_step,
    matching_strategy_controls,
    strategy_control_after_seconds,
    strategy_iteration_control_triggers,
)






from loopora.recovery import RetryConfig

from loopora.service_types import normalize_completion_mode

from loopora.strategy_source import normalize_strategy_source

from loopora.utils import read_json

class ServiceRunnerContextPreparationMixin:
    def _prepare_runner_run_context(
        self,
        run_id: str,
        run: dict,
        run_dir: Path,
        strategy_source: dict,
    ) -> RunnerRunContext:
        executor = self.executor_factory()
        compiled_spec = run["compiled_spec_json"]
        retry_config = RetryConfig(max_retries=run["max_role_retries"])
        prompt_files = self._read_prompt_files_for_run(run)
        layout = self._run_artifact_layout(run_dir)
        strategy_source = normalize_strategy_source(strategy_source)
        role_by_id = {role["id"]: role for role in strategy_source.get("roles", [])}
        strategy_steps = list(strategy_source.get("steps", []))
        strategy_controls = list(strategy_source.get("controls", []))
        completion_mode = normalize_completion_mode(run.get("completion_mode", "gatekeeper"))

        self.append_run_event(run_id, "run_started", {"status": "running"})
        self._write_summary(run_id, "running", "Resolving checks for this run.")
        compiled_spec = self._resolve_run_checks(run, executor, compiled_spec, run_dir, retry_config)
        run_contract = read_json(layout.run_contract_path)
        self._write_summary(run_id, "running", "Waiting for the first runner iteration to complete.")
        log_event(
            logger,
            logging.INFO,
            "service.runner.execution.started",
            "Starting runner run execution",
            **self._run_log_context(
                run,
                completion_mode=completion_mode,
                step_count=len(strategy_steps),
                role_count=len(role_by_id),
            ),
        )
        return RunnerRunContext(
            run_id=run_id,
            run=run,
            run_dir=run_dir,
            strategy_source=strategy_source,
            executor=executor,
            compiled_spec=compiled_spec,
            retry_config=retry_config,
            prompt_files=prompt_files,
            layout=layout,
            run_contract=run_contract,
            strategy_steps=strategy_steps,
            strategy_controls=strategy_controls,
            control_fire_counts={},
            runner_started_at=time.monotonic(),
            role_by_id=role_by_id,
            completion_mode=completion_mode,
        )

class ServiceRunnerControlExecutionMixin:
    def _run_strategy_controls_for_signal(
        self,
        context: RunnerRunContext,
        iteration: RunnerIterationState,
        signal: str,
        trigger: dict[str, object],
        snapshot: dict[str, object],
    ) -> None:
        matching_controls = matching_strategy_controls(context.strategy_controls, signal)
        if not matching_controls:
            return
        for control in matching_controls:
            control_id = str(control.get("id") or "").strip()
            max_fires = int(control.get("max_fires_per_run", 1) or 1)
            fired = int(context.control_fire_counts.get(control_id, 0) or 0)
            role_id = str((control.get("call") or {}).get("role_id") or "").strip()
            elapsed_seconds = time.monotonic() - context.runner_started_at
            base_payload = build_strategy_control_payload(
                StrategyControlPayloadRequest(
                    control=control,
                    iter_id=iteration.iter_id,
                    signal=signal,
                    trigger=trigger,
                    elapsed_seconds=elapsed_seconds,
                )
            )
            if fired >= max_fires:
                self.append_run_event(
                    context.run_id,
                    "control_skipped",
                    {**base_payload, "skip_reason": "max_fires_per_run"},
                )
                continue
            if elapsed_seconds < strategy_control_after_seconds(base_payload["after"]):
                self.append_run_event(
                    context.run_id,
                    "control_skipped",
                    {**base_payload, "skip_reason": "after_not_elapsed"},
                )
                continue
            role = context.role_by_id.get(role_id)
            if not role:
                self.append_run_event(
                    context.run_id,
                    "control_failed",
                    {**base_payload, "error": "control role not found"},
                )
                continue
            context.control_fire_counts[control_id] = fired + 1
            existing_control_count = sum(1 for item in iteration.step_results if item["step"].get("control_id"))
            control_step, control_order = build_strategy_control_step(
                StrategyControlStepRequest(
                    control=control,
                    payload=base_payload,
                    role=role,
                    strategy_step_count=len(context.strategy_steps),
                    existing_control_count=existing_control_count,
                )
            )
            self.append_run_event(context.run_id, "control_triggered", base_payload, role=role_id)
            try:
                result = self._run_runner_step_once(
                    RunnerStepRunRequest(
                        context=context,
                        iteration=iteration,
                        step_order=control_order,
                        step=control_step,
                        state_snapshot=snapshot,
                        is_control=True,
                    )
                )
                finish_result = self.submit_runner_step_result(context, iteration, result)
                evidence_id = evidence_entry_id(iteration.iter_id, control_order, control_step["id"])
                self.append_run_event(
                    context.run_id,
                    "control_completed",
                    {
                        **base_payload,
                        "status": result.get("normalized_output", {}).get("status")
                        or result.get("normalized_output", {}).get("mode")
                        or "completed",
                        "evidence_refs": [evidence_id],
                    },
                    role=role_id,
                )
                if finish_result is not None:
                    self.append_run_event(
                        context.run_id,
                        "control_skipped",
                        {**base_payload, "skip_reason": "control_cannot_finish_run"},
                        role=role_id,
                    )
            except Exception as exc:
                self.append_run_event(
                    context.run_id,
                    "control_failed",
                    {**base_payload, "error": str(exc)},
                    role=role_id,
                )
                if str(control.get("mode") or "") == "blocking":
                    raise

    def _run_strategy_iteration_controls(
        self,
        context: RunnerRunContext,
        iteration: RunnerIterationState,
    ) -> None:
        for trigger in strategy_iteration_control_triggers(iteration.current_gatekeeper_result, iteration.stagnation):
            self._run_strategy_controls_for_signal(
                context,
                iteration,
                trigger.signal,
                trigger.trigger,
                iteration.snapshot(),
            )

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
