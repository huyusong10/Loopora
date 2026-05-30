from __future__ import annotations

from dataclasses import replace

from loopora.engine.run_artifact_index import step_result_artifact_index_entries
from loopora.engine.run_requests import RunEngineRecordStepEvidenceResult, RunEngineSubmitStepResult
from loopora.events.store import DomainEventAppendRequest, DomainEventTransaction
from loopora.kernel import StepResult


def append_step_submission_events(
    event_transaction: DomainEventTransaction,
    result: StepResult,
    *,
    loop_id: str,
    submitted_request: DomainEventAppendRequest,
    committed_request: DomainEventAppendRequest,
) -> RunEngineSubmitStepResult:
    submitted_event = event_transaction.append_domain_event(submitted_request)
    for artifact_entry in step_result_artifact_index_entries(
        result,
        loop_id=loop_id,
        created_by_event_id=submitted_event.event_id,
    ):
        event_transaction.record_artifact_index(artifact_entry)
    committed_event = event_transaction.append_domain_event(
        replace(
            committed_request,
            correlation_id=committed_request.correlation_id or submitted_event.correlation_id,
            causation_id=submitted_event.event_id,
        )
    )
    return RunEngineSubmitStepResult(submitted_event=submitted_event, committed_event=committed_event)


def append_step_evidence_events(
    event_transaction: DomainEventTransaction,
    evidence_request: DomainEventAppendRequest,
    coverage_request: DomainEventAppendRequest,
) -> RunEngineRecordStepEvidenceResult:
    evidence_event = event_transaction.append_domain_event(evidence_request)
    coverage_event = event_transaction.append_domain_event(
        replace(
            coverage_request,
            correlation_id=coverage_request.correlation_id or evidence_event.correlation_id,
            causation_id=evidence_event.event_id,
        )
    )
    return RunEngineRecordStepEvidenceResult(evidence_event=evidence_event, coverage_event=coverage_event)
