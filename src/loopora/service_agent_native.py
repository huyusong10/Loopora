from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loopora.agent_adapters import normalize_agent_adapter_kind, read_agent_binding
from loopora.agent_native_capsule_context import (
    agent_native_capsule_continuation_context,
    agent_native_capsule_iteration_repair_context,
    agent_native_capsule_judgment_contract,
    agent_native_evidence_rules,
    agent_native_required_coverage,
    agent_native_todo_contract,
)
from loopora.agent_native_capsule import (
    AgentNativeCapsuleRequest,
    agent_native_capsule,
    agent_native_context_packet_with_coverage,
    refresh_agent_native_capsule_with_judgment_contract,
)
from loopora.agent_native_controls import (
    AgentNativeControlQueueRequest,
    agent_native_build_control_queue,
    agent_native_control_queue_index,
    agent_native_control_queue_iter_matches,
    agent_native_control_queue_step_order,
)
from loopora.agent_native_iteration_transition import (
    AgentNativeNextIterationStateRequest,
    agent_native_next_iteration_state_update,
)
from loopora.agent_native_parallel_groups import (
    agent_native_claim_input_snapshot,
    agent_native_parallel_group_started_payload,
)
from loopora.agent_native_result_template import (
    agent_native_result_template,
    write_agent_native_step_contract_files,
)
from loopora.agent_native_runtime_context import (
    agent_native_iteration_state,
    agent_native_run_context,
    agent_native_state_from_iteration,
)
from loopora.agent_native_submit_validation import (
    validate_agent_native_host_dispatch,
    validate_agent_native_step_output_contract,
)
from loopora.agent_native_state import (
    agent_native_state,
    agent_native_state_path,
    agent_native_step_already_submitted,
    agent_native_submit_lock,
    agent_native_submit_lock_path,
    update_agent_native_parallel_group_snapshot_after_submit,
    write_agent_native_state,
)
from loopora.agent_native_submit_flow import (
    AgentNativeStepAdvanceRequest as _AgentNativeStepAdvanceRequest,
    agent_native_advance_state_after_submit,
    agent_native_record_control_completion,
)
from loopora.agent_native_submitted_step import (
    AgentNativeSubmittedStepResultRequest,
    agent_native_submitted_step_result,
)
from loopora.agent_native_task_proof import agent_native_task_next_action, with_agent_native_judgment_contract
from loopora.context_flow import evidence_entry_id
from loopora.run_artifacts import RunArtifactLayout
from loopora.service_agent_native_contracts import (
    _agent_native_actionable_blocking_item as _agent_native_actionable_blocking_item,
    _agent_native_actionable_repair_next_action as _agent_native_actionable_repair_next_action,
    _agent_native_submit_command as _agent_native_submit_command,
    _agent_native_unknown_evidence_refs,
)
from loopora.service_types import ACTIVE_RUN_STATUSES, LooporaConflictError, LooporaError, LooporaNotFoundError, TERMINAL_RUN_STATUSES, normalize_completion_mode
from loopora.service_workflow_execution import (
    _WorkflowIterationState,
    _WorkflowRunContext,
    _evidence_context_with_canonical_items,
)
from loopora.service_workflow_failure_handling import WorkflowExhaustionRequest
from loopora.service_workflow_iteration_state import WorkflowIterationCheckpointRequest
from loopora.service_workflow_runtime import WorkflowStepRuntimeRequest
from loopora.service_workflow_support import StepOutputNormalizationRequest, WorkflowSummaryRequest
from loopora.structured_numbers import structured_non_negative_int
from loopora.utils import utc_now, write_json


@dataclass(frozen=True)
class AgentNativeStepClaimRequest:
    adapter: str
    workdir: Path | str | None = None
    context_id: str = ""
    run_id: str = ""
    entry_source: str = ""


@dataclass(frozen=True)
class AgentNativeStepSubmitRequest:
    adapter: str
    output: dict[str, Any]
    host_dispatch: dict[str, Any] | None = None
    workdir: Path | str | None = None
    context_id: str = ""
    run_id: str = ""
    step_id: str = ""
    session_ref: dict[str, Any] | None = None
    entry_source: str = ""


