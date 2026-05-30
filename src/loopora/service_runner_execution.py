from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import itertools
import logging
import os
import time
from pathlib import Path

from loopora.context_flow import evidence_entry_id
from loopora.diagnostics import get_logger, log_event
from loopora.engine import (
    RepositoryRunEngine,
    RunEngineStartIterationRequest,
    RunEngineClaimRunnerStepRequest,
    RunnerStepSelectionRequest,
    select_next_runner_step,
)
from loopora.engine.runner_runtime import (
    RunnerRunProgress,
    RunnerStepRunRequest,
)
from loopora.engine.runner_context import (
    RunnerIterationState,
    RunnerRunContext,
    evidence_context_with_canonical_items,
)
from loopora.executor import ExecutionStopped
from loopora.recovery import RetryConfig
from loopora.runners import headless_runner_actor
from loopora.run_artifacts import read_stagnation_state
from loopora.service_types import (
    LooporaConflictError,
    LooporaNotFoundError,
    RoleExecutionError,
    StopRequested,
    WorkspaceSafetyError,
    normalize_completion_mode,
)
from loopora.step_instruction_context import step_instruction_context_legacy_fields
from loopora.structured_booleans import structured_bool_is_true
from loopora.service_runner_failure_handling import ServiceRunnerFailureHandlingMixin
from loopora.service_runner_iteration_state import ServiceRunnerIterationStateMixin
from loopora.service_runner_step_artifacts import ServiceRunnerStepArtifactsMixin
from loopora.service_runner_step_commit import ServiceRunnerStepCommitMixin
from loopora.service_run_finalization import TerminalRunFinalizationRequest
from loopora.strategy_controls import (
    StrategyControlPayloadRequest,
    StrategyControlStepRequest,
    build_strategy_control_payload,
    build_strategy_control_step,
    matching_strategy_controls,
    strategy_control_after_seconds,
    strategy_iteration_control_triggers,
)
from loopora.strategy_source import normalize_strategy_source
from loopora.runner_run_requests import RunnerExhaustionRequest, RunnerIterationCheckpointRequest
from loopora.runner_support_requests import RunnerSummaryRequest, StepOutputNormalizationRequest
from loopora.runner_step_runtime import RunnerStepRuntimeRequest
from loopora.utils import read_json
from loopora.structured_numbers import structured_non_negative_int

logger = get_logger(__name__)


def _runner_role_error_signal(exc: Exception) -> str:
    return "role_timeout" if "timeout" in str(exc).lower() else "step_failed"


