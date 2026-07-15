from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.agent_adapters import normalize_agent_adapter_kind
from loopora.agent_native_state import agent_native_state, agent_native_submit_lock, write_agent_native_state
from loopora.agent_native_runtime_context import agent_native_iteration_state, agent_native_state_from_iteration
from loopora.context_iteration_summary import derive_latest_state_from_step_results
from loopora.agent_native_host_dispatch_validation import validate_agent_native_host_dispatch
from loopora.run_artifacts import RunArtifactLayout
from loopora.service_agent_native_requests import (
    AgentNativeNormalizedSubmit,
    AgentNativeStepSubmitRequest,
    AgentNativeSubmitContext,
    AgentNativeSubmitResponseRequest,
    agent_native_first_present_int,
)
from loopora.service_types import ACTIVE_RUN_STATUSES, LooporaConflictError, LooporaError, TERMINAL_RUN_STATUSES
from loopora.step_instruction_context import step_instruction_context_from_mapping
from loopora.utils import read_json, write_json


from loopora.agent_native_evidence_contracts import agent_native_unknown_evidence_refs


from loopora.agent_native_submit_validation import validate_agent_native_step_output_contract


from loopora.context_flow import evidence_entry_id

from loopora.engine.runner_context import evidence_context_with_canonical_items


from loopora.runner_summary_projection import StepOutputNormalizationRequest

from loopora.service_agent_native_requests import (
    agent_native_submit_guard_message,
)




from loopora.agent_native_coverage_summary import coverage_gap_summaries, required_coverage_summary



from loopora.evidence_coverage import load_or_build_evidence_coverage_projection

from loopora.service_agent_native_requests import AgentNativeStepClaimRequest

from loopora.utils import structured_non_negative_int

from collections.abc import Callable

from dataclasses import dataclass


from loopora.agent_native_controls import agent_native_control_queue_index

from loopora.agent_native_parallel_groups import agent_native_parallel_group_finished_payload

from loopora.agent_native_state import update_agent_native_parallel_group_snapshot_after_submit


from loopora.utils import coerced_non_negative_int



from loopora.runners import agent_runner_actor

from loopora.step_instruction_context import STEP_INSTRUCTION_CONTEXT_KEY




from loopora.agent_native_evidence_contracts import _agent_native_output_coverage_results


from loopora.service_agent_native_contracts import (
    agent_native_actionable_blocking_item,
    agent_native_actionable_repair_next_action,
)

@dataclass(frozen=True)
class AgentNativeSubmittedStepResultRequest:
    layout: RunArtifactLayout
    iter_id: int
    step: dict[str, Any]
    step_order: int
    role: dict[str, Any]
    runtime_role: str
    normalized_output: dict[str, Any]
    handoff: dict[str, Any]

def agent_native_submitted_step_result(request: AgentNativeSubmittedStepResultRequest) -> dict[str, Any]:
    step_id = str(request.step.get("id") or "").strip()
    evidence_refs = [str(item) for item in list(request.handoff.get("evidence_refs") or []) if str(item).strip()]
    if not evidence_refs and step_id:
        evidence_refs = [evidence_entry_id(request.iter_id, request.step_order, step_id)]
    handoff_path = request.layout.step_handoff_path(request.iter_id, request.step_order, step_id)
    blocking_items = [str(item).strip() for item in list(request.handoff.get("blocking_items") or []) if str(item).strip()]
    actionable_blocking_items = [agent_native_actionable_blocking_item(item) for item in blocking_items]
    recommended_next_action = agent_native_actionable_repair_next_action(
        str(request.handoff.get("recommended_next_action") or "").strip(),
        actionable_blocking_items,
    )
    submitted_step = {
        "iter": request.iter_id,
        "step_id": step_id,
        "step_order": request.step_order,
        "role": {
            "id": str(request.role.get("id") or ""),
            "name": str(request.role.get("name") or ""),
            "archetype": str(request.role.get("archetype") or ""),
        },
        "runtime_role": request.runtime_role,
        "status": str(
            request.handoff.get("status") or request.normalized_output.get("status") or request.normalized_output.get("mode") or "completed"
        ),
        "summary": str(
            request.handoff.get("summary")
            or request.normalized_output.get("summary")
            or request.normalized_output.get("decision_summary")
            or ""
        ).strip(),
        "evidence_refs": evidence_refs,
        "blocking_items": actionable_blocking_items,
        "recommended_next_action": recommended_next_action,
        "handoff_path": request.layout.relative(handoff_path),
        "handoff_absolute_path": str(handoff_path.resolve()),
    }
    coverage_results = _agent_native_output_coverage_results(request.normalized_output)
    if coverage_results:
        submitted_step["coverage_result_scope"] = "submitted_role_raw_classifications_not_aggregated_coverage"
        submitted_step["coverage_results"] = coverage_results
    return submitted_step

