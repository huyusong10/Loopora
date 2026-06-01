from __future__ import annotations

from loopora.events.run_event_payloads import (
    next_gap_selected_payload,
    residual_risk_accepted_payload,
    verdict_closure_payload,
    verdict_issued_payload,
    verdict_requested_payload,
)
from loopora.engine.run_requests import RunEngineIssueVerdictRequest, RunEngineIssueVerdictResult
from loopora.events.append_requests import RunEventAppend
from loopora.events.run_verdict_event_transactions import (
    VerdictEventAppendRequest,
    append_verdict_events_and_rebuild_projection_cache,
)
from loopora.events.streams import run_stream_id


def append_verdict_issue_and_rebuild_projection_cache(
    repository,
    request: RunEngineIssueVerdictRequest,
) -> RunEngineIssueVerdictResult:
    issued_payload = verdict_issued_payload(request.run_id, request.verdict)
    return append_verdict_events_and_rebuild_projection_cache(
        repository,
        VerdictEventAppendRequest(
            run_id=request.run_id,
            requested_request=RunEventAppend(
                run_id=request.run_id,
                event_type="VerdictRequested",
                actor=request.actor,
                payload=verdict_requested_payload(request.run_id, request.verdict),
                correlation_id=request.correlation_id,
                causation_id=request.causation_id or _latest_coverage_event_id(repository, request.run_id),
            ),
            issued_request=RunEventAppend(
                run_id=request.run_id,
                event_type="VerdictIssued",
                actor=request.actor,
                payload=issued_payload,
                correlation_id=request.correlation_id,
                causation_id=None,
            ),
            closure_request=RunEventAppend(
                run_id=request.run_id,
                event_type="VerdictAllowedClosure" if issued_payload["status"] in {"passed", "passed_with_residual_risk"} else "VerdictBlockedClosure",
                actor=request.actor,
                payload=verdict_closure_payload(request.run_id, issued_payload),
                correlation_id=request.correlation_id,
                causation_id=None,
            ),
            residual_risk_request=_residual_risk_accepted_request(
                request,
                issued_payload,
            ),
            next_gap_request=_next_gap_selected_request(
                request,
                issued_payload,
            ),
        ),
    )


def _latest_coverage_event_id(repository, run_id: str) -> str | None:
    events = repository.list_domain_events(run_stream_id(run_id))
    for event in reversed(events):
        if event.event_type == "CoverageRecomputed":
            return event.event_id
    return None


def _next_gap_selected_request(
    request: RunEngineIssueVerdictRequest,
    issued_payload: dict,
) -> RunEventAppend | None:
    next_gap = issued_payload.get("next_gap")
    if issued_payload.get("status") in {"passed", "passed_with_residual_risk"} or not isinstance(next_gap, list) or not next_gap:
        return None
    return RunEventAppend(
        run_id=request.run_id,
        event_type="NextGapSelected",
        actor=request.actor,
        payload=next_gap_selected_payload(request.run_id, issued_payload),
        correlation_id=request.correlation_id,
        causation_id=None,
    )


def _residual_risk_accepted_request(
    request: RunEngineIssueVerdictRequest,
    issued_payload: dict,
) -> RunEventAppend | None:
    if issued_payload.get("status") != "passed_with_residual_risk":
        return None
    return RunEventAppend(
        run_id=request.run_id,
        event_type="ResidualRiskAccepted",
        actor=request.actor,
        payload=residual_risk_accepted_payload(request.run_id, issued_payload),
        correlation_id=request.correlation_id,
        causation_id=None,
    )