class ServiceRunnerExecutionMixin(
    ServiceRunnerIterationStateMixin,
    ServiceRunnerStepArtifactsMixin,
    ServiceRunnerFailureHandlingMixin,
    ServiceRunnerStepCommitMixin,
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
            strategy_source = self._normalized_strategy_source_from_record(run) if run.get("workflow_json") else {}
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

    def _run_runner_step_once(
        self,
        request: RunnerStepRunRequest,
    ) -> dict:
        context = request.context
        iteration = request.iteration
        step_order = request.step_order
        step = request.step
        state_snapshot = request.state_snapshot
        role = context.role_by_id[step["role_id"]]
        runtime_role = self._runtime_role_key(role)

        execution_settings = self._resolve_role_execution_settings(context.run, step, role)
        actor = headless_runner_actor()
        RepositoryRunEngine(self.repository).claim_runner_step(
            RunEngineClaimRunnerStepRequest(
                run_id=context.run_id,
                contract_ref=str(context.layout.run_contract_path),
                compiled_spec=context.compiled_spec,
                iteration=iteration.iter_id,
                step=step,
                role=role,
                pending_actor=actor,
            )
        )
        log_event(
            logger,
            logging.INFO,
            "service.runner.step.started",
            "Starting runner step",
            **self._run_log_context(
                context.run,
                iter=iteration.iter_id,
                step_id=step["id"],
                role=runtime_role,
                archetype=role["archetype"],
                executor_kind=execution_settings["executor_kind"],
                executor_mode=execution_settings["executor_mode"],
                model=execution_settings["model"],
                parallel_group=step.get("parallel_group"),
            ),
        )
        step_started_at = time.perf_counter()
        output, step_instruction_context, session_ref = self._run_runner_step(
            RunnerStepRuntimeRequest(
                executor=context.executor,
                run=context.run,
                compiled_spec=context.compiled_spec,
                layout=context.layout,
                iter_id=iteration.iter_id,
                step=step,
                step_order=step_order,
                role=role,
                prompt_files=context.prompt_files,
                execution_settings=execution_settings,
                run_contract=context.run_contract,
                current_outputs_by_step=dict(state_snapshot["current_outputs_by_step"]),
                current_outputs_by_role=dict(state_snapshot["current_outputs_by_role"]),
                current_outputs_by_archetype=dict(state_snapshot["current_outputs_by_archetype"]),
                current_handoffs=list(state_snapshot["current_handoffs"]),
                previous_outputs_by_step=iteration.previous_outputs_by_step,
                previous_outputs_by_role=iteration.previous_outputs_by_role,
                previous_outputs_by_archetype=iteration.previous_outputs_by_archetype,
                previous_handoffs_by_step=iteration.previous_handoffs_by_step,
                previous_handoffs_by_role=iteration.previous_handoffs_by_role,
                previous_iteration_summary=iteration.previous_iteration_summary,
                previous_session_refs_by_step=iteration.previous_session_refs_by_step,
                previous_composite=iteration.previous_composite,
                stagnation_mode=iteration.stagnation.get("stagnation_mode", "none"),
                evidence_progress_mode=iteration.stagnation.get("evidence_progress_mode", "none"),
                covered_check_count=structured_non_negative_int(iteration.stagnation.get("latest_covered_check_count")),
                missing_check_count=structured_non_negative_int(iteration.stagnation.get("latest_missing_check_count")),
                consecutive_no_required_coverage_delta=structured_non_negative_int(
                    iteration.stagnation.get("consecutive_no_required_coverage_delta")
                ),
                retry_config=context.retry_config,
            )
        )
        normalized_output = self._normalize_step_output(
            StepOutputNormalizationRequest(
                archetype=role["archetype"],
                output=output,
                compiled_spec=context.compiled_spec,
                inspector_output=dict(state_snapshot["current_outputs_by_archetype"]).get("inspector"),
                evidence_context=evidence_context_with_canonical_items(step_instruction_context, context.layout),
                current_evidence_id=evidence_entry_id(iteration.iter_id, step_order, step["id"]),
            )
        )
        return {
            "skipped": False,
            "step_order": step_order,
            "step": step,
            "role": role,
            "runtime_role": runtime_role,
            "execution_settings": execution_settings,
            "normalized_output": normalized_output,
            **step_instruction_context_legacy_fields(step_instruction_context),
            "session_ref": session_ref,
            "actor_ref": actor.to_dict(),
            "duration_ms": int((time.perf_counter() - step_started_at) * 1000),
        }

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
                finish_result = self.commit_runner_step_result(context, iteration, result)
                evidence_id = evidence_entry_id(iteration.iter_id, control_order, control_step["id"])
                self.append_run_event(
                    context.run_id,
                    "control_completed",
                    {
                        **base_payload,
                        "status": result.get("normalized_output", {}).get("status") or result.get("normalized_output", {}).get("mode") or "completed",
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

    def _run_runner_linear_step(
        self,
        context: RunnerRunContext,
        iteration: RunnerIterationState,
        step_order: int,
        step: dict,
    ) -> dict | None:
        try:
            step_result = self._run_runner_step_once(
                RunnerStepRunRequest(
                    context=context,
                    iteration=iteration,
                    step_order=step_order,
                    step=step,
                    state_snapshot=iteration.snapshot(),
                )
            )
        except RoleExecutionError as exc:
            self._run_strategy_controls_for_signal(
                context,
                iteration,
                _runner_role_error_signal(exc),
                {
                    "reason": f"step {step.get('id')} failed",
                    "failed_step_id": step.get("id"),
                    "error": str(exc),
                    "evidence_refs": [],
                },
                iteration.snapshot(),
            )
            raise
        return self.commit_runner_step_result(context, iteration, step_result)

    def _collect_runner_parallel_group(
        self,
        context: RunnerRunContext,
        group_start: int,
        parallel_group: str,
    ) -> tuple[int, list[tuple[int, dict]]]:
        step_index = group_start
        group_items: list[tuple[int, dict]] = []
        while step_index < len(context.strategy_steps) and str(context.strategy_steps[step_index].get("parallel_group") or "").strip() == parallel_group:
            group_items.append((step_index, context.strategy_steps[step_index]))
            step_index += 1
        return step_index, group_items

    def _run_runner_parallel_group(
        self,
        context: RunnerRunContext,
        iteration: RunnerIterationState,
        parallel_group: str,
        group_start: int,
        group_items: list[tuple[int, dict]],
    ) -> dict | None:
        group_snapshot = iteration.snapshot()
        self.append_run_event(
            context.run_id,
            "parallel_group_started",
            {
                "iter": iteration.iter_id,
                "parallel_group": parallel_group,
                "step_orders": [order for order, _step in group_items],
                "step_ids": [_step["id"] for _order, _step in group_items],
            },
        )
        log_event(
            logger,
            logging.INFO,
            "service.runner.parallel_group.started",
            "Starting runner parallel group",
            **self._run_log_context(
                context.run,
                iter=iteration.iter_id,
                parallel_group=parallel_group,
                step_count=len(group_items),
                group_start=group_start,
            ),
        )
        with ThreadPoolExecutor(max_workers=len(group_items)) as pool:
            futures = [
                pool.submit(
                    self._run_runner_step_once,
                    RunnerStepRunRequest(
                        context=context,
                        iteration=iteration,
                        step_order=order,
                        step=group_step,
                        state_snapshot=group_snapshot,
                    ),
                )
                for order, group_step in group_items
            ]
            parallel_results = []
            for (_, group_step), future in zip(group_items, futures, strict=False):
                try:
                    parallel_results.append(future.result())
                except RoleExecutionError as exc:
                    self._run_strategy_controls_for_signal(
                        context,
                        iteration,
                        _runner_role_error_signal(exc),
                        {
                            "reason": f"parallel step {group_step.get('id')} failed",
                            "failed_step_id": group_step.get("id"),
                            "error": str(exc),
                            "evidence_refs": [],
                        },
                        group_snapshot,
                    )
                    raise
        for result in sorted(parallel_results, key=lambda item: int(item["step_order"])):
            finish_result = self.commit_runner_step_result(context, iteration, result)
            if finish_result is not None:
                return finish_result
        self.append_run_event(
            context.run_id,
            "parallel_group_finished",
            {
                "iter": iteration.iter_id,
                "parallel_group": parallel_group,
                "step_orders": [order for order, _step in group_items],
                "step_ids": [_step["id"] for _order, _step in group_items],
            },
        )
        return None

    def _run_runner_iteration_steps(
        self,
        context: RunnerRunContext,
        iteration: RunnerIterationState,
    ) -> dict | None:
        step_index = 0
        while step_index < len(context.strategy_steps):
            selection = select_next_runner_step(RunnerStepSelectionRequest(context.strategy_steps, step_index))
            if selection is None:
                return None
            step = dict(selection.step)
            parallel_group = selection.parallel_group
            if not parallel_group:
                finish_result = self._run_runner_linear_step(context, iteration, selection.step_order, step)
                if finish_result is not None:
                    return finish_result
                step_index = selection.step_order + 1
                continue

            group_start = selection.step_order
            step_index, group_items = self._collect_runner_parallel_group(context, group_start, parallel_group)
            finish_result = self._run_runner_parallel_group(
                context,
                iteration,
                parallel_group,
                group_start,
                group_items,
            )
            if finish_result is not None:
                return finish_result
        return None

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

    def _new_runner_run_progress(self, context: RunnerRunContext) -> RunnerRunProgress:
        return RunnerRunProgress(stagnation=read_stagnation_state(context.layout.timeline_stagnation_path))

    def _build_runner_iteration_state(
        self,
        context: RunnerRunContext,
        progress: RunnerRunProgress,
        iter_id: int,
    ) -> RunnerIterationState:
        previous_composite = context.last_gatekeeper_result.get("composite_score") if isinstance(context.last_gatekeeper_result, dict) else None
        return RunnerIterationState(
            iter_id=iter_id,
            previous_composite=previous_composite,
            stagnation=progress.stagnation,
            previous_outputs_by_step=progress.previous_outputs_by_step,
            previous_outputs_by_role=progress.previous_outputs_by_role,
            previous_outputs_by_archetype=progress.previous_outputs_by_archetype,
            previous_handoffs_by_step=progress.previous_handoffs_by_step,
            previous_handoffs_by_role=progress.previous_handoffs_by_role,
            previous_iteration_summary=progress.previous_iteration_summary,
            previous_session_refs_by_step=progress.previous_session_refs_by_step,
        )

    def _log_runner_iteration_started(
        self,
        context: RunnerRunContext,
        iteration: RunnerIterationState,
    ) -> None:
        log_event(
            logger,
            logging.INFO,
            "service.runner.iteration.started",
            "Starting runner iteration",
            **self._run_log_context(
                context.run,
                iter=iteration.iter_id,
                step_count=len(context.strategy_steps),
                previous_composite_score=iteration.previous_composite,
                stagnation_mode=iteration.stagnation.get("stagnation_mode", "none"),
            ),
        )

    def _checkpoint_runner_iteration_progress(
        self,
        context: RunnerRunContext,
        progress: RunnerRunProgress,
        iteration: RunnerIterationState,
    ) -> None:
        (
            progress.previous_outputs_by_step,
            progress.previous_outputs_by_role,
            progress.previous_outputs_by_archetype,
            progress.previous_handoffs_by_step,
            progress.previous_handoffs_by_role,
            _previous_handoffs_by_archetype,
            progress.previous_iteration_summary,
        ) = self._checkpoint_runner_iteration_state(
            RunnerIterationCheckpointRequest(
                layout=context.layout,
                iter_id=iteration.iter_id,
                step_results=iteration.step_results,
                current_outputs_by_step=iteration.current_outputs_by_step,
                current_outputs_by_role=iteration.current_outputs_by_role,
                current_outputs_by_archetype=iteration.current_outputs_by_archetype,
                current_session_refs_by_step=iteration.current_session_refs_by_step,
                stagnation=iteration.stagnation,
                previous_composite=iteration.previous_composite,
                run_id=context.run_id,
            )
        )
        progress.previous_session_refs_by_step = dict(iteration.current_session_refs_by_step)
        progress.last_step_results = iteration.step_results
        progress.stagnation = iteration.stagnation
        summary = self._build_runner_summary(
            RunnerSummaryRequest(
                run=context.run,
                strategy_source=context.strategy_source,
                compiled_spec=context.compiled_spec,
                iter_id=iteration.iter_id,
                step_results=iteration.step_results,
                stagnation=progress.stagnation,
                exhausted=False,
                previous_composite=iteration.previous_composite,
            )
        )
        self._write_summary(context.run_id, "running", summary)
        log_event(
            logger,
            logging.INFO,
            "service.runner.iteration.completed",
            "Completed runner iteration",
            **self._run_log_context(
                context.run,
                iter=iteration.iter_id,
                executed_step_count=len(iteration.step_results),
                stagnation_mode=progress.stagnation.get("stagnation_mode", "none"),
                gatekeeper_passed=structured_bool_is_true(
                    iteration.current_gatekeeper_result.get("passed") if iteration.current_gatekeeper_result else None
                ),
                guide_used=iteration.current_guide_result is not None,
            ),
        )

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
        if isinstance(exc, (StopRequested, ExecutionStopped)):
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
        except (StopRequested, ExecutionStopped, RoleExecutionError, WorkspaceSafetyError) as exc:
            return self._handle_runner_execution_exception(run_id, run, run_dir, exc)
        except Exception as exc:  # noqa: BLE001 - runner crash boundary must persist failed run state.
            return self._handle_runner_execution_exception(run_id, run, run_dir, exc)
        finally:
            self._cleanup_run_execution(run_id, run, phase="runner")
