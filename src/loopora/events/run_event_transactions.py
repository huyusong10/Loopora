from __future__ import annotations

from dataclasses import replace

from loopora.events.append_requests import RunEventAppend, run_event_append_request
from loopora.events.envelope import EventEnvelope
from loopora.events.projection_cache import rebuild_run_projection_cache
from loopora.events.run_artifact_index import evidence_artifact_index_entries, step_result_artifact_index_entries
from loopora.events.run_event_results import StepEvidenceEventsResult, StepSubmissionEventsResult
from loopora.events.store import DomainEventAppendRequest, DomainEventTransaction
from loopora.kernel import StepResult


def append_step_submission_events(
    event_transaction: DomainEventTransaction,
    result: StepResult,
    *,
    loop_id: str,
    submitted_request: DomainEventAppendRequest,
    committed_request: DomainEventAppendRequest,
) -> StepSubmissionEventsResult:
    submitted_event = event_transaction.append_domain_event(submitted_request)
    for artifact_entry in step_result_artifact_index_entries(
        result,
        loop_id=loop_id,
        created_by_event_id=submitted_event.event_id,
    ):
        event_transaction.record_artifact_index(artifact_entry)
    accepted_event = event_transaction.append_domain_event(
        replace(
            committed_request,
            event_type="StepAccepted",
            correlation_id=committed_request.correlation_id or submitted_event.correlation_id,
            causation_id=submitted_event.event_id,
        )
    )
    committed_event = event_transaction.append_domain_event(
        replace(
            committed_request,
            correlation_id=committed_request.correlation_id or accepted_event.correlation_id,
            causation_id=accepted_event.event_id,
        )
    )
    return StepSubmissionEventsResult(
        submitted_event=submitted_event,
        accepted_event=accepted_event,
        committed_event=committed_event,
    )


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


def append_step_submission_events_and_rebuild_projection_cache(
    repository,
    result: StepResult,
    *,
    loop_id: str,
    submitted_request: RunEventAppend,
    committed_request: RunEventAppend,
) -> StepSubmissionEventsResult:
    append_result = repository.append_domain_event_transaction(
        lambda event_transaction: append_step_submission_events(
            event_transaction,
            result,
            loop_id=loop_id,
            submitted_request=run_event_append_request(submitted_request),
            committed_request=run_event_append_request(committed_request),
        )
    )
    rebuild_run_projection_cache(repository, result.run_id)
    return append_result


def append_step_evidence_events(
    event_transaction: DomainEventTransaction,
    evidence_request: DomainEventAppendRequest,
    coverage_request: DomainEventAppendRequest,
) -> StepEvidenceEventsResult:
    evidence_event = append_evidence_acceptance_event(event_transaction, evidence_request)
    coverage_event = event_transaction.append_domain_event(
        replace(
            coverage_request,
            correlation_id=coverage_request.correlation_id or evidence_event.correlation_id,
            causation_id=evidence_event.event_id,
        )
    )
    return StepEvidenceEventsResult(evidence_event=evidence_event, coverage_event=coverage_event)


def append_step_evidence_events_and_rebuild_projection_cache(
    repository,
    *,
    run_id: str,
    evidence_request: RunEventAppend,
    coverage_request: RunEventAppend,
) -> StepEvidenceEventsResult:
    append_result = repository.append_domain_event_transaction(
        lambda event_transaction: append_step_evidence_events(
            event_transaction,
            run_event_append_request(evidence_request),
            run_event_append_request(coverage_request),
        )
    )
    rebuild_run_projection_cache(repository, run_id)
    return append_result
