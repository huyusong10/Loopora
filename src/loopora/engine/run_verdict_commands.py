from __future__ import annotations

from loopora.events.run_event_payloads import verdict_issued_payload
from loopora.engine.run_requests import RunEngineIssueVerdictRequest
from loopora.events.append_requests import RunEventAppend
from loopora.events.envelope import EventEnvelope
from loopora.events.run_event_commands import append_run_event_and_rebuild_projection_cache
from loopora.events.streams import run_stream_id


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
            causation_id=request.causation_id or _latest_coverage_event_id(repository, request.run_id),
        ),
    )


def _latest_coverage_event_id(repository, run_id: str) -> str | None:
    events = repository.list_domain_events(run_stream_id(run_id))
    for event in reversed(events):
        if event.event_type == "CoverageRecomputed":
            return event.event_id
    return None
