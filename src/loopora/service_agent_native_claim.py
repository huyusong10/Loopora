from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.agent_adapters import normalize_agent_adapter_kind
from loopora.agent_native_claim_active_step import (
    AgentNativeActiveStepRefreshRequest,
    refresh_agent_native_claimed_active_step,
)
from loopora.agent_native_claim_events import AgentNativeStepClaimedEventRequest, agent_native_step_claimed_event_payload
from loopora.agent_native_claim_runtime_step import (
    AgentNativeClaimedActiveStepPayloadRequest,
    AgentNativeRuntimeStepViewBuildRequest,
    agent_native_claimed_active_step_payload,
    build_agent_native_runtime_step_view,
)
from loopora.agent_native_parallel_groups import agent_native_parallel_group_started_payload
from loopora.agent_native_result_template import write_agent_native_step_view_files
from loopora.agent_native_runtime_context import agent_native_iteration_state
from loopora.agent_native_state import agent_native_state, write_agent_native_state
from loopora.agent_native_step_view import AgentNativeStepViewRequest, agent_native_step_view
from loopora.engine import RepositoryRunEngine, RunEngineStartIterationRequest
from loopora.engine.runner_context import runner_step_claim_plan, runner_step_claim_request
from loopora.events.projection_cache import current_step_projection_for_run
from loopora.runners import agent_runner_actor
from loopora.service_agent_native_requests import AgentNativeRuntimeClaimRequest, AgentNativeStepClaimRequest
from loopora.service_types import ACTIVE_RUN_STATUSES, LooporaConflictError, TERMINAL_RUN_STATUSES
from loopora.structured_numbers import coerced_non_negative_int


class ServiceAgentNativeClaimMixin:
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
        state = agent_native_state(layout, adapter=kind, run=run)
        entry_source = str(request.entry_source or "").strip() or str(state.get("entry_source") or "").strip()
        if entry_source and state.get("entry_source") != entry_source:
            state["entry_source"] = entry_source
            write_agent_native_state(layout, state)
        active_step_refresh = refresh_agent_native_claimed_active_step(
            AgentNativeActiveStepRefreshRequest(
                run,
                state,
                self._coverage_context_for_run(layout),
                current_step_projection_for_run(self.repository, run["id"]),
            )
        )
        if active_step_refresh.state_changed:
            state["active_step"] = active_step_refresh.active_step
            write_agent_native_state(layout, state)
        if active_step_refresh.step_view is not None:
            step_view = active_step_refresh.step_view
            write_agent_native_step_view_files(step_view)
            return self._with_agent_native_judgment_contract(
                {
                    "adapter": kind,
                    "run": run,
                    "run_path": f"/runs/{run['id']}",
                    "next_step": step_view,
                    "complete": False,
                }
            )

        context = self._agent_native_run_context(run, state)
        iteration = agent_native_iteration_state(state)
        actor = agent_runner_actor(kind)
        plan = runner_step_claim_plan(
            RepositoryRunEngine(self.repository),
            context,
            iteration,
            pending_actor=actor,
            fallback_step_index=coerced_non_negative_int(state.get("step_index")),
        )
        if plan is None:
            return self._agent_native_finish_iteration_or_advance(kind, run, state, context)

        return self._agent_native_claim_runtime_step(
            AgentNativeRuntimeClaimRequest(
                kind=kind,
                run=run,
                state=state,
                context=context,
                iteration=iteration,
                step=plan.step,
                step_order=plan.step_order,
                entry_source=entry_source,
                claim_request=plan.claim_request,
            )
        )

    def _agent_native_claim_runtime_step(
        self,
        request: AgentNativeRuntimeClaimRequest,
    ) -> dict[str, Any]:
        kind = request.kind
        run = request.run
        state = request.state
        context = request.context
        iteration = request.iteration
        step = request.step
        step_order = request.step_order
        role = context.role_by_id[step["role_id"]]
        RepositoryRunEngine(self.repository).start_iteration(
            RunEngineStartIterationRequest(
                run_id=run["id"],
                iteration=iteration.iter_id,
                actor=agent_runner_actor(kind),
                step_count=len(context.strategy_steps),
            )
        )
        execution_settings = self._resolve_role_execution_settings(run, step, role)
        runtime_step = build_agent_native_runtime_step_view(
            AgentNativeRuntimeStepViewBuildRequest(
                kind=kind,
                run=run,
                state=state,
                context=context,
                iteration=iteration,
                step=step,
                step_order=step_order,
                role=role,
                execution_settings=execution_settings,
                entry_source=request.entry_source,
                runtime_role_key=self._runtime_role_key,
                prepare_runner_step_request=self.prepare_runner_step_request,
                step_view_builder=self._agent_native_step_view,
            )
        )
        runtime_role = runtime_step.runtime_role
        step_view = runtime_step.step_view
        run = self.repository.update_run(
            run["id"],
            status="awaiting_agent",
            current_iter=iteration.iter_id,
            active_role=runtime_role,
        )
        claim_request = request.claim_request or runner_step_claim_request(
            context,
            iteration,
            step=step,
            role=role,
            pending_actor=agent_runner_actor(kind),
        )
        RepositoryRunEngine(self.repository).claim_runner_step(claim_request)
        write_agent_native_step_view_files(step_view)
        state["active_step"] = agent_native_claimed_active_step_payload(
            AgentNativeClaimedActiveStepPayloadRequest(
                step_view=step_view,
                step_instruction_context=runtime_step.step_instruction_context,
                execution_settings=execution_settings,
                role=role,
                runtime_role=runtime_role,
                step=step,
                step_order=step_order,
                iter_id=iteration.iter_id,
            )
        )
        write_agent_native_state(context.layout, state)
        self.append_run_event(
            run["id"],
            "agent_native_step_claimed",
            agent_native_step_claimed_event_payload(
                AgentNativeStepClaimedEventRequest(
                    adapter=kind,
                    iter_id=iteration.iter_id,
                    step=step,
                    step_order=step_order,
                    role=role,
                    runtime_role=runtime_role,
                    step_view=step_view,
                )
            ),
            role=runtime_role,
        )
        parallel_started = agent_native_parallel_group_started_payload(context.strategy_steps, iteration.iter_id, step, step_order)
        if parallel_started is not None:
            self.append_run_event(run["id"], "parallel_group_started", parallel_started)
        return self._with_agent_native_judgment_contract(
            {
                "adapter": kind,
                "run": self._hydrate_run_files(run),
                "run_path": f"/runs/{run['id']}",
                "next_step": step_view,
                "complete": False,
            }
        )

    def _agent_native_step_view(  # noqa: PLR0913 - Agent Step View projection needs the frozen step contract inputs.
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
        step_instruction_context: dict[str, Any] | None = None,
        entry_source: str = "",
    ) -> dict[str, Any]:
        return agent_native_step_view(
            AgentNativeStepViewRequest(
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
                step_instruction_context=step_instruction_context,
                entry_source=entry_source,
            )
        )
