from __future__ import annotations

import logging
import time

from loopora.context_flow import evidence_entry_id
from loopora.diagnostics import get_logger, log_event
from loopora.engine import RepositoryRunEngine
from loopora.engine.runner_context import (
    RunnerIterationState,
    RunnerRunContext,
    evidence_context_with_canonical_items,
    runner_parallel_group_claim_plan,
    runner_step_claim_plan,
    runner_step_claim_request,
)
from loopora.engine.runner_runtime import RunnerStepRunRequest
from loopora.runner_step_runtime_requests import (
    RunnerStepRuntimeRequestBuildRequest,
    build_runner_step_runtime_request,
    runner_step_runtime_input_snapshot_from_mapping,
)
from loopora.runner_summary_projection import StepOutputNormalizationRequest
from loopora.runners import headless_runner_actor
from loopora.service_runner_parallel_execution import ServiceRunnerParallelExecutionMixin, runner_role_error_signal
from loopora.service_types import RoleExecutionError
from loopora.step_instruction_context import STEP_INSTRUCTION_CONTEXT_KEY

logger = get_logger(__name__)


class ServiceRunnerStepExecutionMixin(ServiceRunnerParallelExecutionMixin):
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
        claim_request = request.claim_request or runner_step_claim_request(
            context,
            iteration,
            step=step,
            role=role,
            pending_actor=actor,
        )
        RepositoryRunEngine(self.repository).claim_runner_step(claim_request)
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
            build_runner_step_runtime_request(
                RunnerStepRuntimeRequestBuildRequest(
                    context=context,
                    iteration=iteration,
                    run=context.run,
                    step=step,
                    step_order=step_order,
                    role=role,
                    execution_settings=execution_settings,
                    input_snapshot=runner_step_runtime_input_snapshot_from_mapping(state_snapshot),
                )
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
            STEP_INSTRUCTION_CONTEXT_KEY: step_instruction_context,
            "session_ref": session_ref,
            "actor_ref": actor.to_dict(),
            "duration_ms": int((time.perf_counter() - step_started_at) * 1000),
        }

    def _run_runner_linear_step(
        self,
        context: RunnerRunContext,
        iteration: RunnerIterationState,
        step_order: int,
        step: dict,
        claim_request: object | None = None,
    ) -> dict | None:
        try:
            step_result = self._run_runner_step_once(
                RunnerStepRunRequest(
                    context=context,
                    iteration=iteration,
                    step_order=step_order,
                    step=step,
                    state_snapshot=iteration.snapshot(),
                    claim_request=claim_request,
                )
            )
        except RoleExecutionError as exc:
            self._run_strategy_controls_for_signal(
                context,
                iteration,
                runner_role_error_signal(exc),
                {
                    "reason": f"step {step.get('id')} failed",
                    "failed_step_id": step.get("id"),
                    "error": str(exc),
                    "evidence_refs": [],
                },
                iteration.snapshot(),
            )
            raise
        return self.submit_runner_step_result(context, iteration, step_result)

    def _run_runner_iteration_steps(
        self,
        context: RunnerRunContext,
        iteration: RunnerIterationState,
    ) -> dict | None:
        step_index = 0
        run_engine = RepositoryRunEngine(self.repository)
        actor = headless_runner_actor()
        while step_index < len(context.strategy_steps):
            plan = runner_step_claim_plan(
                run_engine,
                context,
                iteration,
                pending_actor=actor,
                fallback_step_index=step_index,
            )
            if plan is None:
                return None
            step = dict(plan.step)
            parallel_group = plan.parallel_group
            if not parallel_group:
                finish_result = self._run_runner_linear_step(
                    context,
                    iteration,
                    plan.step_order,
                    step,
                    claim_request=plan.claim_request,
                )
                if finish_result is not None:
                    return finish_result
                step_index = plan.step_order + 1
                continue

            group_plan = runner_parallel_group_claim_plan(
                context,
                iteration,
                first_plan=plan,
                pending_actor=actor,
            )
            step_index = group_plan.next_step_index
            finish_result = self._run_runner_parallel_group(
                context,
                iteration,
                group_plan,
            )
            if finish_result is not None:
                return finish_result
        return None
