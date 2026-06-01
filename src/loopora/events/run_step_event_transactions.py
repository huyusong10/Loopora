from __future__ import annotations

from dataclasses import replace

from loopora.events.append_requests import RunEventAppend, run_event_append_request
from loopora.events.projection_cache import rebuild_run_projection_cache
from loopora.events.run_artifact_index import step_result_artifact_index_entries
from loopora.events.run_event_payloads import strategy_advanced_payload
from loopora.events.run_event_results import StepClaimEventsResult, StepSubmissionEventsResult
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
    strategy_event = event_transaction.append_domain_event(
        replace(
            committed_request,
            event_type="StrategyAdvanced",
            payload=strategy_advanced_payload(result),
            correlation_id=committed_request.correlation_id or committed_event.correlation_id,
            causation_id=committed_event.event_id,
        )
    )
    return StepSubmissionEventsResult(
        submitted_event=submitted_event,
        accepted_event=accepted_event,
        committed_event=committed_event,
        strategy_event=strategy_event,
    )


def append_step_claim_events(
    event_transaction: DomainEventTransaction,
    *,
    planned_request: DomainEventAppendRequest,
    claimed_request: DomainEventAppendRequest,
    instruction_request: DomainEventAppendRequest,
) -> StepClaimEventsResult:
    planned_event = event_transaction.append_domain_event(planned_request)
    claimed_event = event_transaction.append_domain_event(
        replace(
            claimed_request,
            correlation_id=claimed_request.correlation_id or planned_event.correlation_id,
            causation_id=planned_event.event_id,
        )
    )
    instruction_event = event_transaction.append_domain_event(
        replace(
            instruction_request,
            correlation_id=instruction_request.correlation_id or claimed_event.correlation_id,
            causation_id=claimed_event.event_id,
        )
    )
    return StepClaimEventsResult(
        planned_event=planned_event,
        claimed_event=claimed_event,
        instruction_event=instruction_event,
    )


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


def append_step_claim_events_and_rebuild_projection_cache(
    repository,
    *,
    run_id: str,
    planned_request: RunEventAppend,
    claimed_request: RunEventAppend,
    instruction_request: RunEventAppend,
) -> StepClaimEventsResult:
    append_result = repository.append_domain_event_transaction(
        lambda event_transaction: append_step_claim_events(
            event_transaction,
            planned_request=run_event_append_request(planned_request),
            claimed_request=run_event_append_request(claimed_request),
            instruction_request=run_event_append_request(instruction_request),
        )
    )
    rebuild_run_projection_cache(repository, run_id)
    return append_result
