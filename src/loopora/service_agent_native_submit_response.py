from __future__ import annotations

from typing import Any

from loopora.agent_native_coverage_summary import coverage_gap_summaries, required_coverage_summary
from loopora.agent_native_state import write_agent_native_state
from loopora.agent_native_submitted_step import (
    AgentNativeSubmittedStepResultRequest,
    agent_native_submitted_step_result,
)
from loopora.evidence_coverage import load_or_build_evidence_coverage_projection
from loopora.service_agent_native_requests import AgentNativeStepClaimRequest, AgentNativeSubmitResponseRequest
from loopora.structured_numbers import structured_non_negative_int


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
