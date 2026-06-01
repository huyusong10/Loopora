from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import logging

from loopora.diagnostics import get_logger, log_event
from loopora.engine.runner_context import (
    RunnerIterationState,
    RunnerParallelGroupClaimPlan,
    RunnerRunContext,
)
from loopora.engine.runner_runtime import RunnerStepRunRequest
from loopora.service_types import RoleExecutionError

logger = get_logger(__name__)


def runner_role_error_signal(exc: Exception) -> str:
    return "role_timeout" if "timeout" in str(exc).lower() else "step_failed"


class ServiceRunnerParallelExecutionMixin:
    def _run_runner_parallel_group(
        self,
        context: RunnerRunContext,
        iteration: RunnerIterationState,
        group_plan: RunnerParallelGroupClaimPlan,
    ) -> dict | None:
        group_snapshot = iteration.snapshot()
        self.append_run_event(
            context.run_id,
            "parallel_group_started",
            {
                "iter": iteration.iter_id,
                "parallel_group": group_plan.parallel_group,
                "step_orders": [plan.step_order for plan in group_plan.steps],
                "step_ids": [plan.step["id"] for plan in group_plan.steps],
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
                parallel_group=group_plan.parallel_group,
                step_count=len(group_plan.steps),
                group_start=group_plan.group_start,
            ),
        )
        with ThreadPoolExecutor(max_workers=len(group_plan.steps)) as pool:
            futures = [
                pool.submit(
                    self._run_runner_step_once,
                    RunnerStepRunRequest(
                        context=context,
                        iteration=iteration,
                        step_order=plan.step_order,
                        step=plan.step,
                        state_snapshot=group_snapshot,
                        claim_request=plan.claim_request,
                    ),
                )
                for plan in group_plan.steps
            ]
            parallel_results = []
            for plan, future in zip(group_plan.steps, futures, strict=False):
                try:
                    parallel_results.append(future.result())
                except RoleExecutionError as exc:
                    self._run_strategy_controls_for_signal(
                        context,
                        iteration,
                        runner_role_error_signal(exc),
                        {
                            "reason": f"parallel step {plan.step.get('id')} failed",
                            "failed_step_id": plan.step.get("id"),
                            "error": str(exc),
                            "evidence_refs": [],
                        },
                        group_snapshot,
                    )
                    raise
        for result in sorted(parallel_results, key=lambda item: int(item["step_order"])):
            finish_result = self.submit_runner_step_result(context, iteration, result)
            if finish_result is not None:
                return finish_result
        self.append_run_event(
            context.run_id,
            "parallel_group_finished",
            {
                "iter": iteration.iter_id,
                "parallel_group": group_plan.parallel_group,
                "step_orders": [plan.step_order for plan in group_plan.steps],
                "step_ids": [plan.step["id"] for plan in group_plan.steps],
            },
        )
        return None