@dataclass(frozen=True)
class _AgentNativeRuntimeClaimRequest:
    kind: str
    run: dict
    state: dict[str, Any]
    context: _WorkflowRunContext
    iteration: _WorkflowIterationState
    step: dict
    step_order: int
    entry_source: str = ""


@dataclass(frozen=True)
class _AgentNativeSubmitResponseRequest:
    kind: str
    run: dict[str, Any]
    state: dict[str, Any]
    layout: RunArtifactLayout
    finish_result: dict[str, Any] | None
    submitted_step: dict[str, Any]
    entry_source: str


@dataclass(frozen=True)
class _AgentNativeSubmitContext:
    kind: str
    run: dict[str, Any]
    layout: RunArtifactLayout
    state: dict[str, Any]
    active: dict[str, Any]
    step: dict[str, Any]
    step_id: str
    iter_id: int
    step_order: int
    context: _WorkflowRunContext
    iteration: _WorkflowIterationState
    role: dict[str, Any]
    runtime_role: str
    context_packet: dict[str, Any]
    host_dispatch: dict[str, Any]


@dataclass(frozen=True)
class _AgentNativeNormalizedSubmit:
    submitted_step: dict[str, Any]
    finish_result: dict[str, Any] | None
    is_control_step: bool


class ServiceAgentNativeMixin:
    @staticmethod
    def _with_agent_native_judgment_contract(result: dict[str, Any]) -> dict[str, Any]:
        return with_agent_native_judgment_contract(result)

    @staticmethod
    def _agent_native_task_next_action(result: dict[str, Any]) -> dict[str, Any]:
        return agent_native_task_next_action(result)

    def prepare_agent_native_run(
        self,
        adapter: str,
        run_id: str,
        *,
        entry_source: str = "",
    ) -> dict[str, Any]:
        kind = normalize_agent_adapter_kind(adapter)
        run = self.get_run(run_id)
        if run["status"] in TERMINAL_RUN_STATUSES:
            return self._with_agent_native_judgment_contract({"run": run, "next_step": None, "complete": True})
        if run["status"] not in ACTIVE_RUN_STATUSES:
            raise LooporaConflictError(f"cannot prepare agent-native run in status {run['status']}")

        layout = self._run_artifact_layout(Path(run["runs_dir"]))
        state = self._agent_native_state(layout, adapter=kind, run=run)
        if str(entry_source or "").strip():
            state["entry_source"] = str(entry_source or "").strip()
        summary = "# Loopora Run Summary\n\nAwaiting host Agent step execution.\n"
        update: dict[str, Any] = {
            "status": "awaiting_agent",
            "summary_md": summary,
        }
        if not run.get("started_at"):
            update["started_at"] = utc_now()
        run = self.repository.update_run(run_id, **update)
        self._persist_summary_file(Path(run["runs_dir"]), summary)
        self.append_run_event(
            run_id,
            "agent_native_run_prepared",
            {
                "adapter": kind,
                "execution_plane": "agent_native",
                "entry_source": str(entry_source or "").strip(),
            },
        )
        self._write_agent_native_state(layout, state)
        next_result = self.claim_agent_native_step(
            AgentNativeStepClaimRequest(
                adapter=kind,
                run_id=run_id,
                entry_source=entry_source,
            )
        )
        return self._with_agent_native_judgment_contract(
            {
                "run": next_result["run"],
                "next_step": next_result.get("next_step"),
                "complete": bool(next_result.get("complete")),
            }
        )

    def claim_agent_native_step(self, request: AgentNativeStepClaimRequest) -> dict[str, Any]:
        kind = normalize_agent_adapter_kind(request.adapter)
        run = self._agent_native_resolve_run(kind, workdir=request.workdir, context_id=request.context_id, run_id=request.run_id)
        if run["status"] in TERMINAL_RUN_STATUSES:
            return self._with_agent_native_judgment_contract(
                {
                    "adapter": kind,
                    "run": run,
                    "run_path": f"/runs/{run['id']}",
                    "next_step": None,
                    "complete": True,
                }
            )
        if run["status"] not in ACTIVE_RUN_STATUSES:
            raise LooporaConflictError(f"cannot claim agent-native step in status {run['status']}")

        layout = self._run_artifact_layout(Path(run["runs_dir"]))
        state = self._agent_native_state(layout, adapter=kind, run=run)
        entry_source = str(request.entry_source or "").strip() or str(state.get("entry_source") or "").strip()
        if entry_source and state.get("entry_source") != entry_source:
            state["entry_source"] = entry_source
            self._write_agent_native_state(layout, state)
        active = state.get("active_step") if isinstance(state.get("active_step"), dict) else {}
        if active and active.get("capsule"):
            refreshed_context_packet = self._agent_native_context_packet_with_latest_coverage(
                layout,
                active.get("context_packet"),
            )
            if refreshed_context_packet != active.get("context_packet"):
                active["context_packet"] = refreshed_context_packet
            capsule = self._agent_native_capsule_with_judgment_contract(
                run,
                active["capsule"],
                context_packet=active.get("context_packet"),
            )
            if capsule != active["capsule"]:
                active["capsule"] = capsule
                state["active_step"] = active
                self._write_agent_native_state(layout, state)
            self._write_agent_native_step_contract_files(capsule)
            return self._with_agent_native_judgment_contract(
                {
                    "adapter": kind,
                    "run": run,
                    "run_path": f"/runs/{run['id']}",
                    "next_step": capsule,
                    "complete": False,
                }
            )

        context = self._agent_native_run_context(run, state)
        step_index = int(state.get("step_index") or 0)
        if step_index >= len(context.workflow_steps):
            return self._agent_native_finish_iteration_or_advance(kind, run, state, context)

        step = context.workflow_steps[step_index]
        iteration = self._agent_native_iteration_state(state)
        return self._agent_native_claim_runtime_step(
            _AgentNativeRuntimeClaimRequest(
                kind=kind,
                run=run,
                state=state,
                context=context,
                iteration=iteration,
                step=step,
                step_order=step_index,
                entry_source=entry_source,
            )
        )

    def _agent_native_claim_runtime_step(
        self,
        request: _AgentNativeRuntimeClaimRequest,
    ) -> dict[str, Any]:
        kind = request.kind
        run = request.run
        state = request.state
        context = request.context
        iteration = request.iteration
        step = request.step
        step_order = request.step_order
        role = context.role_by_id[step["role_id"]]
        execution_settings = self._resolve_role_execution_settings(run, step, role)
        claim_snapshot = agent_native_claim_input_snapshot(
            state,
            context,
            iteration,
            step,
            step_order,
            runtime_role_key=self._runtime_role_key,
        )
        prepared = self._prepare_workflow_step_request(
            WorkflowStepRuntimeRequest(
                executor=context.executor,
                run=run,
                compiled_spec=context.compiled_spec,
                layout=context.layout,
                iter_id=iteration.iter_id,
                step=step,
                step_order=step_order,
                role=role,
                prompt_files=context.prompt_files,
                execution_settings=execution_settings,
                run_contract=context.run_contract,
                current_outputs_by_step=claim_snapshot.current_outputs_by_step,
                current_outputs_by_role=claim_snapshot.current_outputs_by_role,
                current_outputs_by_archetype=claim_snapshot.current_outputs_by_archetype,
                current_handoffs=claim_snapshot.current_handoffs,
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
                evidence_items_snapshot=claim_snapshot.evidence_items_snapshot,
            )
        )
        runtime_role = str(prepared["runtime_role"])
        role_request = prepared["role_request"]
        context_packet = prepared["context_packet"] if isinstance(prepared.get("context_packet"), dict) else {}
        evidence_context = context_packet.get("evidence") if isinstance(context_packet.get("evidence"), dict) else {}
        capsule = self._agent_native_capsule(
            kind,
            run=run,
            layout=context.layout,
            iter_id=iteration.iter_id,
            step=step,
            step_order=step_order,
            role=role,
            runtime_role=runtime_role,
            prompt=str(prepared["prompt"]),
            output_schema=role_request.output_schema,
            known_evidence_ids=list(
                dict.fromkeys(str(item) for item in list(evidence_context.get("known_ids") or []) if str(item).strip())
            ),
            context_packet=context_packet,
            entry_source=request.entry_source,
        )
        self._write_agent_native_step_contract_files(capsule)
        state["active_step"] = {
            "claimed_at": utc_now(),
            "capsule": capsule,
            "context_packet": context_packet,
            "execution_settings": execution_settings,
            "role": role,
            "runtime_role": runtime_role,
            "step": step,
            "step_order": step_order,
            "iter_id": iteration.iter_id,
        }
        self._write_agent_native_state(context.layout, state)
        run = self.repository.update_run(run["id"], status="awaiting_agent", current_iter=iteration.iter_id, active_role=runtime_role)
        self.append_run_event(
            run["id"],
            "agent_native_step_claimed",
            {
                "adapter": kind,
                "iter": iteration.iter_id,
                "step_id": step["id"],
                "step_order": step_order,
                "role_name": role["name"],
                "archetype": role["archetype"],
                "runtime_role": runtime_role,
                "target_agent": str((capsule.get("role_dispatch") or {}).get("target_agent") or ""),
                "capsule_path": str(capsule.get("capsule_path") or ""),
                "result_template_path": str((capsule.get("submit_hint") or {}).get("result_template_path") or ""),
                "parallel_group": str(step.get("parallel_group") or ""),
                "control_id": str(step.get("control_id") or ""),
            },
            role=runtime_role,
        )
        parallel_started = agent_native_parallel_group_started_payload(context.workflow_steps, iteration.iter_id, step, step_order)
        if parallel_started is not None:
            self.append_run_event(run["id"], "parallel_group_started", parallel_started)
        return self._with_agent_native_judgment_contract(
            {
                "adapter": kind,
                "run": self._hydrate_run_files(run),
                "run_path": f"/runs/{run['id']}",
                "next_step": capsule,
                "complete": False,
            }
        )

    def submit_agent_native_step(self, request: AgentNativeStepSubmitRequest) -> dict[str, Any]:
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
        with self._agent_native_submit_lock(layout):
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
    ) -> _AgentNativeSubmitContext:
        state = self._agent_native_state(layout, adapter=kind, run=run)
        active = state.get("active_step") if isinstance(state.get("active_step"), dict) else {}
        if not active:
            raise LooporaConflictError("no agent-native step is currently claimed; run next first")
        step = active.get("step") if isinstance(active.get("step"), dict) else {}
        step_id = str(request.step_id or step.get("id") or "").strip()
        if not step_id or step_id != str(step.get("id") or "").strip():
            raise LooporaConflictError("submitted step_id does not match the claimed agent-native step")

        iter_id = int(active.get("iter_id") or state.get("iter_id") or 0)
        step_order = int(active.get("step_order") or state.get("step_index") or 0)
        if self._agent_native_step_already_submitted(layout, iter_id=iter_id, step_order=step_order, step_id=step_id):
            raise LooporaConflictError(
                "agent-native step was already submitted; rerun agent next --json if the run advanced or this result file is stale"
            )

        context = self._agent_native_run_context(run, state)
        iteration = self._agent_native_iteration_state(state)
        role = active.get("role") if isinstance(active.get("role"), dict) else context.role_by_id[step["role_id"]]
        runtime_role = str(active.get("runtime_role") or self._runtime_role_key(role))
        context_packet = active.get("context_packet") if isinstance(active.get("context_packet"), dict) else {}
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
        return _AgentNativeSubmitContext(
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
            context_packet=context_packet,
            host_dispatch=host_dispatch,
        )

    def _agent_native_normalized_submit(
        self,
        request: AgentNativeStepSubmitRequest,
        *,
        run: dict[str, Any],
        layout: RunArtifactLayout,
        output: dict[str, Any],
        submit_context: _AgentNativeSubmitContext,
    ) -> _AgentNativeNormalizedSubmit:
        active = submit_context.active
        step = submit_context.step
        iter_id = submit_context.iter_id
        step_order = submit_context.step_order
        step_id = submit_context.step_id
        context = submit_context.context
        iteration = submit_context.iteration
        role = submit_context.role
        runtime_role = submit_context.runtime_role
        context_packet = submit_context.context_packet
        host_dispatch = submit_context.host_dispatch
        self._validate_agent_native_step_output_contract(output, active=active)
        if role["archetype"] != "gatekeeper":
            unknown_refs = _agent_native_unknown_evidence_refs(output, active=active, context_packet=context_packet)
            if unknown_refs:
                raise LooporaError(
                    "agent-native evidence_refs_unknown: "
                    + ", ".join(unknown_refs[:4])
                    + ("..." if len(unknown_refs) > 4 else "")
                )
        write_json(layout.step_output_raw_path(iter_id, step_order, step_id), output)
        normalized_output = self._normalize_step_output(
            StepOutputNormalizationRequest(
                archetype=role["archetype"],
                output=output,
                compiled_spec=context.compiled_spec,
                inspector_output=dict(iteration.current_outputs_by_archetype).get("inspector"),
                evidence_context=_evidence_context_with_canonical_items(context_packet, context.layout),
                current_evidence_id=evidence_entry_id(iter_id, step_order, step_id),
            )
        )
        submitted_session_ref = request.session_ref if isinstance(request.session_ref, dict) else {}
        if not submitted_session_ref and isinstance(output.get("session_ref"), dict):
            submitted_session_ref = output["session_ref"]
        result = {
            "skipped": False,
            "step_order": step_order,
            "step": step,
            "role": role,
            "runtime_role": runtime_role,
            "execution_settings": active.get("execution_settings") if isinstance(active.get("execution_settings"), dict) else {},
            "normalized_output": normalized_output,
            "context_packet": context_packet,
            "session_ref": submitted_session_ref,
            "duration_ms": 0,
            "iter_id": iter_id,
        }
        finish_result = self._commit_workflow_step_result(context, iteration, result)
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
        return _AgentNativeNormalizedSubmit(
            submitted_step=submitted_step,
            finish_result=finish_result,
            is_control_step=is_control_step,
        )

    def _agent_native_commit_submit(
        self,
        request: AgentNativeStepSubmitRequest,
        *,
        submit_context: _AgentNativeSubmitContext,
        normalized: _AgentNativeNormalizedSubmit,
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
        runtime_role = submit_context.runtime_role
        role = submit_context.role
        host_dispatch = submit_context.host_dispatch
        step_id = submit_context.step_id
        submitted_step = normalized.submitted_step
        self.append_run_event(
            run["id"],
            "agent_native_step_submitted",
            {
                "adapter": kind,
                "iter": iter_id,
                "step_id": step_id,
                "step_order": step_order,
                "role_name": role["name"],
                "archetype": role["archetype"],
                "entry_source": str(request.entry_source or "").strip(),
                "host_dispatch": host_dispatch,
            },
            role=runtime_role,
        )

        state.update(self._state_from_iteration(iteration))
        state["control_fire_counts"] = dict(context.control_fire_counts)
        state["host_dispatches"] = [*list(state.get("host_dispatches") or []), host_dispatch]
        state["active_step"] = {}
        self._agent_native_advance_state_after_submit(
            _AgentNativeStepAdvanceRequest(
                run=run,
                state=state,
                context=context,
                iter_id=iter_id,
                step=step,
                step_order=step_order,
                is_control_step=normalized.is_control_step,
            )
        )
        self._write_agent_native_state(layout, state)
        return self._agent_native_submit_response(
            _AgentNativeSubmitResponseRequest(
                kind=kind,
                run=run,
                state=state,
                layout=layout,
                finish_result=normalized.finish_result,
                submitted_step=submitted_step,
                entry_source=str(request.entry_source or "").strip(),
            )
        )

    def _agent_native_submit_response(self, request: _AgentNativeSubmitResponseRequest) -> dict[str, Any]:
        if request.finish_result is not None:
            request.state["status"] = "complete"
            self._write_agent_native_state(request.layout, request.state)
            self.repository.release_run_slot(request.run["id"])
            return self._with_agent_native_judgment_contract(
                {
                    "adapter": request.kind,
                    "run": request.finish_result,
                    "run_path": f"/runs/{request.run['id']}",
                    "next_step": None,
                    "complete": True,
                    "submitted_step": request.submitted_step,
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
        return next_result

    def _agent_native_submitted_step_result(self, request: AgentNativeSubmittedStepResultRequest) -> dict[str, Any]:
        return agent_native_submitted_step_result(request)

    def _agent_native_advance_state_after_submit(self, request: _AgentNativeStepAdvanceRequest) -> None:
        agent_native_advance_state_after_submit(request, append_run_event=self.append_run_event)

    def _agent_native_record_control_completion(self, run: dict, result: dict) -> bool:
        return agent_native_record_control_completion(run, result, append_run_event=self.append_run_event)

    def _agent_native_finish_iteration_or_advance(
        self,
        adapter: str,
        run: dict,
        state: dict[str, Any],
        context: _WorkflowRunContext,
    ) -> dict[str, Any]:
        layout = context.layout
        iteration = self._agent_native_iteration_state(state)
        control_claim = self._agent_native_claim_pending_control_step(adapter, run, state, context, iteration)
        if control_claim is not None:
            return control_claim
        checkpoint = self._checkpoint_workflow_iteration_state(
            WorkflowIterationCheckpointRequest(
                layout=layout,
                iter_id=iteration.iter_id,
                step_results=iteration.step_results,
                current_outputs_by_step=iteration.current_outputs_by_step,
                current_outputs_by_role=iteration.current_outputs_by_role,
                current_outputs_by_archetype=iteration.current_outputs_by_archetype,
                current_session_refs_by_step=iteration.current_session_refs_by_step,
                stagnation=iteration.stagnation,
                previous_composite=iteration.previous_composite,
                run_id=run["id"],
            )
        )
        (
            previous_outputs_by_step,
            previous_outputs_by_role,
            previous_outputs_by_archetype,
            previous_handoffs_by_step,
            previous_handoffs_by_role,
            _previous_handoffs_by_archetype,
            previous_iteration_summary,
        ) = checkpoint
        summary = self._build_workflow_summary(
            WorkflowSummaryRequest(
                run=run,
                workflow=context.workflow,
                compiled_spec=context.compiled_spec,
                iter_id=iteration.iter_id,
                step_results=iteration.step_results,
                stagnation=iteration.stagnation,
                exhausted=False,
                previous_composite=iteration.previous_composite,
            )
        )
        self._write_summary(run["id"], "awaiting_agent", summary)
        max_iters = int(run.get("max_iters") or 0)
        next_iter = iteration.iter_id + 1
        if max_iters > 0 and next_iter >= max_iters:
            exhausted_summary = self._build_workflow_summary(
                WorkflowSummaryRequest(
                    run=run,
                    workflow=context.workflow,
                    compiled_spec=context.compiled_spec,
                    iter_id=iteration.iter_id,
                    step_results=iteration.step_results,
                    stagnation=iteration.stagnation,
                    exhausted=True,
                    previous_composite=iteration.previous_composite,
                )
            )
            finished = self._handle_workflow_exhaustion(
                WorkflowExhaustionRequest(
                    run_id=run["id"],
                    run=run,
                    run_dir=Path(run["runs_dir"]),
                    completion_mode=normalize_completion_mode(run.get("completion_mode", "gatekeeper")),
                    last_iter_id=iteration.iter_id,
                    summary=exhausted_summary,
                )
            )
            self.repository.release_run_slot(run["id"])
            state["status"] = "complete"
            self._write_agent_native_state(layout, state)
            return self._with_agent_native_judgment_contract(
                {
                    "adapter": adapter,
                    "run": finished,
                    "run_path": f"/runs/{run['id']}",
                    "next_step": None,
                    "complete": True,
                }
            )

        state.update(
            agent_native_next_iteration_state_update(
                AgentNativeNextIterationStateRequest(
                    iteration=iteration,
                    next_iter=next_iter,
                    previous_outputs_by_step=previous_outputs_by_step,
                    previous_outputs_by_role=previous_outputs_by_role,
                    previous_outputs_by_archetype=previous_outputs_by_archetype,
                    previous_handoffs_by_step=previous_handoffs_by_step,
                    previous_handoffs_by_role=previous_handoffs_by_role,
                    previous_iteration_summary=previous_iteration_summary,
                )
            )
        )
        self._write_agent_native_state(layout, state)
        return self.claim_agent_native_step(AgentNativeStepClaimRequest(adapter=adapter, run_id=run["id"]))

    def _agent_native_claim_pending_control_step(
        self,
        adapter: str,
        run: dict,
        state: dict[str, Any],
        context: _WorkflowRunContext,
        iteration: _WorkflowIterationState,
    ) -> dict[str, Any] | None:
        if not context.workflow_controls:
            return None
        if not agent_native_control_queue_iter_matches(state.get("control_queue_iter"), iteration.iter_id):
            state["control_queue"] = agent_native_build_control_queue(
                AgentNativeControlQueueRequest(
                    run=run,
                    state=state,
                    context=context,
                    iteration=iteration,
                    append_run_event=self.append_run_event,
                )
            )
            state["control_queue_index"] = 0
            state["control_queue_iter"] = iteration.iter_id
            state["control_fire_counts"] = dict(context.control_fire_counts)
            self._write_agent_native_state(context.layout, state)

        queue = [item for item in list(state.get("control_queue") or []) if isinstance(item, dict)]
        index = agent_native_control_queue_index(state, queue=queue)
        if index >= len(queue):
            return None
        entry = queue[index]
        step = entry.get("step") if isinstance(entry.get("step"), dict) else {}
        step_order = agent_native_control_queue_step_order(entry)
        if not step or step_order is None:
            state["control_queue_index"] = index + 1
            self._write_agent_native_state(context.layout, state)
            return self._agent_native_claim_pending_control_step(adapter, run, state, context, iteration)
        return self._agent_native_claim_runtime_step(
            _AgentNativeRuntimeClaimRequest(
                kind=adapter,
                run=run,
                state=state,
                context=context,
                iteration=iteration,
                step=step,
                step_order=step_order,
            )
        )

    def _agent_native_resolve_run(
        self,
        adapter: str,
        *,
        workdir: Path | str | None,
        context_id: str,
        run_id: str,
    ) -> dict:
        resolved_run_id = str(run_id or "").strip()
        if not resolved_run_id:
            if workdir is None:
                raise LooporaError("agent-native run lookup requires --run-id or --workdir")
            binding = read_agent_binding(adapter, workdir, context_id=context_id)
            resolved_run_id = str(binding.get("linked_run_id") or "").strip()
        if not resolved_run_id:
            raise LooporaConflictError("no Loopora run is associated with this agent session/workdir; run /loopora-run first")
        try:
            return self.get_run(resolved_run_id)
        except LooporaNotFoundError:
            raise

    def _agent_native_run_context(self, run: dict, state: dict[str, Any]) -> _WorkflowRunContext:
        layout = self._run_artifact_layout(Path(run["runs_dir"]))
        return agent_native_run_context(
            run,
            state,
            layout=layout,
            executor=self.executor_factory(),
            prompt_files=self._read_prompt_files_for_run(run),
        )

    def _agent_native_iteration_state(self, state: dict[str, Any]) -> _WorkflowIterationState:
        return agent_native_iteration_state(state)

    def _state_from_iteration(self, iteration: _WorkflowIterationState) -> dict[str, Any]:
        return agent_native_state_from_iteration(iteration)

    def _agent_native_state(self, layout, *, adapter: str, run: dict) -> dict[str, Any]:
        return agent_native_state(layout, adapter=adapter, run=run)

    @staticmethod
    def _agent_native_update_parallel_group_snapshot_after_submit(
        state: dict[str, Any],
        context: _WorkflowRunContext,
        step: dict,
        step_order: int,
    ) -> None:
        update_agent_native_parallel_group_snapshot_after_submit(
            state,
            workflow_steps=context.workflow_steps,
            step=step,
            step_order=step_order,
        )

    @staticmethod
    def _write_agent_native_state(layout, state: dict[str, Any]) -> None:
        write_agent_native_state(layout, state)

    @staticmethod
    def _agent_native_state_path(layout) -> Path:
        return agent_native_state_path(layout)

    @staticmethod
    def _agent_native_submit_lock(layout):
        return agent_native_submit_lock(layout)

    @staticmethod
    def _agent_native_submit_lock_path(layout) -> Path:
        return agent_native_submit_lock_path(layout)

    @staticmethod
    def _agent_native_step_already_submitted(layout, *, iter_id: int, step_order: int, step_id: str) -> bool:
        return agent_native_step_already_submitted(layout, iter_id=iter_id, step_order=step_order, step_id=step_id)

    def _agent_native_capsule(  # noqa: PLR0913 - capsule fields are the public step contract projection.
        self,
        adapter: str,
        *,
        run: dict,
        layout,
        iter_id: int,
        step: dict,
        step_order: int,
        role: dict,
        runtime_role: str,
        prompt: str,
        output_schema: dict,
        known_evidence_ids: list[str] | None = None,
        context_packet: dict[str, Any] | None = None,
        entry_source: str = "",
    ) -> dict[str, Any]:
        return agent_native_capsule(
            AgentNativeCapsuleRequest(
                adapter=adapter,
                run=run,
                layout=layout,
                iter_id=iter_id,
                step=step,
                step_order=step_order,
                role=role,
                runtime_role=runtime_role,
                prompt=prompt,
                output_schema=output_schema,
                known_evidence_ids=known_evidence_ids,
                context_packet=context_packet,
                entry_source=entry_source,
            )
        )

    def _write_agent_native_step_contract_files(self, capsule: dict[str, Any]) -> None:
        write_agent_native_step_contract_files(capsule)

    @staticmethod
    def _agent_native_result_template(capsule: dict[str, Any]) -> dict[str, Any]:
        return agent_native_result_template(capsule)

    @classmethod
    def _agent_native_capsule_with_judgment_contract(
        cls,
        run: dict,
        capsule: object,
        *,
        context_packet: object = None,
    ) -> dict[str, Any]:
        return refresh_agent_native_capsule_with_judgment_contract(run, capsule, context_packet=context_packet)

    def _agent_native_context_packet_with_latest_coverage(
        self,
        layout: RunArtifactLayout,
        context_packet: object,
    ) -> object:
        if not isinstance(context_packet, dict):
            return context_packet
        coverage = self._coverage_context_for_run(layout)
        return agent_native_context_packet_with_coverage(context_packet, coverage)

    @staticmethod
    def _agent_native_capsule_continuation_context(context_packet: object) -> dict[str, Any]:
        return agent_native_capsule_continuation_context(context_packet)

    @staticmethod
    def _agent_native_capsule_iteration_repair_context(context_packet: object) -> dict[str, Any]:
        return agent_native_capsule_iteration_repair_context(context_packet)

    @staticmethod
    def _agent_native_capsule_judgment_contract(run: dict, context_packet: object) -> dict[str, Any]:
        return agent_native_capsule_judgment_contract(run, context_packet)

    @staticmethod
    def _agent_native_required_coverage(context_packet: dict[str, Any] | None) -> dict[str, Any]:
        return agent_native_required_coverage(context_packet)

    @staticmethod
    def _agent_native_todo_contract(*, step_id: str, target_agent: str) -> dict[str, Any]:
        return agent_native_todo_contract(step_id=step_id, target_agent=target_agent)

    @staticmethod
    def _validate_agent_native_step_output_contract(output: dict[str, Any], *, active: dict[str, Any]) -> None:
        validate_agent_native_step_output_contract(output, active=active)

    @staticmethod
    def _validate_agent_native_host_dispatch(context: dict[str, Any], dispatch: dict[str, Any] | None) -> dict[str, Any]:
        return validate_agent_native_host_dispatch(context, dispatch)

    @staticmethod
    def _agent_native_evidence_rules(archetype: str) -> list[dict[str, str]]:
        return agent_native_evidence_rules(archetype)
