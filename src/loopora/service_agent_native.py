from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.agent_adapters import normalize_agent_adapter_kind, read_agent_binding
from loopora.agent_native_runtime_context import agent_native_run_context
from loopora.agent_native_state import (
    agent_native_state,
    write_agent_native_state,
)
from loopora.agent_native_task_proof import with_agent_native_judgment_contract
from loopora.engine.runner_context import RunnerRunContext
from loopora.service_agent_native_claim import ServiceAgentNativeClaimMixin
from loopora.service_agent_native_requests import (
    AgentNativeStepClaimRequest,
    AgentNativeStepSubmitRequest,
)
from loopora.service_agent_native_iteration import ServiceAgentNativeIterationMixin
from loopora.service_agent_native_submit import ServiceAgentNativeSubmitMixin
from loopora.service_types import ACTIVE_RUN_STATUSES, LooporaConflictError, LooporaError, LooporaNotFoundError, TERMINAL_RUN_STATUSES
from loopora.utils import utc_now


class ServiceAgentNativeMixin(ServiceAgentNativeClaimMixin, ServiceAgentNativeIterationMixin, ServiceAgentNativeSubmitMixin):
    @staticmethod
    def _with_agent_native_judgment_contract(result: dict[str, Any]) -> dict[str, Any]:
        return with_agent_native_judgment_contract(result)

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
        state = agent_native_state(layout, adapter=kind, run=run)
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
        write_agent_native_state(layout, state)
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

    def submit_agent_native_step(self, request: AgentNativeStepSubmitRequest) -> dict[str, Any]:
        return self._submit_agent_native_step_impl(request)

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

    def _agent_native_run_context(self, run: dict, state: dict[str, Any]) -> RunnerRunContext:
        layout = self._run_artifact_layout(Path(run["runs_dir"]))
        return agent_native_run_context(
            run,
            state,
            layout=layout,
            executor=self.executor_factory(),
            prompt_files=self._read_prompt_files_for_run(run),
        )
