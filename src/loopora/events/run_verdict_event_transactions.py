from __future__ import annotations

from dataclasses import dataclass, replace

from loopora.events.append_requests import RunEventAppend, run_event_append_request
from loopora.events.projection_cache import rebuild_run_projection_cache
from loopora.events.run_event_results import VerdictEventsResult
from loopora.events.store import DomainEventAppendRequest, DomainEventTransaction


@dataclass(frozen=True, slots=True)
class VerdictEventAppendRequest:
    run_id: str
    requested_request: RunEventAppend
    issued_request: RunEventAppend
    closure_request: RunEventAppend
    residual_risk_request: RunEventAppend | None = None
    next_gap_request: RunEventAppend | None = None


@dataclass(frozen=True, slots=True)
class _DomainVerdictEventAppendRequest:
    requested_request: DomainEventAppendRequest
    issued_request: DomainEventAppendRequest
    closure_request: DomainEventAppendRequest
    residual_risk_request: DomainEventAppendRequest | None = None
    next_gap_request: DomainEventAppendRequest | None = None


def append_verdict_events(
    event_transaction: DomainEventTransaction,
    request: _DomainVerdictEventAppendRequest,
) -> VerdictEventsResult:
    requested_event = event_transaction.append_domain_event(request.requested_request)
    issued_event = event_transaction.append_domain_event(
        replace(
            request.issued_request,
            correlation_id=request.issued_request.correlation_id or requested_event.correlation_id,
            causation_id=requested_event.event_id,
        )
    )
    closure_event = event_transaction.append_domain_event(
        replace(
            request.closure_request,
            correlation_id=request.closure_request.correlation_id or issued_event.correlation_id,
            causation_id=issued_event.event_id,
        )
    )
    residual_risk_event = None
    if request.residual_risk_request is not None:
        residual_risk_event = event_transaction.append_domain_event(
            replace(
                request.residual_risk_request,
                correlation_id=request.residual_risk_request.correlation_id or closure_event.correlation_id,
                causation_id=closure_event.event_id,
            )
        )
    next_gap_event = None
    if request.next_gap_request is not None:
        next_gap_event = event_transaction.append_domain_event(
            replace(
                request.next_gap_request,
                correlation_id=request.next_gap_request.correlation_id or closure_event.correlation_id,
                causation_id=closure_event.event_id,
            )
        )
    return VerdictEventsResult(
        requested_event=requested_event,
        issued_event=issued_event,
        closure_event=closure_event,
        residual_risk_event=residual_risk_event,
        next_gap_event=next_gap_event,
    )


def append_verdict_events_and_rebuild_projection_cache(
    repository,
    request: VerdictEventAppendRequest,
) -> VerdictEventsResult:
    append_result = repository.append_domain_event_transaction(
        lambda event_transaction: append_verdict_events(
            event_transaction,
            _DomainVerdictEventAppendRequest(
                requested_request=run_event_append_request(request.requested_request),
                issued_request=run_event_append_request(request.issued_request),
                closure_request=run_event_append_request(request.closure_request),
                residual_risk_request=run_event_append_request(request.residual_risk_request)
                if request.residual_risk_request is not None
                else None,
                next_gap_request=run_event_append_request(request.next_gap_request)
                if request.next_gap_request is not None
                else None,
            ),
        )
    )
    rebuild_run_projection_cache(repository, request.run_id)
    return append_result
