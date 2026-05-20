from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
import fcntl
from pathlib import Path
from typing import Any

from loopora.agent_adapters import normalize_agent_adapter_kind, read_agent_binding
from loopora.context_flow import evidence_entry_id
from loopora.recovery import RetryConfig
from loopora.run_artifacts import INITIAL_STAGNATION_STATE, RunArtifactLayout, read_jsonl
from loopora.run_takeaways import build_judgment_contract
from loopora.service_agent_native_contracts import (
    AGENT_NATIVE_WORKSPACE_ARTIFACT_FIELDS,
    _agent_native_actionable_blocking_item,
    _agent_native_actionable_repair_next_action,
    _agent_native_compact_known_evidence_refs,
    _agent_native_current_gap_repair_next_action,
    _agent_native_output_coverage_results,
    _agent_native_previous_blocked_handoff,
    _agent_native_repair_blockers_still_current,
    _agent_native_result_artifact_stem,
    _agent_native_result_scaffold_from_schema,
    _agent_native_role_posture_list,
    _agent_native_schema_validation_issues,
    _agent_native_string_list,
    _agent_native_submit_command,
    _agent_native_submit_hint_with_scoped_result_paths,
    _agent_native_template_coverage_targets,
    _agent_native_unknown_coverage_target_ids,
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
from loopora.service_workflow_controls import (
    WorkflowControlPayloadRequest,
    WorkflowControlStepRequest,
    build_workflow_control_payload,
    build_workflow_control_step,
    matching_workflow_controls,
    workflow_control_after_seconds,
    workflow_iteration_control_triggers,
)
from loopora.service_workflow_support import StepOutputNormalizationRequest, WorkflowSummaryRequest
from loopora.structured_booleans import structured_bool_is_true
from loopora.structured_numbers import structured_non_negative_int
from loopora.utils import read_json, utc_now, write_json
from loopora.workflows import normalize_workflow


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
class _AgentNativeControlSignalRequest:
    run: dict
    context: _WorkflowRunContext
    iteration: _WorkflowIterationState
    queue: list[dict[str, Any]]
    signal: str
    trigger: dict[str, object]


@dataclass(frozen=True)
class _AgentNativeClaimInputSnapshot:
    current_outputs_by_step: dict[str, dict]
    current_outputs_by_role: dict[str, dict]
    current_outputs_by_archetype: dict[str, dict]
    current_handoffs: list[dict]
    evidence_items_snapshot: list[dict] | None = None


@dataclass(frozen=True)
class _AgentNativeStepAdvanceRequest:
    run: dict
    state: dict[str, Any]
    context: _WorkflowRunContext
    iter_id: int
    step: dict
    step_order: int
    is_control_step: bool


@dataclass(frozen=True)
class _AgentNativeSubmittedStepResultRequest:
    layout: RunArtifactLayout
    iter_id: int
    step: dict[str, Any]
    step_order: int
    role: dict[str, Any]
    runtime_role: str
    normalized_output: dict[str, Any]
    handoff: dict[str, Any]


@dataclass(frozen=True)
class _AgentNativeSubmitResponseRequest:
    kind: str
    run: dict[str, Any]
    state: dict[str, Any]
    layout: RunArtifactLayout
    finish_result: dict[str, Any] | None
    submitted_step: dict[str, Any]
    entry_source: str


class ServiceAgentNativeMixin:
    @staticmethod
    def _with_agent_native_judgment_contract(result: dict[str, Any]) -> dict[str, Any]:
        run = result.get("run") if isinstance(result.get("run"), dict) else {}
        result["judgment_contract"] = build_judgment_contract(run)
        task_next_action = ServiceAgentNativeMixin._agent_native_task_next_action(result)
        if task_next_action:
            result["task_next_action"] = task_next_action
        return result

    @staticmethod
    def _agent_native_task_next_action(result: dict[str, Any]) -> dict[str, Any]:
        if result.get("complete") is not True:
            return {}
        run = result.get("run") if isinstance(result.get("run"), dict) else {}
        run_status = str(run.get("run_status") or run.get("status") or "").strip()
        if run_status not in TERMINAL_RUN_STATUSES:
            return {}
        task_verdict = run.get("task_verdict") if isinstance(run.get("task_verdict"), dict) else run.get("task_verdict_json")
        task_verdict = task_verdict if isinstance(task_verdict, dict) else {}
        status = str(task_verdict.get("status") or "").strip() or "not_evaluated"
        summary = str(task_verdict.get("summary") or "").strip()
        if status in {"passed", "passed_with_residual_risk"}:
            return {
                "kind": "already_passed",
                "reason": "task_verdict_passed",
                "run_status": run_status,
                "task_verdict_status": status,
                "task_verdict_summary": summary,
                "guidance": "Task verdict already passed; no new evidence pass will start unless the task scope changes.",
            }
        return {
            "kind": "continue_evidence",
            "reason": "run_lifecycle_complete_task_not_proven",
            "run_status": run_status,
            "task_verdict_status": status,
            "task_verdict_summary": summary,
            "next_loop_command": "/loopora-run",
            "plan_action": "open_run_url_improve_with_evidence_if_loop_needs_adjustment",
            "guidance": (
                "Run lifecycle is complete, but the task is not proven. Run /loopora-run again in the same "
                "Agent session to start the next evidence pass from this verdict."
            ),
        }

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
        claim_snapshot = self._agent_native_claim_input_snapshot(state, context, iteration, step, step_order)
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
        self._agent_native_record_parallel_group_started(run, context, iteration, step, step_order)
        return self._with_agent_native_judgment_contract(
            {
                "adapter": kind,
                "run": self._hydrate_run_files(run),
                "run_path": f"/runs/{run['id']}",
                "next_step": capsule,
                "complete": False,
            }
        )

    def _agent_native_claim_input_snapshot(
        self,
        state: dict[str, Any],
        context: _WorkflowRunContext,
        iteration: _WorkflowIterationState,
        step: dict,
        step_order: int,
    ) -> _AgentNativeClaimInputSnapshot:
        parallel_group = str(step.get("parallel_group") or "").strip()
        if not parallel_group:
            state["parallel_group_snapshot"] = {}
            return _AgentNativeClaimInputSnapshot(
                current_outputs_by_step=dict(iteration.current_outputs_by_step),
                current_outputs_by_role=dict(iteration.current_outputs_by_role),
                current_outputs_by_archetype=dict(iteration.current_outputs_by_archetype),
                current_handoffs=list(iteration.current_handoffs),
            )

        snapshot = self._agent_native_parallel_group_snapshot(state, context, iteration, step_order, parallel_group)
        return _AgentNativeClaimInputSnapshot(
            current_outputs_by_step=dict(snapshot.get("current_outputs_by_step") or {}),
            current_outputs_by_role=dict(snapshot.get("current_outputs_by_role") or {}),
            current_outputs_by_archetype=dict(snapshot.get("current_outputs_by_archetype") or {}),
            current_handoffs=list(snapshot.get("current_handoffs") or []),
            evidence_items_snapshot=[item for item in list(snapshot.get("evidence_items") or []) if isinstance(item, dict)],
        )

    def _agent_native_parallel_group_snapshot(
        self,
        state: dict[str, Any],
        context: _WorkflowRunContext,
        iteration: _WorkflowIterationState,
        step_order: int,
        parallel_group: str,
    ) -> dict[str, Any]:
        group_start, group_end, group_step_ids = self._agent_native_parallel_group_bounds(context.workflow_steps, step_order, parallel_group)
        existing = state.get("parallel_group_snapshot") if isinstance(state.get("parallel_group_snapshot"), dict) else {}
        if (
            existing
            and self._agent_native_int(existing.get("iter_id"), default=-1) == iteration.iter_id
            and str(existing.get("parallel_group") or "") == parallel_group
            and self._agent_native_int(existing.get("group_start"), default=-1) == group_start
            and self._agent_native_int(existing.get("group_end"), default=-1) == group_end
        ):
            return existing

        group_step_id_set = set(group_step_ids)
        group_roles = [context.role_by_id[step["role_id"]] for step in context.workflow_steps[group_start:group_end]]
        group_role_ids = {str(role["id"]) for role in group_roles}
        group_runtime_roles = {self._runtime_role_key(role) for role in group_roles}
        group_archetypes = {str(role["archetype"]) for role in group_roles}
        snapshot = {
            "iter_id": iteration.iter_id,
            "parallel_group": parallel_group,
            "group_start": group_start,
            "group_end": group_end,
            "step_ids": group_step_ids,
            "current_outputs_by_step": {
                step_id: output for step_id, output in iteration.current_outputs_by_step.items() if step_id not in group_step_id_set
            },
            "current_outputs_by_role": {
                role_id: output
                for role_id, output in iteration.current_outputs_by_role.items()
                if role_id not in group_role_ids and role_id not in group_runtime_roles
            },
            "current_outputs_by_archetype": {
                archetype: output for archetype, output in iteration.current_outputs_by_archetype.items() if archetype not in group_archetypes
            },
            "current_handoffs": [
                handoff
                for handoff in iteration.current_handoffs
                if str(((handoff.get("source") or {}) if isinstance(handoff, dict) else {}).get("step_id") or "") not in group_step_id_set
            ],
            "evidence_items": [
                item
                for item in read_jsonl(context.layout.evidence_ledger_path)
                if not (
                    isinstance(item, dict)
                    and self._agent_native_int(item.get("iter"), default=-1) == iteration.iter_id
                    and str(item.get("step_id") or "") in group_step_id_set
                )
            ],
        }
        state["parallel_group_snapshot"] = snapshot
        return snapshot

    @staticmethod
    def _agent_native_int(value: object, *, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _agent_native_parallel_group_bounds(steps: list[dict], step_order: int, parallel_group: str) -> tuple[int, int, list[str]]:
        group_start = step_order
        while group_start > 0 and str(steps[group_start - 1].get("parallel_group") or "").strip() == parallel_group:
            group_start -= 1
        group_end = step_order + 1
        while group_end < len(steps) and str(steps[group_end].get("parallel_group") or "").strip() == parallel_group:
            group_end += 1
        return group_start, group_end, [str(step["id"]) for step in steps[group_start:group_end]]

    def _agent_native_record_parallel_group_started(
        self,
        run: dict,
        context: _WorkflowRunContext,
        iteration: _WorkflowIterationState,
        step: dict,
        step_order: int,
    ) -> None:
        parallel_group = str(step.get("parallel_group") or "").strip()
        if not parallel_group:
            return
        group_start, _group_end, _group_step_ids = self._agent_native_parallel_group_bounds(
            context.workflow_steps,
            step_order,
            parallel_group,
        )
        if step_order != group_start:
            return
        self.append_run_event(
            run["id"],
            "parallel_group_started",
            self._agent_native_parallel_group_event_payload(context.workflow_steps, iteration.iter_id, step_order, parallel_group),
        )

    def _agent_native_record_parallel_group_finished(
        self,
        run: dict,
        context: _WorkflowRunContext,
        iter_id: int,
        step: dict,
        step_order: int,
    ) -> None:
        parallel_group = str(step.get("parallel_group") or "").strip()
        if not parallel_group:
            return
        next_step_order = step_order + 1
        if next_step_order < len(context.workflow_steps) and str(context.workflow_steps[next_step_order].get("parallel_group") or "").strip() == parallel_group:
            return
        self.append_run_event(
            run["id"],
            "parallel_group_finished",
            self._agent_native_parallel_group_event_payload(context.workflow_steps, iter_id, step_order, parallel_group),
        )

    def _agent_native_parallel_group_event_payload(
        self,
        steps: list[dict],
        iter_id: int,
        step_order: int,
        parallel_group: str,
    ) -> dict[str, object]:
        group_start, _group_end, group_step_ids = self._agent_native_parallel_group_bounds(steps, step_order, parallel_group)
        return {
            "iter": iter_id,
            "parallel_group": parallel_group,
            "step_orders": list(range(group_start, group_start + len(group_step_ids))),
            "step_ids": group_step_ids,
        }

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
            _AgentNativeSubmittedStepResultRequest(
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
        is_control_step = self._agent_native_record_control_completion(run, result)
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
                is_control_step=is_control_step,
            )
        )
        self._write_agent_native_state(layout, state)
        return self._agent_native_submit_response(
            _AgentNativeSubmitResponseRequest(
                kind=kind,
                run=run,
                state=state,
                layout=layout,
                finish_result=finish_result,
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

    def _agent_native_submitted_step_result(
        self,
        request: _AgentNativeSubmittedStepResultRequest,
    ) -> dict[str, Any]:
        step_id = str(request.step.get("id") or "").strip()
        evidence_refs = [str(item) for item in list(request.handoff.get("evidence_refs") or []) if str(item).strip()]
        if not evidence_refs and step_id:
            evidence_refs = [evidence_entry_id(request.iter_id, request.step_order, step_id)]
        handoff_path = request.layout.step_handoff_path(request.iter_id, request.step_order, step_id)
        blocking_items = [str(item).strip() for item in list(request.handoff.get("blocking_items") or []) if str(item).strip()]
        actionable_blocking_items = [_agent_native_actionable_blocking_item(item) for item in blocking_items]
        recommended_next_action = _agent_native_actionable_repair_next_action(
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
            submitted_step["coverage_results"] = coverage_results
        return submitted_step

    def _agent_native_advance_state_after_submit(self, request: _AgentNativeStepAdvanceRequest) -> None:
        if request.is_control_step:
            queue = [item for item in list(request.state.get("control_queue") or []) if isinstance(item, dict)]
            request.state["control_queue_index"] = self._agent_native_control_queue_index(request.state, queue=queue) + 1
            request.state["step_index"] = len(request.context.workflow_steps)
            return
        self._agent_native_record_parallel_group_finished(request.run, request.context, request.iter_id, request.step, request.step_order)
        request.state["step_index"] = request.step_order + 1
        self._agent_native_update_parallel_group_snapshot_after_submit(request.state, request.context, request.step, request.step_order)

    def _agent_native_record_control_completion(self, run: dict, result: dict) -> bool:
        step = result["step"]
        if not step.get("control_id"):
            return False
        control = step.get("control") if isinstance(step.get("control"), dict) else {}
        evidence_id = evidence_entry_id(int(result["iter_id"]), int(result["step_order"]), str(step["id"]))
        normalized_output = result["normalized_output"]
        self.append_run_event(
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
            {
                "iter_id": next_iter,
                "step_index": 0,
                "previous_composite": (
                    iteration.current_gatekeeper_result.get("composite_score")
                    if isinstance(iteration.current_gatekeeper_result, dict)
                    else iteration.previous_composite
                ),
                "previous_outputs_by_step": previous_outputs_by_step,
                "previous_outputs_by_role": previous_outputs_by_role,
                "previous_outputs_by_archetype": previous_outputs_by_archetype,
                "previous_handoffs_by_step": previous_handoffs_by_step,
                "previous_handoffs_by_role": previous_handoffs_by_role,
                "previous_iteration_summary": previous_iteration_summary,
                "previous_session_refs_by_step": dict(iteration.current_session_refs_by_step),
                "current_outputs_by_step": {},
                "current_outputs_by_role": {},
                "current_outputs_by_archetype": {},
                "current_handoffs": [],
                "current_session_refs_by_step": {},
                "current_gatekeeper_result": None,
                "current_guide_result": None,
                "step_results": [],
                "control_queue": [],
                "control_queue_index": 0,
                "control_queue_iter": None,
                "parallel_group_snapshot": {},
                "active_step": {},
                "stagnation": iteration.stagnation,
            }
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
        if not self._agent_native_control_queue_iter_matches(state.get("control_queue_iter"), iteration.iter_id):
            state["control_queue"] = self._agent_native_build_control_queue(run, state, context, iteration)
            state["control_queue_index"] = 0
            state["control_queue_iter"] = iteration.iter_id
            state["control_fire_counts"] = dict(context.control_fire_counts)
            self._write_agent_native_state(context.layout, state)

        queue = [item for item in list(state.get("control_queue") or []) if isinstance(item, dict)]
        index = self._agent_native_control_queue_index(state, queue=queue)
        if index >= len(queue):
            return None
        entry = queue[index]
        step = entry.get("step") if isinstance(entry.get("step"), dict) else {}
        step_order = self._agent_native_control_queue_step_order(entry)
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

    @staticmethod
    def _agent_native_control_queue_iter_matches(value: object, iter_id: int) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and value == iter_id

    @staticmethod
    def _agent_native_control_queue_index(state: dict[str, Any], *, queue: list[dict[str, Any]]) -> int:
        if "control_queue_index" not in state or state.get("control_queue_index") is None:
            return 0
        value = state.get("control_queue_index")
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            return value
        return len(queue)

    @staticmethod
    def _agent_native_control_queue_step_order(entry: dict[str, Any]) -> int | None:
        value = entry.get("step_order")
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            return value
        return None

    def _agent_native_build_control_queue(
        self,
        run: dict,
        state: dict[str, Any],
        context: _WorkflowRunContext,
        iteration: _WorkflowIterationState,
    ) -> list[dict[str, Any]]:
        queue: list[dict[str, Any]] = []
        for trigger in workflow_iteration_control_triggers(iteration.current_gatekeeper_result, iteration.stagnation):
            self._agent_native_append_controls_for_signal(
                _AgentNativeControlSignalRequest(
                    run=run,
                    context=context,
                    iteration=iteration,
                    queue=queue,
                    signal=trigger.signal,
                    trigger=trigger.trigger,
                )
            )
        state["control_fire_counts"] = dict(context.control_fire_counts)
        return queue

    def _agent_native_append_controls_for_signal(
        self,
        request: _AgentNativeControlSignalRequest,
    ) -> None:
        run = request.run
        context = request.context
        iteration = request.iteration
        queue = request.queue
        signal = request.signal
        trigger = request.trigger
        matching_controls = matching_workflow_controls(context.workflow_controls, signal)
        if not matching_controls:
            return
        for control in matching_controls:
            control_id = str(control.get("id") or "").strip()
            max_fires = structured_non_negative_int(control.get("max_fires_per_run"), default=1) or 1
            fired = self._agent_native_control_fire_count(context.control_fire_counts.get(control_id), max_fires=max_fires)
            role_id = str((control.get("call") or {}).get("role_id") or "").strip()
            elapsed_seconds = self._agent_native_elapsed_seconds(run)
            base_payload = build_workflow_control_payload(
                WorkflowControlPayloadRequest(
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
            if elapsed_seconds < workflow_control_after_seconds(base_payload["after"]):
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
            existing_control_count = sum(1 for item in iteration.step_results if item["step"].get("control_id")) + len(queue)
            control_step, control_order = build_workflow_control_step(
                WorkflowControlStepRequest(
                    control=control,
                    payload=base_payload,
                    role=role,
                    workflow_step_count=len(context.workflow_steps),
                    existing_control_count=existing_control_count,
                )
            )
            self.append_run_event(context.run_id, "control_triggered", base_payload, role=role_id)
            queue.append({"step": control_step, "step_order": control_order})

    @staticmethod
    def _agent_native_control_fire_count(value: object, *, max_fires: int) -> int:
        if value is None:
            return 0
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            return value
        return max_fires

    @staticmethod
    def _agent_native_elapsed_seconds(run: dict) -> float:
        started_at = str(run.get("started_at") or run.get("queued_at") or run.get("created_at") or "").strip()
        if not started_at:
            return 0.0
        try:
            started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        except ValueError:
            return 0.0
        if started.tzinfo is None:
            started = started.replace(tzinfo=UTC)
        return max((datetime.now(UTC) - started.astimezone(UTC)).total_seconds(), 0.0)

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
        workflow = run.get("workflow_json") or read_json(layout.contract_workflow_path)
        workflow = normalize_workflow(workflow)
        role_by_id = {role["id"]: role for role in workflow.get("roles", [])}
        return _WorkflowRunContext(
            run_id=run["id"],
            run=run,
            run_dir=Path(run["runs_dir"]),
            workflow=workflow,
            executor=self.executor_factory(),
            compiled_spec=run["compiled_spec_json"],
            retry_config=RetryConfig(max_retries=run["max_role_retries"]),
            prompt_files=self._read_prompt_files_for_run(run),
            layout=layout,
            run_contract=read_json(layout.run_contract_path),
            workflow_steps=list(workflow.get("steps", [])),
            workflow_controls=list(workflow.get("controls", [])),
            control_fire_counts=dict(state.get("control_fire_counts") or {}),
            workflow_started_at=0.0,
            role_by_id=role_by_id,
            completion_mode=normalize_completion_mode(run.get("completion_mode", "gatekeeper")),
            last_gatekeeper_result=state.get("current_gatekeeper_result") if isinstance(state.get("current_gatekeeper_result"), dict) else None,
        )

    def _agent_native_iteration_state(self, state: dict[str, Any]) -> _WorkflowIterationState:
        return _WorkflowIterationState(
            iter_id=int(state.get("iter_id") or 0),
            previous_composite=state.get("previous_composite"),
            stagnation=dict(state.get("stagnation") or INITIAL_STAGNATION_STATE),
            previous_outputs_by_step=dict(state.get("previous_outputs_by_step") or {}),
            previous_outputs_by_role=dict(state.get("previous_outputs_by_role") or {}),
            previous_outputs_by_archetype=dict(state.get("previous_outputs_by_archetype") or {}),
            previous_handoffs_by_step=dict(state.get("previous_handoffs_by_step") or {}),
            previous_handoffs_by_role=dict(state.get("previous_handoffs_by_role") or {}),
            previous_iteration_summary=state.get("previous_iteration_summary") if isinstance(state.get("previous_iteration_summary"), dict) else None,
            previous_session_refs_by_step=dict(state.get("previous_session_refs_by_step") or {}),
            step_results=list(state.get("step_results") or []),
            current_outputs_by_step=dict(state.get("current_outputs_by_step") or {}),
            current_outputs_by_role=dict(state.get("current_outputs_by_role") or {}),
            current_outputs_by_archetype=dict(state.get("current_outputs_by_archetype") or {}),
            current_handoffs=list(state.get("current_handoffs") or []),
            current_session_refs_by_step=dict(state.get("current_session_refs_by_step") or {}),
            current_gatekeeper_result=state.get("current_gatekeeper_result") if isinstance(state.get("current_gatekeeper_result"), dict) else None,
            current_guide_result=state.get("current_guide_result") if isinstance(state.get("current_guide_result"), dict) else None,
        )

    def _state_from_iteration(self, iteration: _WorkflowIterationState) -> dict[str, Any]:
        return {
            "iter_id": iteration.iter_id,
            "previous_composite": iteration.previous_composite,
            "stagnation": iteration.stagnation,
            "previous_outputs_by_step": iteration.previous_outputs_by_step,
            "previous_outputs_by_role": iteration.previous_outputs_by_role,
            "previous_outputs_by_archetype": iteration.previous_outputs_by_archetype,
            "previous_handoffs_by_step": iteration.previous_handoffs_by_step,
            "previous_handoffs_by_role": iteration.previous_handoffs_by_role,
            "previous_iteration_summary": iteration.previous_iteration_summary,
            "previous_session_refs_by_step": iteration.previous_session_refs_by_step,
            "step_results": iteration.step_results,
            "current_outputs_by_step": iteration.current_outputs_by_step,
            "current_outputs_by_role": iteration.current_outputs_by_role,
            "current_outputs_by_archetype": iteration.current_outputs_by_archetype,
            "current_handoffs": iteration.current_handoffs,
            "current_session_refs_by_step": iteration.current_session_refs_by_step,
            "current_gatekeeper_result": iteration.current_gatekeeper_result,
            "current_guide_result": iteration.current_guide_result,
        }

    def _agent_native_state(self, layout, *, adapter: str, run: dict) -> dict[str, Any]:
        path = self._agent_native_state_path(layout)
        if path.exists():
            try:
                payload = read_json(path)
            except (OSError, UnicodeError, ValueError) as exc:
                raise LooporaError(f"agent-native state is unreadable: {path}: {exc}") from exc
            if isinstance(payload, dict) and payload:
                return payload
        return {
            "version": 1,
            "execution_plane": "agent_native",
            "adapter": adapter,
            "run_id": run["id"],
            "status": "awaiting_agent",
            "iter_id": 0,
            "step_index": 0,
            "previous_composite": None,
            "stagnation": dict(INITIAL_STAGNATION_STATE),
            "previous_outputs_by_step": {},
            "previous_outputs_by_role": {},
            "previous_outputs_by_archetype": {},
            "previous_handoffs_by_step": {},
            "previous_handoffs_by_role": {},
            "previous_iteration_summary": None,
            "previous_session_refs_by_step": {},
            "current_outputs_by_step": {},
            "current_outputs_by_role": {},
            "current_outputs_by_archetype": {},
            "current_handoffs": [],
            "current_session_refs_by_step": {},
            "current_gatekeeper_result": None,
            "current_guide_result": None,
            "step_results": [],
            "control_fire_counts": {},
            "control_queue": [],
            "control_queue_index": 0,
            "control_queue_iter": None,
            "parallel_group_snapshot": {},
            "host_dispatches": [],
            "active_step": {},
        }

    @staticmethod
    def _agent_native_update_parallel_group_snapshot_after_submit(
        state: dict[str, Any],
        context: _WorkflowRunContext,
        step: dict,
        step_order: int,
    ) -> None:
        parallel_group = str(step.get("parallel_group") or "").strip()
        if not parallel_group:
            state["parallel_group_snapshot"] = {}
            return
        next_step_order = step_order + 1
        if next_step_order < len(context.workflow_steps) and str(context.workflow_steps[next_step_order].get("parallel_group") or "").strip() == parallel_group:
            return
        state["parallel_group_snapshot"] = {}

    def _write_agent_native_state(self, layout, state: dict[str, Any]) -> None:
        write_json(self._agent_native_state_path(layout), state)

    @staticmethod
    def _agent_native_state_path(layout) -> Path:
        return layout.run_dir / "agent_native" / "state.json"

    @contextmanager
    def _agent_native_submit_lock(self, layout) -> Iterator[None]:
        # Agent submits can arrive from separate CLI processes; evidence/state writes must be single-accept.
        lock_path = self._agent_native_submit_lock_path(layout)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _agent_native_submit_lock_path(layout) -> Path:
        return layout.run_dir / "agent_native" / "submit.lock"

    @staticmethod
    def _agent_native_step_already_submitted(layout, *, iter_id: int, step_order: int, step_id: str) -> bool:
        existing_id = evidence_entry_id(iter_id, step_order, step_id)
        return any(str(item.get("id") or "").strip() == existing_id for item in read_jsonl(layout.evidence_ledger_path))

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
        context_path = layout.step_context_path(iter_id, step_order, step["id"])
        capsule_path = layout.step_capsule_path(iter_id, step_order, step["id"])
        output_path = layout.step_output_raw_path(iter_id, step_order, step["id"])
        result_outbox_dir = layout.workdir_path / ".loopora" / "agent_outbox" / adapter
        result_artifact_stem = _agent_native_result_artifact_stem(
            run_id=str(run["id"]),
            iter_id=iter_id,
            step_order=step_order,
            step_id=str(step["id"]),
        )
        result_template_path = result_outbox_dir / f"{result_artifact_stem}.result.template.json"
        result_file_path = result_outbox_dir / f"{result_artifact_stem}.result.json"
        if known_evidence_ids is None:
            known_evidence_ids = list(
                dict.fromkeys(
                    str(item.get("id"))
                    for item in read_jsonl(layout.evidence_ledger_path)
                    if isinstance(item, dict) and str(item.get("id") or "").strip()
                )
            )
        else:
            known_evidence_ids = list(dict.fromkeys(str(item) for item in known_evidence_ids if str(item).strip()))
        normalized_entry_source = str(entry_source or "").strip()
        target_agent = self._agent_native_target_agent(role["archetype"])
        target_agent_config_path = self._agent_native_target_agent_config_path(adapter, target_agent)
        target_agent_config_absolute_path = str((layout.workdir_path / target_agent_config_path).resolve()) if target_agent_config_path else ""
        return {
            "execution_plane": "agent_native",
            "adapter": adapter,
            "entry_source": normalized_entry_source,
            "run_id": run["id"],
            "run_path": f"/runs/{run['id']}",
            "iter": iter_id,
            "step_id": step["id"],
            "step_order": step_order,
            "parallel_group": str(step.get("parallel_group") or ""),
            "role": {
                "id": role["id"],
                "name": role["name"],
                "archetype": role["archetype"],
                "prompt_ref": str(role.get("prompt_ref") or ""),
                "posture_notes": str(role.get("posture_notes") or "").strip(),
                "runtime_role": runtime_role,
            },
            "role_dispatch": {
                "required": True,
                "dispatch_contract": "host_native_subagent",
                "target_agent": target_agent,
                "target_agent_config_path": target_agent_config_path,
                "target_agent_config_absolute_path": target_agent_config_absolute_path,
                "target_agent_config_exists": Path(target_agent_config_absolute_path).exists() if target_agent_config_absolute_path else False,
                "target_role_archetype": role["archetype"],
                "inline_allowed": False,
                "proof_field": "loopora_host_dispatch",
                "result_field": "result",
                "accepted_dispatch_modes": ["host_subagent", "host_task", "host_agent"],
            },
            "inputs": dict(step.get("inputs") or {}) if isinstance(step.get("inputs"), dict) else {},
            "action_policy": dict(step.get("action_policy") or {}),
            "required_coverage": self._agent_native_required_coverage(context_packet),
            "judgment_contract": self._agent_native_capsule_judgment_contract(run, context_packet),
            "continuation": self._agent_native_capsule_continuation_context(context_packet),
            "iteration_repair": self._agent_native_capsule_iteration_repair_context(context_packet),
            "prompt": prompt,
            "output_schema": output_schema,
            "evidence_rules": self._agent_native_evidence_rules(role["archetype"]),
            "evidence_ref_contract": {
                "allowed_ids_field": "known_evidence_ids",
                "unknown_ids_are_blocking": True,
                "must_copy_exact_ids": True,
            },
            "context_path": layout.relative(context_path),
            "context_absolute_path": str(context_path.resolve()),
            "capsule_path": layout.relative(capsule_path),
            "capsule_absolute_path": str(capsule_path.resolve()),
            "result_output_path": layout.relative(output_path),
            "submit_hint": {
                "command": _agent_native_submit_command(
                    adapter=adapter,
                    run_id=str(run["id"]),
                    step_id=str(step["id"]),
                    entry_source=normalized_entry_source,
                    result_file=str(result_file_path.resolve()),
                ),
                "result_file_contract": "Write one wrapper JSON object with loopora_host_dispatch and a schema-shaped result; replace null placeholders before submit.",
                "result_outbox_dir": layout.workspace_relative(result_outbox_dir),
                "result_outbox_absolute_dir": str(result_outbox_dir.resolve()),
                "result_file_path": layout.workspace_relative(result_file_path),
                "result_file_absolute_path": str(result_file_path.resolve()),
                "result_template_path": layout.workspace_relative(result_template_path),
                "result_template_absolute_path": str(result_template_path.resolve()),
            },
            "known_evidence_ids": known_evidence_ids,
            "known_evidence_refs": _agent_native_compact_known_evidence_refs(known_evidence_ids, context_packet),
            "known_evidence_count": len(known_evidence_ids),
        }

    def _write_agent_native_step_contract_files(self, capsule: dict[str, Any]) -> None:
        capsule_path_text = str(capsule.get("capsule_absolute_path") or "").strip()
        if not capsule_path_text:
            raise LooporaError("agent-native capsule path is required")
        capsule_path = Path(capsule_path_text)
        write_json(capsule_path, capsule)

        submit_hint = capsule.get("submit_hint") if isinstance(capsule.get("submit_hint"), dict) else {}
        template_path_text = str(submit_hint.get("result_template_absolute_path") or "").strip()
        if not template_path_text:
            raise LooporaError("agent-native result template path is required")
        template_path = Path(template_path_text)
        write_json(template_path, self._agent_native_result_template(capsule))

    @staticmethod
    def _agent_native_result_template(capsule: dict[str, Any]) -> dict[str, Any]:
        dispatch = capsule.get("role_dispatch") if isinstance(capsule.get("role_dispatch"), dict) else {}
        target_agent = str(dispatch.get("target_agent") or "").strip()
        output_schema = dict(capsule.get("output_schema") or {}) if isinstance(capsule.get("output_schema"), dict) else {}
        coverage_targets = _agent_native_template_coverage_targets(capsule)
        iteration_repair = dict(capsule.get("iteration_repair") or {}) if isinstance(capsule.get("iteration_repair"), dict) else {}
        submit_hint = capsule.get("submit_hint") if isinstance(capsule.get("submit_hint"), dict) else {}
        result_contract = {
            "ignored_on_submit": True,
            "result_must_match_output_schema": True,
            "result_is_schema_shaped_scaffold": True,
            "result_scaffold_uses_null_placeholders": True,
            "replace_null_placeholders_before_submit": True,
            "remove_optional_placeholders_if_unused": True,
            "array_placeholders_show_item_shape": True,
            "step_id": str(capsule.get("step_id") or ""),
            "role": dict(capsule.get("role") or {}) if isinstance(capsule.get("role"), dict) else {},
            "action_policy": dict(capsule.get("action_policy") or {}) if isinstance(capsule.get("action_policy"), dict) else {},
            "required_coverage": dict(capsule.get("required_coverage") or {}) if isinstance(capsule.get("required_coverage"), dict) else {},
            "coverage_target_ids": [str(item["id"]) for item in coverage_targets],
            "coverage_targets": coverage_targets,
            "known_evidence_ids": list(
                dict.fromkeys(str(item) for item in list(capsule.get("known_evidence_ids") or []) if isinstance(item, str))
            ),
            "known_evidence_refs": [
                dict(item) for item in list(capsule.get("known_evidence_refs") or []) if isinstance(item, dict)
            ],
            "evidence_ref_contract": dict(capsule.get("evidence_ref_contract") or {})
            if isinstance(capsule.get("evidence_ref_contract"), dict)
            else {},
            "evidence_rules": [dict(item) for item in list(capsule.get("evidence_rules") or []) if isinstance(item, dict)],
            "output_schema": output_schema,
        }
        result_file_to_write = str(submit_hint.get("result_file_absolute_path") or submit_hint.get("result_file_path") or "").strip()
        if result_file_to_write:
            result_contract["result_file_to_write"] = result_file_to_write
        submit_command = str(submit_hint.get("command") or "").strip()
        if submit_command:
            result_contract["submit_command"] = submit_command
        result_template_path = str(
            submit_hint.get("result_template_absolute_path") or submit_hint.get("result_template_path") or ""
        ).strip()
        if result_template_path:
            result_contract["result_template_path"] = result_template_path
        if iteration_repair.get("active") is True:
            result_contract["iteration_repair"] = iteration_repair
        return {
            "loopora_host_dispatch": {
                "schema_version": 1,
                "adapter": str(capsule.get("adapter") or ""),
                "run_id": str(capsule.get("run_id") or ""),
                "iter": structured_non_negative_int(capsule.get("iter")),
                "step_id": str(capsule.get("step_id") or ""),
                "step_order": structured_non_negative_int(capsule.get("step_order")),
                "target_agent": target_agent,
                "actual_agent": target_agent,
                "dispatch_mode": "host_subagent",
                "inline": False,
                "attestation": "The host invoked the named Loopora role agent for this step.",
            },
            "loopora_result_contract": result_contract,
            "result": _agent_native_result_scaffold_from_schema(output_schema),
        }

    @classmethod
    def _agent_native_capsule_with_judgment_contract(
        cls,
        run: dict,
        capsule: object,
        *,
        context_packet: object = None,
    ) -> dict[str, Any]:
        if not isinstance(capsule, dict):
            raise LooporaError("agent-native active step capsule is invalid")
        normalized = dict(capsule)
        normalized["judgment_contract"] = cls._agent_native_capsule_judgment_contract(run, context_packet)
        normalized["required_coverage"] = cls._agent_native_required_coverage(context_packet)
        normalized["continuation"] = cls._agent_native_capsule_continuation_context(context_packet)
        normalized["iteration_repair"] = cls._agent_native_capsule_iteration_repair_context(context_packet)
        role = normalized.get("role") if isinstance(normalized.get("role"), dict) else {}
        archetype = str(role.get("archetype") or "").strip()
        if archetype:
            normalized["evidence_rules"] = cls._agent_native_evidence_rules(archetype)
        cls._refresh_agent_native_submit_hint(normalized)
        cls._refresh_agent_native_role_dispatch_availability(normalized)
        known_evidence_ids = normalized.get("known_evidence_ids")
        if isinstance(known_evidence_ids, list):
            known_evidence_ids = list(dict.fromkeys(str(item) for item in known_evidence_ids if isinstance(item, str)))
            normalized["known_evidence_ids"] = known_evidence_ids
        normalized["known_evidence_count"] = len(known_evidence_ids) if isinstance(known_evidence_ids, list) else 0
        normalized["known_evidence_refs"] = (
            _agent_native_compact_known_evidence_refs(known_evidence_ids, context_packet) if isinstance(known_evidence_ids, list) else []
        )
        return normalized

    def _agent_native_context_packet_with_latest_coverage(
        self,
        layout: RunArtifactLayout,
        context_packet: object,
    ) -> object:
        if not isinstance(context_packet, dict):
            return context_packet
        coverage = self._coverage_context_for_run(layout)
        iteration = dict(context_packet.get("iteration") or {}) if isinstance(context_packet.get("iteration"), dict) else {}
        refreshed_iteration = {
            **iteration,
            "coverage_status": coverage["status"],
            "covered_check_count": coverage["covered_check_count"],
            "missing_check_count": coverage["missing_check_count"],
            "covered_check_ids": list(coverage["covered_check_ids"]),
            "missing_check_ids": list(coverage["missing_check_ids"]),
            "target_count": coverage["target_count"],
            "covered_target_count": coverage["covered_target_count"],
            "weak_target_count": coverage["weak_target_count"],
            "missing_target_count": coverage["missing_target_count"],
            "blocked_target_count": coverage["blocked_target_count"],
            "coverage_top_gaps": [dict(item) for item in list(coverage["top_gaps"]) if isinstance(item, dict)],
        }
        refreshed_packet = dict(context_packet)
        refreshed_packet["iteration"] = refreshed_iteration
        return refreshed_packet

    @staticmethod
    def _refresh_agent_native_submit_hint(capsule: dict[str, Any]) -> None:
        submit_hint = dict(capsule.get("submit_hint") or {}) if isinstance(capsule.get("submit_hint"), dict) else {}
        if not submit_hint:
            return
        adapter = str(capsule.get("adapter") or "").strip()
        run_id = str(capsule.get("run_id") or "").strip()
        step_id = str(capsule.get("step_id") or "").strip()
        if not adapter or not run_id or not step_id:
            return
        submit_hint = _agent_native_submit_hint_with_scoped_result_paths(submit_hint, capsule, run_id=run_id, step_id=step_id)
        result_file = str(submit_hint.get("result_file_absolute_path") or submit_hint.get("result_file_path") or "").strip()
        if not result_file:
            template_path = str(submit_hint.get("result_template_absolute_path") or submit_hint.get("result_template_path") or "").strip()
            if template_path.endswith(".result.template.json"):
                result_file = template_path[: -len(".result.template.json")] + ".result.json"
        if result_file and result_file != "RESULT_JSON_PATH":
            if Path(result_file).is_absolute():
                submit_hint["result_file_absolute_path"] = result_file
            else:
                submit_hint["result_file_path"] = result_file
        submit_hint["command"] = _agent_native_submit_command(
            adapter=adapter,
            run_id=run_id,
            step_id=step_id,
            entry_source=str(capsule.get("entry_source") or "").strip(),
            result_file=result_file or "RESULT_JSON_PATH",
        )
        capsule["submit_hint"] = submit_hint

    @staticmethod
    def _refresh_agent_native_role_dispatch_availability(capsule: dict[str, Any]) -> None:
        dispatch = dict(capsule.get("role_dispatch") or {}) if isinstance(capsule.get("role_dispatch"), dict) else {}
        if not dispatch:
            return
        config_path = str(dispatch.get("target_agent_config_absolute_path") or "").strip()
        if not config_path:
            config_path = str(dispatch.get("target_agent_config_path") or "").strip()
        if not config_path:
            dispatch["target_agent_config_exists"] = False
            capsule["role_dispatch"] = dispatch
            return
        dispatch["target_agent_config_exists"] = Path(config_path).expanduser().exists()
        capsule["role_dispatch"] = dispatch

    @staticmethod
    def _agent_native_capsule_continuation_context(context_packet: object) -> dict[str, Any]:
        packet = context_packet if isinstance(context_packet, dict) else {}
        continuation = packet.get("continuation") if isinstance(packet.get("continuation"), dict) else {}
        return dict(continuation) if continuation.get("active") is True else {}

    @staticmethod
    def _agent_native_capsule_iteration_repair_context(context_packet: object) -> dict[str, Any]:
        packet = context_packet if isinstance(context_packet, dict) else {}
        iteration = packet.get("iteration") if isinstance(packet.get("iteration"), dict) else {}
        previous_summary = packet.get("upstream", {}).get("previous_iteration_summary") if isinstance(packet.get("upstream"), dict) else None
        previous_summary = previous_summary if isinstance(previous_summary, dict) else {}
        iter_index = structured_non_negative_int(iteration.get("iter_index"))
        if not previous_summary and not (iter_index and iter_index > 0):
            return {}
        blocked_handoff = _agent_native_previous_blocked_handoff(previous_summary)
        gatekeeper_verdict = previous_summary.get("gatekeeper_verdict") if isinstance(previous_summary.get("gatekeeper_verdict"), dict) else {}
        blocking_items = _agent_native_string_list(blocked_handoff.get("blocking_items"))
        if not blocking_items:
            blocking_items = _agent_native_string_list(gatekeeper_verdict.get("blocking_issues"))
        blocking_items = [_agent_native_actionable_blocking_item(item) for item in blocking_items if item]
        top_gaps = [dict(item) for item in list(iteration.get("coverage_top_gaps") or []) if isinstance(item, dict)][:5]
        summary = str(blocked_handoff.get("summary") or gatekeeper_verdict.get("decision_summary") or "").strip()
        recommended_next_action = str(
            blocked_handoff.get("recommended_next_action")
            or gatekeeper_verdict.get("feedback_to_builder")
            or gatekeeper_verdict.get("feedback_to_generator")
            or ""
        ).strip()
        if not _agent_native_repair_blockers_still_current(blocking_items, top_gaps):
            blocking_items = []
            recommended_next_action = _agent_native_current_gap_repair_next_action(top_gaps)
        recommended_next_action = _agent_native_actionable_repair_next_action(recommended_next_action, blocking_items)
        if not any((blocking_items, top_gaps, summary, recommended_next_action)):
            return {}
        source = blocked_handoff.get("source") if isinstance(blocked_handoff.get("source"), dict) else {}
        return {
            "active": True,
            "previous_iteration": structured_non_negative_int(previous_summary.get("iter")),
            "source_step_id": str(source.get("step_id") or "").strip(),
            "source_role": str(source.get("role_name") or source.get("role_id") or "").strip(),
            "status": str(blocked_handoff.get("status") or "").strip(),
            "summary": summary,
            "blocking_items": blocking_items[:8],
            "recommended_next_action": recommended_next_action,
            "evidence_refs": _agent_native_string_list(blocked_handoff.get("evidence_refs"))[:8],
            "top_gaps": top_gaps,
        }

    @staticmethod
    def _agent_native_capsule_judgment_contract(run: dict, context_packet: object) -> dict[str, Any]:
        packet = context_packet if isinstance(context_packet, dict) else {}
        contract = packet.get("contract") if isinstance(packet.get("contract"), dict) else {}
        if not contract:
            return build_judgment_contract(run)
        projection = build_judgment_contract(run)
        contract_role_postures = _agent_native_role_posture_list(contract.get("role_postures"))
        contract_coverage_targets = [dict(item) for item in list(contract.get("coverage_targets") or []) if isinstance(item, dict)]
        projection.update(
            {
                "contract_path": str(contract.get("path") or projection.get("contract_path") or "").strip(),
                "goal": str(contract.get("goal") or projection.get("goal") or "").strip(),
                "constraints": str(contract.get("constraints") or projection.get("constraints") or "").strip(),
                "check_mode": str(contract.get("check_mode") or projection.get("check_mode") or "").strip(),
                "check_count": structured_non_negative_int(contract.get("check_count")),
                "completion_mode": str(contract.get("completion_mode") or projection.get("completion_mode") or "").strip(),
                "collaboration_summary": str(contract.get("collaboration_summary") or projection.get("collaboration_summary") or "").strip(),
                "loop_fit_reasons": _agent_native_string_list(contract.get("loop_fit_reasons")) or projection.get("loop_fit_reasons", []),
                "workflow_preset": str(contract.get("workflow_preset") or projection.get("workflow_preset") or "").strip(),
                "workflow_collaboration_intent": str(
                    contract.get("workflow_collaboration_intent") or projection.get("workflow_collaboration_intent") or ""
                ).strip(),
                "judgment_tradeoffs": _agent_native_string_list(contract.get("judgment_tradeoffs")) or projection.get("judgment_tradeoffs", []),
                "execution_strategy": _agent_native_string_list(contract.get("execution_strategy")) or projection.get("execution_strategy", []),
                "local_governance": _agent_native_string_list(contract.get("local_governance")) or projection.get("local_governance", []),
                "role_postures": contract_role_postures or projection.get("role_postures", []),
                "coverage_targets": contract_coverage_targets or projection.get("coverage_targets", []),
                "success_surface": _agent_native_string_list(contract.get("success_surface")) or projection.get("success_surface", []),
                "fake_done_states": _agent_native_string_list(contract.get("fake_done_states")) or projection.get("fake_done_states", []),
                "evidence_preferences": _agent_native_string_list(contract.get("evidence_preferences")) or projection.get("evidence_preferences", []),
                "residual_risk": str(contract.get("residual_risk") or projection.get("residual_risk") or "").strip(),
            }
        )
        return projection

    @staticmethod
    def _agent_native_required_coverage(context_packet: dict[str, Any] | None) -> dict[str, Any]:
        packet = context_packet if isinstance(context_packet, dict) else {}
        iteration = packet.get("iteration") if isinstance(packet.get("iteration"), dict) else {}
        return {
            "status": str(iteration.get("coverage_status") or "pending"),
            "evidence_progress_mode": str(iteration.get("evidence_progress_mode") or "none"),
            "covered_check_count": structured_non_negative_int(iteration.get("covered_check_count")),
            "missing_check_count": structured_non_negative_int(iteration.get("missing_check_count")),
            "target_count": structured_non_negative_int(iteration.get("target_count")),
            "covered_target_count": structured_non_negative_int(iteration.get("covered_target_count")),
            "weak_target_count": structured_non_negative_int(iteration.get("weak_target_count")),
            "missing_target_count": structured_non_negative_int(iteration.get("missing_target_count")),
            "blocked_target_count": structured_non_negative_int(iteration.get("blocked_target_count")),
            "covered_check_ids": [str(item) for item in list(iteration.get("covered_check_ids") or []) if str(item).strip()],
            "missing_check_ids": [str(item) for item in list(iteration.get("missing_check_ids") or []) if str(item).strip()],
            "top_gaps": [dict(item) for item in list(iteration.get("coverage_top_gaps") or []) if isinstance(item, dict)][:5],
        }

    @staticmethod
    def _agent_native_target_agent(archetype: str) -> str:
        normalized = str(archetype or "").strip().lower()
        if normalized == "builder":
            return "loopora-builder"
        if normalized == "gatekeeper":
            return "loopora-gatekeeper"
        if normalized == "guide":
            return "loopora-guide"
        return "loopora-inspector"

    @staticmethod
    def _agent_native_target_agent_config_path(adapter: str, target_agent: str) -> str:
        normalized_adapter = str(adapter or "").strip().lower()
        normalized_agent = str(target_agent or "").strip()
        if not normalized_agent:
            return ""
        if normalized_adapter == "codex":
            return f".codex/agents/{normalized_agent}.toml"
        if normalized_adapter == "claude":
            return f".claude/agents/{normalized_agent}.md"
        if normalized_adapter == "opencode":
            return f".opencode/agents/{normalized_agent}.md"
        return ""

    @staticmethod
    def _required_agent_native_dispatch_text(dispatch: dict[str, Any], field: str) -> str:
        value = str(dispatch.get(field) or "").strip()
        if not value:
            raise LooporaConflictError(f"agent-native host dispatch {field} is required")
        return value

    @staticmethod
    def _required_agent_native_dispatch_int(dispatch: dict[str, Any], field: str) -> int:
        value = dispatch.get(field)
        if isinstance(value, bool) or not isinstance(value, int):
            raise LooporaConflictError(f"agent-native host dispatch {field} is required")
        return value

    @staticmethod
    def _agent_native_dispatch_schema_version(dispatch: dict[str, Any]) -> int:
        value = dispatch.get("schema_version")
        if value is None or value == "":
            return 1
        if isinstance(value, bool) or not isinstance(value, int):
            raise LooporaConflictError("agent-native host dispatch schema_version must be an integer")
        return value

    @staticmethod
    def _agent_native_role_dispatch_for_submit(active: dict[str, Any]) -> dict[str, Any]:
        capsule = active.get("capsule") if isinstance(active.get("capsule"), dict) else {}
        role_dispatch = capsule.get("role_dispatch") if isinstance(capsule.get("role_dispatch"), dict) else {}
        if not role_dispatch:
            raise LooporaConflictError("agent-native role_dispatch is required")
        if not structured_bool_is_true(role_dispatch.get("required")):
            raise LooporaConflictError("agent-native role_dispatch.required must be literal true")
        if not isinstance(role_dispatch.get("inline_allowed"), bool):
            raise LooporaConflictError("agent-native role_dispatch.inline_allowed must be a literal boolean")
        if not str(role_dispatch.get("target_agent") or "").strip():
            raise LooporaConflictError("agent-native role_dispatch.target_agent is required")
        accepted_modes = role_dispatch.get("accepted_dispatch_modes")
        if not isinstance(accepted_modes, list) or not any(str(item).strip() for item in accepted_modes):
            raise LooporaConflictError("agent-native role_dispatch.accepted_dispatch_modes must be a non-empty list")
        return role_dispatch

    @staticmethod
    def _agent_native_output_schema(active: dict[str, Any]) -> dict[str, Any]:
        capsule = active.get("capsule") if isinstance(active.get("capsule"), dict) else {}
        output_schema = capsule.get("output_schema") if isinstance(capsule.get("output_schema"), dict) else {}
        return dict(output_schema)

    @staticmethod
    def _agent_native_required_capsule_object(active: dict[str, Any], field_name: str) -> dict[str, Any]:
        capsule = active.get("capsule") if isinstance(active.get("capsule"), dict) else {}
        value = capsule.get(field_name)
        if not isinstance(value, dict) or not value:
            raise LooporaConflictError(f"agent-native {field_name} is required")
        return dict(value)

    @staticmethod
    def _validate_agent_native_known_evidence_ids(active: dict[str, Any]) -> None:
        capsule = active.get("capsule") if isinstance(active.get("capsule"), dict) else {}
        if "known_evidence_ids" not in capsule or not isinstance(capsule.get("known_evidence_ids"), list):
            raise LooporaConflictError("agent-native known_evidence_ids must be a list")
        if any(not isinstance(item, str) for item in capsule["known_evidence_ids"]):
            raise LooporaConflictError("agent-native known_evidence_ids must contain strings")

    @staticmethod
    def _validate_agent_native_action_policy(action_policy: dict[str, Any]) -> None:
        workspace = str(action_policy.get("workspace") or "").strip()
        if workspace not in {"read_only", "workspace_write"}:
            raise LooporaConflictError("agent-native action_policy.workspace must be read_only or workspace_write")
        for field in ("can_block", "can_finish_run"):
            if not isinstance(action_policy.get(field), bool):
                raise LooporaConflictError(f"agent-native action_policy.{field} must be a literal boolean")

    def _validate_agent_native_step_output_contract(self, output: dict[str, Any], *, active: dict[str, Any]) -> None:
        output_schema = self._agent_native_output_schema(active)
        if not output_schema:
            raise LooporaConflictError("agent-native output_schema is required")

        self._agent_native_required_capsule_object(active, "judgment_contract")
        self._agent_native_required_capsule_object(active, "required_coverage")
        action_policy = self._agent_native_required_capsule_object(active, "action_policy")
        self._validate_agent_native_action_policy(action_policy)
        self._validate_agent_native_known_evidence_ids(active)

        if str(action_policy.get("workspace") or "").strip() != "workspace_write":
            workspace_fields = [field for field in AGENT_NATIVE_WORKSPACE_ARTIFACT_FIELDS if _agent_native_string_list(output.get(field))]
            if workspace_fields:
                raise LooporaConflictError(
                    "agent-native read-only step cannot claim workspace artifact fields: "
                    + ", ".join(workspace_fields)
                )

        schema_issues = _agent_native_schema_validation_issues(output, output_schema)
        if schema_issues:
            raise LooporaConflictError(
                "agent-native result does not match output_schema: "
                + "; ".join(schema_issues[:6])
                + ("..." if len(schema_issues) > 6 else "")
            )

        unknown_targets = _agent_native_unknown_coverage_target_ids(output, active=active)
        if unknown_targets:
            raise LooporaConflictError(
                "agent-native coverage_results_unknown_target_id: "
                + ", ".join(unknown_targets[:4])
                + ("..." if len(unknown_targets) > 4 else "")
            )

    def _validate_agent_native_host_dispatch(self, context: dict[str, Any], dispatch: dict[str, Any] | None) -> dict[str, Any]:
        adapter = str(context["adapter"])
        run = context["run"]
        step_id = str(context["step_id"])
        active = context["active"]
        role_dispatch = self._agent_native_role_dispatch_for_submit(active)
        if not isinstance(dispatch, dict) or not dispatch:
            raise LooporaConflictError("agent-native submit requires loopora_host_dispatch proof from the host native role agent")

        expected_agent = str(role_dispatch.get("target_agent") or "").strip()
        accepted_modes = {str(item) for item in list(role_dispatch.get("accepted_dispatch_modes") or []) if str(item).strip()}
        actual_agent = str(dispatch.get("actual_agent") or dispatch.get("agent_name") or "").strip()
        target_agent = str(dispatch.get("target_agent") or "").strip()
        dispatch_mode = str(dispatch.get("dispatch_mode") or dispatch.get("mode") or "").strip()
        if not isinstance(dispatch.get("inline"), bool):
            raise LooporaConflictError("agent-native host dispatch inline must be a literal boolean")
        inline = dispatch["inline"]

        if actual_agent != expected_agent or target_agent != expected_agent:
            raise LooporaConflictError(f"agent-native submit used {actual_agent or target_agent or 'unknown'} but expected {expected_agent}")
        if accepted_modes and dispatch_mode not in accepted_modes:
            raise LooporaConflictError(f"agent-native submit dispatch_mode must be one of {sorted(accepted_modes)}")
        if inline and not structured_bool_is_true(role_dispatch.get("inline_allowed")):
            raise LooporaConflictError("agent-native submit cannot claim inline role execution for this step")

        dispatch_run_id = self._required_agent_native_dispatch_text(dispatch, "run_id")
        dispatch_step_id = self._required_agent_native_dispatch_text(dispatch, "step_id")
        dispatch_adapter = self._required_agent_native_dispatch_text(dispatch, "adapter")
        if dispatch_run_id != str(run["id"]):
            raise LooporaConflictError("agent-native host dispatch run_id does not match the submitted run")
        if dispatch_step_id != step_id:
            raise LooporaConflictError("agent-native host dispatch step_id does not match the submitted step")
        if dispatch_adapter != adapter:
            raise LooporaConflictError("agent-native host dispatch adapter does not match the submitted adapter")
        dispatch_position = self._agent_native_dispatch_position(active, dispatch)

        normalized = {
            "schema_version": self._agent_native_dispatch_schema_version(dispatch),
            "adapter": adapter,
            "run_id": str(run["id"]),
            "step_id": step_id,
            "target_agent": expected_agent,
            "actual_agent": actual_agent,
            "dispatch_mode": dispatch_mode,
            "inline": inline,
            "attestation": str(dispatch.get("attestation") or "").strip(),
        }
        normalized.update(dispatch_position)
        return normalized

    def _agent_native_dispatch_position(self, active: dict[str, Any], dispatch: dict[str, Any]) -> dict[str, int]:
        position: dict[str, int] = {}
        expected_iter = self._agent_native_expected_dispatch_int(active, "iter_id", "iter")
        expected_step_order = self._agent_native_expected_dispatch_int(active, "step_order", "step_order")
        if expected_iter is not None:
            dispatch_iter = self._required_agent_native_dispatch_int(dispatch, "iter")
            if dispatch_iter != expected_iter:
                raise LooporaConflictError("agent-native host dispatch iter does not match the claimed agent-native step")
            position["iter"] = expected_iter
        if expected_step_order is not None:
            dispatch_step_order = self._required_agent_native_dispatch_int(dispatch, "step_order")
            if dispatch_step_order != expected_step_order:
                raise LooporaConflictError("agent-native host dispatch step_order does not match the claimed agent-native step")
            position["step_order"] = expected_step_order
        return position

    @staticmethod
    def _agent_native_expected_dispatch_int(active: dict[str, Any], active_field: str, capsule_field: str) -> int | None:
        value = active.get(active_field)
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        capsule = active.get("capsule") if isinstance(active.get("capsule"), dict) else {}
        value = capsule.get(capsule_field)
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        return None

    @staticmethod
    def _agent_native_evidence_rules(archetype: str) -> list[dict[str, str]]:
        base_rules = [
            {
                "id": "evidence_refs.must_be_exact_known_ids",
                "severity": "hard",
                "rule": "Every evidence_refs value, including coverage_results evidence_refs, must be copied exactly from known_evidence_ids. Do not invent, suffix, split, or derive new evidence IDs.",
            },
            {
                "id": "coverage_results.status_uses_coverage_vocabulary",
                "severity": "hard",
                "rule": "coverage_results.status must use coverage vocabulary such as covered, weak, blocked, or missing; keep Proven, Weak, Unproven, Blocking, and Residual risk as verdict buckets or notes.",
            },
            {
                "id": "coverage_results.target_id_must_be_known_coverage_target",
                "severity": "hard",
                "rule": "Every coverage_results.target_id must be copied exactly from loopora_result_contract.coverage_target_ids or active judgment_contract.coverage_targets[].id; do not invent or rename coverage target IDs.",
            }
        ]
        if archetype == "inspector":
            return [
                *base_rules,
                {
                    "id": "inspector.coverage_requires_current_evidence",
                    "severity": "hard",
                    "rule": "Mark coverage passed only when current upstream evidence already proves it.",
                },
                {
                    "id": "inspector.no_future_terminal_claim",
                    "severity": "hard",
                    "rule": "Do not mark a future terminal run state as passed before GateKeeper has completed.",
                },
            ]
        if archetype == "gatekeeper":
            return [
                *base_rules,
                {
                    "id": "gatekeeper.pass_requires_supporting_upstream_evidence",
                    "severity": "hard",
                    "rule": "A pass must cite supporting upstream evidence_refs from known_evidence_ids.",
                },
                {
                    "id": "gatekeeper.blocked_refs_do_not_support_pass",
                    "severity": "hard",
                    "rule": "Evidence from blocked, failed, rejected, or errored steps cannot support a pass.",
                },
                {
                    "id": "gatekeeper.finish_coverage_is_core_derived",
                    "severity": "hard",
                    "rule": "Do not add a passed gatekeeper.finish coverage row; Loopora Core derives finish coverage from the submitted verdict.",
                },
            ]
        if archetype == "builder":
            return [
                *base_rules,
                {
                    "id": "builder.proof_artifacts_strengthen_evidence",
                    "severity": "advisory",
                    "rule": "When possible, include concrete proof_files or proof_artifacts so downstream GateKeeper evidence is supportable.",
                },
            ]
        return base_rules