def agent_native_submitted_session_ref(request_session_ref: object, output: dict[str, Any]) -> dict:
    if isinstance(request_session_ref, dict):
        return request_session_ref
    session_ref = output.get("session_ref")
    return session_ref if isinstance(session_ref, dict) else {}

@dataclass(frozen=True)
class AgentNativeStepResultPayloadRequest:
    kind: str
    active: dict[str, Any]
    step: dict[str, Any]
    role: dict[str, Any]
    runtime_role: str
    normalized_output: dict[str, Any]
    step_instruction_context: dict[str, Any]
    iter_id: int
    step_order: int
    session_ref: dict

def agent_native_step_result_payload(request: AgentNativeStepResultPayloadRequest) -> dict[str, Any]:
    return {
        "skipped": False,
        "step_order": request.step_order,
        "step": request.step,
        "role": request.role,
        "runtime_role": request.runtime_role,
        "execution_settings": request.active.get("execution_settings")
        if isinstance(request.active.get("execution_settings"), dict)
        else {},
        "normalized_output": request.normalized_output,
        STEP_INSTRUCTION_CONTEXT_KEY: request.step_instruction_context,
        "session_ref": request.session_ref,
        "actor_ref": agent_runner_actor(request.kind).to_dict(),
        "duration_ms": 0,
        "iter_id": request.iter_id,
    }

@dataclass(frozen=True)
class AgentNativeStepAdvanceRequest:
    run: dict[str, Any]
    state: dict[str, Any]
    context: Any
    iter_id: int
    step: dict
    step_order: int
    is_control_step: bool

def agent_native_record_control_completion(
    run: dict,
    result: dict,
    *,
    append_run_event: Callable[..., None],
) -> bool:
    step = result["step"]
    if not step.get("control_id"):
        return False
    control = step.get("control") if isinstance(step.get("control"), dict) else {}
    evidence_id = evidence_entry_id(
        coerced_non_negative_int(result["iter_id"]),
        coerced_non_negative_int(result["step_order"]),
        str(step["id"]),
    )
    normalized_output = result["normalized_output"]
    append_run_event(
        run["id"],
        "control_completed",
        {
            **control,
            "status": normalized_output.get("status") or normalized_output.get("mode") or "completed",
            "evidence_refs": [evidence_id],
        },
        role=str(control.get("role_id") or result["runtime_role"]),
    )
    return True

def agent_native_advance_state_after_submit(
    request: AgentNativeStepAdvanceRequest,
    *,
    append_run_event: Callable[..., None],
) -> None:
    iter_id = coerced_non_negative_int(request.iter_id)
    step_order = coerced_non_negative_int(request.step_order)
    if request.is_control_step:
        queue = [item for item in list(request.state.get("control_queue") or []) if isinstance(item, dict)]
        request.state["control_queue_index"] = agent_native_control_queue_index(request.state, queue=queue) + 1
        request.state["step_index"] = len(request.context.strategy_steps)
        return
    parallel_finished = agent_native_parallel_group_finished_payload(
        request.context.strategy_steps,
        iter_id,
        request.step,
        step_order,
    )
    if parallel_finished is not None:
        append_run_event(request.run["id"], "parallel_group_finished", parallel_finished)
    request.state["step_index"] = step_order + 1
    update_agent_native_parallel_group_snapshot_after_submit(
        request.state,
        strategy_steps=request.context.strategy_steps,
        step=request.step,
        step_order=step_order,
    )

