from __future__ import annotations

from dataclasses import dataclass, replace

from loopora.events.append_requests import RunEventAppend, run_event_append_request
from loopora.events.envelope import EventEnvelope
from loopora.events.projection_cache import rebuild_run_projection_cache
from loopora.events.run_artifact_index import evidence_artifact_index_entries
from loopora.events.run_event_results import StepEvidenceEventsResult
from loopora.events.store import DomainEventAppendRequest, DomainEventTransaction


@dataclass(frozen=True, slots=True)
class StepEvidenceEventAppendRequest:
    run_id: str
    submitted_request: RunEventAppend
    evidence_request: RunEventAppend
    coverage_request: RunEventAppend
    linked_request: RunEventAppend | None = None


def append_evidence_acceptance_event(
    event_transaction: DomainEventTransaction,
    evidence_request: DomainEventAppendRequest,
) -> EventEnvelope:
    evidence_event = event_transaction.append_domain_event(evidence_request)
    for artifact_entry in evidence_artifact_index_entries(
        evidence_event.payload,
        created_by_event_id=evidence_event.event_id,
    ):
        event_transaction.record_artifact_index(artifact_entry)
    return evidence_event


def append_evidence_acceptance_event_and_rebuild_projection_cache(
    repository,
    *,
    run_id: str,
    evidence_request: RunEventAppend,
) -> EventEnvelope:
    evidence_event = repository.append_domain_event_transaction(
        lambda event_transaction: append_evidence_acceptance_event(
            event_transaction,
            run_event_append_request(evidence_request),
        )
    )
    rebuild_run_projection_cache(repository, run_id)
    return evidence_event


def append_step_evidence_events(
    event_transaction: DomainEventTransaction,
    submitted_request: DomainEventAppendRequest,
    evidence_request: DomainEventAppendRequest,
    linked_request: DomainEventAppendRequest | None,
    coverage_request: DomainEventAppendRequest,
) -> StepEvidenceEventsResult:
    submitted_event = event_transaction.append_domain_event(submitted_request)
    evidence_event = append_evidence_acceptance_event(
        event_transaction,
        replace(
            evidence_request,
            correlation_id=evidence_request.correlation_id or submitted_event.correlation_id,
            causation_id=submitted_event.event_id,
        ),
    )
    linked_event = None
    coverage_causation_id = evidence_event.event_id
    if linked_request is not None:
        linked_event = event_transaction.append_domain_event(
            replace(
                linked_request,
                correlation_id=linked_request.correlation_id or evidence_event.correlation_id,
                causation_id=evidence_event.event_id,
            )
        )
        coverage_causation_id = linked_event.event_id
    coverage_event = event_transaction.append_domain_event(
        replace(
            coverage_request,
            correlation_id=coverage_request.correlation_id or evidence_event.correlation_id,
            causation_id=coverage_causation_id,
        )
    )
    return StepEvidenceEventsResult(
        submitted_event=submitted_event,
        evidence_event=evidence_event,
        linked_event=linked_event,
        coverage_event=coverage_event,
    )


def append_step_evidence_events_and_rebuild_projection_cache(
    repository,
    request: StepEvidenceEventAppendRequest,
) -> StepEvidenceEventsResult:
    append_result = repository.append_domain_event_transaction(
        lambda event_transaction: append_step_evidence_events(
            event_transaction,
            run_event_append_request(request.submitted_request),
            run_event_append_request(request.evidence_request),
            run_event_append_request(request.linked_request) if request.linked_request is not None else None,
            run_event_append_request(request.coverage_request),
        )
    )
    rebuild_run_projection_cache(repository, request.run_id)
    return append_result
