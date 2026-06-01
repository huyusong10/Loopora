from __future__ import annotations

import logging

from loopora.diagnostics import get_logger, log_event
from loopora.engine.runner_context import RunnerIterationState, RunnerRunContext
from loopora.engine.runner_runtime import RunnerRunProgress
from loopora.run_artifacts import read_stagnation_state
from loopora.runner_run_requests import RunnerIterationCheckpointRequest
from loopora.runner_support_requests import RunnerSummaryRequest
from loopora.structured_booleans import structured_bool_is_true

logger = get_logger(__name__)


class ServiceRunnerIterationProgressMixin:
    def _new_runner_run_progress(self, context: RunnerRunContext) -> RunnerRunProgress:
        return RunnerRunProgress(stagnation=read_stagnation_state(context.layout.timeline_stagnation_path))

    def _build_runner_iteration_state(
        self,
        context: RunnerRunContext,
        progress: RunnerRunProgress,
        iter_id: int,
    ) -> RunnerIterationState:
        previous_composite = (
            context.last_gatekeeper_result.get("composite_score") if isinstance(context.last_gatekeeper_result, dict) else None
        )
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