class ServiceAgentNativeSubmitResponseMixin:
    def _agent_native_submit_response(self, request: AgentNativeSubmitResponseRequest) -> dict[str, Any]:
        coverage_after_submit = _agent_native_submit_coverage_after_submit(request.layout)
        if request.finish_result is not None:
            request.state["status"] = "complete"
            write_agent_native_state(request.layout, request.state)
            self.repository.release_run_slot(request.run["id"])
            return self._with_agent_native_judgment_contract(
                {
                    "adapter": request.kind,
                    "run": request.finish_result,
                    "run_path": f"/runs/{request.run['id']}",
                    "next_step": None,
                    "complete": True,
                    "submitted_step": request.submitted_step,
                    "coverage_after_submit": coverage_after_submit,
                }
            )
        next_result = self.claim_agent_native_step(
            AgentNativeStepClaimRequest(
                adapter=request.kind,
                run_id=request.run["id"],
                entry_source=request.entry_source,
            )
        )
        next_result["submitted_step"] = request.submitted_step
        if coverage_after_submit:
            next_result["coverage_after_submit"] = coverage_after_submit
        return next_result

    @staticmethod
    def _agent_native_submitted_step_result(request: AgentNativeSubmittedStepResultRequest) -> dict[str, Any]:
        return agent_native_submitted_step_result(request)

def _agent_native_submit_coverage_after_submit(layout) -> dict[str, Any]:
    try:
        coverage = load_or_build_evidence_coverage_projection(layout)
    except (OSError, UnicodeError, ValueError):
        return {}
    if not isinstance(coverage, dict) or not coverage:
        return {}
    summary = coverage.get("summary") if isinstance(coverage.get("summary"), dict) else {}
    payload: dict[str, Any] = {
        "source": "evidence_coverage",
        "status": str(coverage.get("status") or "").strip(),
        "required_coverage": required_coverage_summary(coverage),
    }
    reason = str(summary.get("reason") or "").strip()
    if reason:
        payload["summary"] = reason
    for key in (
        "target_count",
        "covered_target_count",
        "weak_target_count",
        "missing_target_count",
        "blocked_target_count",
        "check_count",
        "covered_check_count",
        "missing_check_count",
        "residual_risk_count",
    ):
        payload[key] = structured_non_negative_int(coverage.get(key))
    missing_check_ids = [str(item).strip() for item in list(coverage.get("missing_check_ids") or []) if str(item).strip()]
    if missing_check_ids:
        payload["missing_check_ids"] = missing_check_ids[:8]
        if len(missing_check_ids) > 8:
            payload["missing_check_ids_omitted"] = len(missing_check_ids) - 8
    top_gaps = coverage_gap_summaries(coverage.get("top_gaps"), limit=3)
    if top_gaps:
        payload["top_gaps"] = top_gaps
    return {key: value for key, value in payload.items() if value not in ("", [], {})}

class ServiceAgentNativeSubmitNormalizationMixin:
    def _agent_native_normalized_submit(
        self,
        request: AgentNativeStepSubmitRequest,
        *,
        run: dict[str, Any],
        layout: RunArtifactLayout,
        output: dict[str, Any],
        submit_context: AgentNativeSubmitContext,
    ) -> AgentNativeNormalizedSubmit:
        active = submit_context.active
        step = submit_context.step
        iter_id = submit_context.iter_id
        step_order = submit_context.step_order
        step_id = submit_context.step_id
        context = submit_context.context
        iteration = submit_context.iteration
        role = submit_context.role
        runtime_role = submit_context.runtime_role
        step_instruction_context = submit_context.step_instruction_context
        host_dispatch = submit_context.host_dispatch
        self._validate_agent_native_step_output_contract(output, active=active)
        if role["archetype"] != "gatekeeper":
            unknown_refs = agent_native_unknown_evidence_refs(
                output,
                active=active,
                step_instruction_context=step_instruction_context,
            )
            if unknown_refs:
                raise LooporaError(
                    "agent-native evidence_refs_unknown: "
                    + ", ".join(unknown_refs[:4])
                    + ("..." if len(unknown_refs) > 4 else "")
                )
        normalized_output = self._normalize_step_output(
            StepOutputNormalizationRequest(
                archetype=role["archetype"],
                output=output,
                compiled_spec=context.compiled_spec,
                inspector_output=dict(iteration.current_outputs_by_archetype).get("inspector"),
                evidence_context=evidence_context_with_canonical_items(step_instruction_context, context.layout),
                current_evidence_id=evidence_entry_id(iter_id, step_order, step_id),
            )
        )
        result = agent_native_step_result_payload(
            AgentNativeStepResultPayloadRequest(
                kind=submit_context.kind,
                active=active,
                step=step,
                role=role,
                runtime_role=runtime_role,
                normalized_output=normalized_output,
                step_instruction_context=step_instruction_context,
                iter_id=iter_id,
                step_order=step_order,
                session_ref=agent_native_submitted_session_ref(request.session_ref, output),
            )
        )
        try:
            self.require_runner_step_result_submittable(context, iteration, result)
        except ValueError as exc:
            raise LooporaConflictError(agent_native_submit_guard_message(str(exc))) from exc
        write_json(layout.step_output_raw_path(iter_id, step_order, step_id), output)
        self._append_agent_native_step_submitted_event(request, submit_context=submit_context)
        finish_result = self.submit_runner_step_result(context, iteration, result)
        submitted_step = self._agent_native_submitted_step_result(
            AgentNativeSubmittedStepResultRequest(
                layout=layout,
                iter_id=iter_id,
                step=step,
                step_order=step_order,
                role=role,
                runtime_role=runtime_role,
                normalized_output=normalized_output,
                handoff=iteration.current_handoffs[-1] if iteration.current_handoffs else {},
            )
        )
        submitted_step["host_dispatch"] = host_dispatch
        is_control_step = self._agent_native_record_control_completion(run, result)
        return AgentNativeNormalizedSubmit(
            submitted_step=submitted_step,
            finish_result=finish_result,
            is_control_step=is_control_step,
        )

    @staticmethod
    def _validate_agent_native_step_output_contract(output: dict[str, Any], *, active: dict[str, Any]) -> None:
        validate_agent_native_step_output_contract(output, active=active)


