from __future__ import annotations

from loopora.events.run_event_payloads import verdict_issued_payload
from loopora.engine.run_requests import RunEngineIssueVerdictRequest
from loopora.events.append_requests import RunEventAppend
from loopora.events.envelope import EventEnvelope
from loopora.events.run_event_commands import append_run_event_and_rebuild_projection_cache


def append_verdict_issue_and_rebuild_projection_cache(
    repository,
    request: RunEngineIssueVerdictRequest,
) -> EventEnvelope:
    return append_run_event_and_rebuild_projection_cache(
        repository,
        RunEventAppend(
            run_id=request.run_id,
            event_type="VerdictIssued",
            actor=request.actor,
            payload=verdict_issued_payload(request.run_id, request.verdict),
            correlation_id=request.correlation_id,
            causation_id=request.causation_id,
        ),
    )
