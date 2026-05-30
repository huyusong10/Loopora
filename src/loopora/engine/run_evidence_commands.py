from __future__ import annotations

from loopora.events.run_event_payloads import coverage_recomputed_payload, evidence_accepted_payload
from loopora.engine.run_requests import (
    RunEngineAcceptEvidenceRequest,
    RunEngineCoverageRecomputedRequest,
    RunEngineRecordStepEvidenceRequest,
    RunEngineRecordStepEvidenceResult,
)
from loopora.events.append_requests import RunEventAppend
from loopora.events.envelope import EventEnvelope
from loopora.events.run_event_commands import append_run_event_and_rebuild_projection_cache
from loopora.events.run_event_transactions import append_step_evidence_events_and_rebuild_projection_cache


def append_evidence_acceptance_and_rebuild_projection_cache(
    repository,
    request: RunEngineAcceptEvidenceRequest,
) -> EventEnvelope:
    return append_run_event_and_rebuild_projection_cache(
        repository,
        RunEventAppend(
            run_id=request.run_id,
            event_type="EvidenceAccepted",
            actor=request.actor,
            payload=evidence_accepted_payload(request.run_id, request.evidence_entry),
            correlation_id=request.correlation_id,
            causation_id=request.causation_id,
        ),
    )


def append_coverage_recompute_and_rebuild_projection_cache(
    repository,
    request: RunEngineCoverageRecomputedRequest,
) -> EventEnvelope:
    return append_run_event_and_rebuild_projection_cache(
        repository,
        RunEventAppend(
            run_id=request.run_id,
            event_type="CoverageRecomputed",
            actor=request.actor,
            payload=coverage_recomputed_payload(request.run_id, request.coverage_projection),
            correlation_id=request.correlation_id,
            causation_id=request.causation_id,
        ),
    )


def append_step_evidence_and_rebuild_projection_cache(
    repository,
    request: RunEngineRecordStepEvidenceRequest,
) -> RunEngineRecordStepEvidenceResult:
    return append_step_evidence_events_and_rebuild_projection_cache(
        repository,
        run_id=request.run_id,
        evidence_request=RunEventAppend(
            run_id=request.run_id,
            event_type="EvidenceAccepted",
            actor=request.actor,
            payload=evidence_accepted_payload(request.run_id, request.evidence_entry),
            correlation_id=request.correlation_id,
            causation_id=request.causation_id,
        ),
        coverage_request=RunEventAppend(
            run_id=request.run_id,
            event_type="CoverageRecomputed",
            actor=request.actor,
            payload=coverage_recomputed_payload(request.run_id, request.coverage_projection),
            correlation_id=request.correlation_id,
            causation_id=None,
        ),
    )