class ServiceAgentNativeSubmitMixin(ServiceAgentNativeSubmitNormalizationMixin, ServiceAgentNativeSubmitResponseMixin):
    def _submit_agent_native_step_impl(self, request: AgentNativeStepSubmitRequest) -> dict[str, Any]:
        kind = normalize_agent_adapter_kind(request.adapter)
        run = self._agent_native_resolve_run(kind, workdir=request.workdir, context_id=request.context_id, run_id=request.run_id)
        if run["status"] in TERMINAL_RUN_STATUSES:
            raise LooporaConflictError(f"cannot submit agent-native step for terminal run {run['id']}")
        if run["status"] not in ACTIVE_RUN_STATUSES:
            raise LooporaConflictError(f"cannot submit agent-native step in status {run['status']}")
        if not isinstance(request.output, dict):
            raise LooporaError("agent-native step result must be a JSON object")
        output = request.output

        layout = self._run_artifact_layout(Path(run["runs_dir"]))
        with agent_native_submit_lock(layout):
            return self._submit_agent_native_step_locked(request, kind=kind, run=run, layout=layout, output=output)

    def _submit_agent_native_step_locked(
        self,
        request: AgentNativeStepSubmitRequest,
        *,
        kind: str,
        run: dict[str, Any],
        layout: RunArtifactLayout,
        output: dict[str, Any],
    ) -> dict[str, Any]:
        submit_context = self._agent_native_submit_context(request, kind=kind, run=run, layout=layout)
        normalized = self._agent_native_normalized_submit(
            request,
            run=run,
            layout=layout,
            output=output,
            submit_context=submit_context,
        )
        return self._agent_native_commit_submit(
            request,
            submit_context=submit_context,
            normalized=normalized,
        )

    def _agent_native_submit_context(
        self,
        request: AgentNativeStepSubmitRequest,
        *,
        kind: str,
        run: dict[str, Any],
        layout: RunArtifactLayout,
    ) -> AgentNativeSubmitContext:
        state = agent_native_state(layout, adapter=kind, run=run)
        active = state.get("active_step") if isinstance(state.get("active_step"), dict) else {}
        if not active:
            raise LooporaConflictError("no agent-native step is currently claimed; run next first")
        step = active.get("step") if isinstance(active.get("step"), dict) else {}
        step_id = str(request.step_id or step.get("id") or "").strip()
        if not step_id or step_id != str(step.get("id") or "").strip():
            raise LooporaConflictError("submitted step_id does not match the claimed agent-native step")

        iter_id = agent_native_first_present_int(active.get("iter_id"), state.get("iter_id"))
        step_order = agent_native_first_present_int(active.get("step_order"), state.get("step_index"))

        context = self._agent_native_run_context(run, state)
        iteration = agent_native_iteration_state(state)
        role = active.get("role") if isinstance(active.get("role"), dict) else context.role_by_id[step["role_id"]]
        runtime_role = str(active.get("runtime_role") or self._runtime_role_key(role))
        step_instruction_context = step_instruction_context_from_mapping(active)
        host_dispatch = self._validate_agent_native_host_dispatch(
            {
                "adapter": kind,
                "run": run,
                "step_id": step_id,
                "role": role,
                "active": active,
            },
            request.host_dispatch,
        )
        return AgentNativeSubmitContext(
            kind=kind,
            run=run,
            layout=layout,
            state=state,
            active=active,
            step=step,
            step_id=step_id,
            iter_id=iter_id,
            step_order=step_order,
            context=context,
            iteration=iteration,
            role=role,
            runtime_role=runtime_role,
            step_instruction_context=step_instruction_context,
            host_dispatch=host_dispatch,
        )

    def _agent_native_commit_submit(
        self,
        request: AgentNativeStepSubmitRequest,
        *,
        submit_context: AgentNativeSubmitContext,
        normalized: AgentNativeNormalizedSubmit,
    ) -> dict[str, Any]:
        kind = submit_context.kind
        run = submit_context.run
        layout = submit_context.layout
        state = submit_context.state
        context = submit_context.context
        iteration = submit_context.iteration
        step = submit_context.step
        iter_id = submit_context.iter_id
        step_order = submit_context.step_order
        host_dispatch = submit_context.host_dispatch
        submitted_step = normalized.submitted_step

        state.update(agent_native_state_from_iteration(iteration))
        state["control_fire_counts"] = dict(context.control_fire_counts)
        state["host_dispatches"] = [*list(state.get("host_dispatches") or []), host_dispatch]
        state["active_step"] = {}
        self._agent_native_advance_state_after_submit(
            AgentNativeStepAdvanceRequest(
                run=run,
                state=state,
                context=context,
                iter_id=iter_id,
                step=step,
                step_order=step_order,
                is_control_step=normalized.is_control_step,
            )
        )
        if normalized.finish_result is None:
            self._agent_native_refresh_latest_state(layout, iteration)
        write_agent_native_state(layout, state)
        return self._agent_native_submit_response(
            AgentNativeSubmitResponseRequest(
                kind=kind,
                run=run,
                state=state,
                layout=layout,
                finish_result=normalized.finish_result,
                submitted_step=submitted_step,
                entry_source=str(request.entry_source or "").strip(),
            )
        )

    def _append_agent_native_step_submitted_event(
        self,
        request: AgentNativeStepSubmitRequest,
        *,
        submit_context: AgentNativeSubmitContext,
    ) -> None:
        role = submit_context.role
        self.append_run_event(
            submit_context.run["id"],
            "agent_native_step_submitted",
            {
                "adapter": submit_context.kind,
                "iter": submit_context.iter_id,
                "step_id": submit_context.step_id,
                "step_order": submit_context.step_order,
                "role_name": role["name"],
                "archetype": role["archetype"],
                "entry_source": str(request.entry_source or "").strip(),
                "host_dispatch": submit_context.host_dispatch,
            },
            role=submit_context.runtime_role,
        )

    def _agent_native_advance_state_after_submit(self, request: AgentNativeStepAdvanceRequest) -> None:
        agent_native_advance_state_after_submit(request, append_run_event=self.append_run_event)

    def _agent_native_record_control_completion(self, run: dict, result: dict) -> bool:
        return agent_native_record_control_completion(run, result, append_run_event=self.append_run_event)

    @staticmethod
    def _agent_native_refresh_latest_state(layout: RunArtifactLayout, iteration: Any) -> None:
        previous_state = _safe_read_json_object(layout.latest_state_path)
        latest_state = derive_latest_state_from_step_results(
            previous_state,
            layout=layout,
            iter_id=iteration.iter_id,
            step_results=list(iteration.step_results),
        )
        write_json(layout.latest_state_path, latest_state)

    @staticmethod
    def _validate_agent_native_host_dispatch(context: dict[str, Any], dispatch: dict[str, Any] | None) -> dict[str, Any]:
        return validate_agent_native_host_dispatch(context, dispatch)


def _safe_read_json_object(path: Path) -> dict:
    try:
        payload = read_json(path)
    except (OSError, UnicodeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}
