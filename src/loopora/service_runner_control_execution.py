from __future__ import annotations

import time

from loopora.context_step_results import evidence_entry_id
from loopora.engine.runner_context import RunnerIterationState, RunnerRunContext
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
