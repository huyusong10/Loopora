from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.agent_adapters import normalize_agent_adapter_kind
from loopora.agent_native_state import agent_native_state, agent_native_submit_lock, write_agent_native_state
from loopora.agent_native_runtime_context import agent_native_iteration_state, agent_native_state_from_iteration
from loopora.agent_native_submit_flow import (
    AgentNativeStepAdvanceRequest,
    agent_native_advance_state_after_submit,
    agent_native_record_control_completion,
)
from loopora.agent_native_host_dispatch_validation import validate_agent_native_host_dispatch
from loopora.run_artifacts import RunArtifactLayout
from loopora.service_agent_native_requests import (
    AgentNativeNormalizedSubmit,
    AgentNativeStepSubmitRequest,
    AgentNativeSubmitContext,
    AgentNativeSubmitResponseRequest,
    agent_native_first_present_int,
)
from loopora.service_agent_native_submit_normalization import ServiceAgentNativeSubmitNormalizationMixin
from loopora.service_agent_native_submit_response import ServiceAgentNativeSubmitResponseMixin
from loopora.service_types import ACTIVE_RUN_STATUSES, LooporaConflictError, LooporaError, TERMINAL_RUN_STATUSES
from loopora.step_instruction_context import step_instruction_context_from_mapping


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

    def _agent_native_advance_state_after_submit(self, request: AgentNativeStepAdvanceRequest) -> None:
        agent_native_advance_state_after_submit(request, append_run_event=self.append_run_event)

    def _agent_native_record_control_completion(self, run: dict, result: dict) -> bool:
        return agent_native_record_control_completion(run, result, append_run_event=self.append_run_event)

    @staticmethod
    def _validate_agent_native_host_dispatch(context: dict[str, Any], dispatch: dict[str, Any] | None) -> dict[str, Any]:
        return validate_agent_native_host_dispatch(context, dispatch)
