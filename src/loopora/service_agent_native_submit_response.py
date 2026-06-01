from __future__ import annotations

from typing import Any

from loopora.agent_native_state import write_agent_native_state
from loopora.agent_native_submitted_step import (
    AgentNativeSubmittedStepResultRequest,
    agent_native_submitted_step_result,
)
from loopora.service_agent_native_requests import AgentNativeStepClaimRequest, AgentNativeSubmitResponseRequest


class ServiceAgentNativeSubmitResponseMixin:
    def _agent_native_submit_response(self, request: AgentNativeSubmitResponseRequest) -> dict[str, Any]:
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

    @staticmethod
    def _agent_native_submitted_step_result(request: AgentNativeSubmittedStepResultRequest) -> dict[str, Any]:
        return agent_native_submitted_step_result(request)
