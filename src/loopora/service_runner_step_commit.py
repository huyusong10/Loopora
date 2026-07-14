from __future__ import annotations

from loopora.engine import (
    RepositoryRunEngine,
    RunEngineRecordStepEvidenceRequest,
    RunEngineSubmitStepRequest,
    RunnerStepResultRequest,
    runner_step_result,
)
from loopora.kernel import ActorRef
from loopora.context_step_results import StepResultContext, build_step_handoff
from loopora.service_runner_step_artifacts import (
    RunnerStepCompletionLogRequest,
    RunnerStepResultEntryRequest,
    RunnerStepWriteRequest,
)
from loopora.service_runner_iteration_state import (
    GatekeeperIterationRecordRequest,
    RunnerGatekeeperSuccessRequest,
)
from loopora.runtime_task_language import runtime_task_language
from loopora.step_instruction_context import required_step_instruction_context_from_mapping
from loopora.structured_numbers import coerced_non_negative_int


class ServiceRunnerStepCommitMixin:
    def require_runner_step_result_submittable(
        self,
        context,
        iteration,
        result: dict,
    ) -> None:
        if result.get("skipped"):
            return
        run_engine = RepositoryRunEngine(self.repository)
        run_engine.validate_step_submission(
            RunEngineSubmitStepRequest(
                result=self._runner_step_result_for_engine(
                    context,
                    iteration,
                    result,
                    handoff=self._runner_step_handoff_preview(context, iteration, result),
                )
            )
        )

    def submit_runner_step_result(
        self,
        context,
        iteration,
        result: dict,
    ) -> dict | None:
        if result.get("skipped"):
            return None
        step = result["step"]
        is_control_step = bool(step.get("control_id"))
        step_order = coerced_non_negative_int(result["step_order"])
        role = result["role"]
        runtime_role = result["runtime_role"]
        normalized_output = result["normalized_output"]
        step_write = self.write_runner_step_result_artifacts(
            RunnerStepWriteRequest(
                run_id=context.run_id,
                layout=context.layout,
                iter_id=iteration.iter_id,
                step=step,
                step_order=step_order,
                role=role,
                runtime_role=runtime_role,
                normalized_output=normalized_output,
                task_language=runtime_task_language(context.compiled_spec),
            )
        )
        handoff = step_write.handoff
        actor = ActorRef.from_dict(result.get("actor_ref"))
        run_engine = RepositoryRunEngine(self.repository)
        submit_result = run_engine.submit_step(
            RunEngineSubmitStepRequest(result=self._runner_step_result_for_engine(context, iteration, result, handoff=handoff, actor=actor))
        )
        submitted_event = submit_result.submitted_event
        run_engine.record_step_evidence(
            RunEngineRecordStepEvidenceRequest(
                run_id=context.run_id,
                evidence_entry=step_write.evidence_entry,
                coverage_projection=step_write.coverage_projection,
                actor=actor,
                correlation_id=submitted_event.correlation_id,
                causation_id=submitted_event.event_id,
            )
        )
        iteration.current_outputs_by_step[step["id"]] = normalized_output
        iteration.current_outputs_by_role[role["id"]] = normalized_output
        if runtime_role != role["id"]:
            iteration.current_outputs_by_role[runtime_role] = normalized_output
        iteration.current_outputs_by_archetype[role["archetype"]] = normalized_output
        iteration.current_handoffs.append(handoff)
        session_ref = result.get("session_ref")
        if isinstance(session_ref, dict) and session_ref:
            iteration.current_session_refs_by_step[step["id"]] = dict(session_ref)
        step_instruction_context = required_step_instruction_context_from_mapping(result)
        iteration.step_results.append(
            self._build_runner_step_result_entry(
                RunnerStepResultEntryRequest(
                    step=step,
                    step_order=step_order,
                    role=role,
                    runtime_role=runtime_role,
                    execution_settings=result["execution_settings"],
                    normalized_output=normalized_output,
                    handoff=handoff,
                    step_instruction_context=step_instruction_context,
                )
            )
        )
        self._log_runner_step_completion(
            RunnerStepCompletionLogRequest(
                run=context.run,
                iter_id=iteration.iter_id,
                step=step,
                runtime_role=runtime_role,
                role=role,
                duration_ms=coerced_non_negative_int(result["duration_ms"]),
                normalized_output=normalized_output,
            )
        )

        if role["archetype"] in {"builder", "inspector"}:
            self._enforce_workspace_safety(context.run, context.run_dir, iteration.iter_id, role=runtime_role)

        if role["archetype"] == "gatekeeper" and not is_control_step:
            iteration.current_gatekeeper_result = normalized_output
            context.last_gatekeeper_result = normalized_output
            iteration.stagnation = self._record_gatekeeper_iteration_result(
                GatekeeperIterationRecordRequest(
                    layout=context.layout,
                    stagnation=iteration.stagnation,
                    normalized_output=normalized_output,
                    iter_id=iteration.iter_id,
                    previous_composite=iteration.previous_composite,
                    run=context.run,
                    run_id=context.run_id,
                )
            )
            if context.completion_mode == "gatekeeper" and normalized_output["passed"] and bool((step.get("action_policy") or {}).get("can_finish_run")):
                return self._finish_runner_gatekeeper_success(
                    RunnerGatekeeperSuccessRequest(
                        run_id=context.run_id,
                        run=context.run,
                        run_dir=context.run_dir,
                        strategy_source=context.strategy_source,
                        compiled_spec=context.compiled_spec,
                        iter_id=iteration.iter_id,
                        step=step,
                        runtime_role=runtime_role,
                        normalized_output=normalized_output,
                        stagnation=iteration.stagnation,
                        previous_composite=iteration.previous_composite,
                        layout=context.layout,
                        step_results=iteration.step_results,
                        current_outputs_by_step=iteration.current_outputs_by_step,
                        current_outputs_by_role=iteration.current_outputs_by_role,
                        current_outputs_by_archetype=iteration.current_outputs_by_archetype,
                        current_session_refs_by_step=iteration.current_session_refs_by_step,
                    )
                )
        elif role["archetype"] == "guide":
            iteration.current_guide_result = normalized_output
            self.append_run_event(
                context.run_id,
                "challenger_done",
                {
                    "iter": iteration.iter_id,
                    "mode": normalized_output.get("mode"),
                    "step_id": step["id"],
                    "role_name": role["name"],
                    "archetype": role["archetype"],
                },
                role=runtime_role,
            )
        return None

    def _runner_step_handoff_preview(self, context, iteration, result: dict) -> dict:
        return build_step_handoff(
            StepResultContext(
                layout=context.layout,
                iter_id=iteration.iter_id,
                step=result["step"],
                step_order=coerced_non_negative_int(result["step_order"]),
                role=result["role"],
                runtime_role=result["runtime_role"],
                output=result["normalized_output"],
                task_language=runtime_task_language(context.compiled_spec),
            )
        )

    def _runner_step_result_for_engine(
        self,
        context,
        iteration,
        result: dict,
        *,
        handoff: dict,
        actor: ActorRef | None = None,
    ):
        return runner_step_result(
            RunnerStepResultRequest(
                run_id=context.run_id,
                iteration=iteration.iter_id,
                step=result["step"],
                actor=actor or ActorRef.from_dict(result.get("actor_ref")),
                output=result["normalized_output"],
                handoff=handoff,
            )
        )
