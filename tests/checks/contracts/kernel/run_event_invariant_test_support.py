from __future__ import annotations

from typing import Any

from loopora.db import LooporaRepository
from loopora.events.store import DomainEventAppendRequest


def _run_event_request(
    stream_id: str,
    run_id: str,
    *,
    event_type: str,
    payload: dict[str, Any],
    causation_id: str | None = None,
):
    event_payload = {"run_id": run_id}
    event_payload.update(payload)
    return DomainEventAppendRequest(
        stream_id=stream_id,
        aggregate_type="run",
        aggregate_id=run_id,
        event_type=event_type,
        payload=event_payload,
        causation_id=causation_id,
    )


def append_run_created(
    repository: LooporaRepository,
    stream_id: str,
    run_id: str,
    *,
    loop_id: str = "loop_verdict_evidence_ref_boundary",
) -> None:
    repository.append_domain_event(_run_event_request(stream_id, run_id, event_type="RunCreated", payload={"loop_id": loop_id}))


def append_accepted_evidence(
    repository: LooporaRepository,
    stream_id: str,
    run_id: str,
    *,
    evidence_id: str,
    verifies: list[str] | None = None,
):
    return repository.append_domain_event(
        _run_event_request(
            stream_id,
            run_id,
            event_type="EvidenceAccepted",
            payload={
                "evidence_id": evidence_id,
                "verifies": verifies or ["target:done_when.proof:covered"],
            },
        )
    )


def append_covered_coverage(repository: LooporaRepository, stream_id: str, run_id: str, *, causation_id: str):
    return append_coverage_recomputed(
        repository,
        stream_id,
        run_id,
        payload={"status": "covered", "target_count": 1, "covered_target_count": 1},
        causation_id=causation_id,
    )


def append_coverage_recomputed(
    repository: LooporaRepository,
    stream_id: str,
    run_id: str,
    *,
    payload: dict[str, Any],
    causation_id: str | None = None,
):
    return repository.append_domain_event(
        _run_event_request(
            stream_id,
            run_id,
            event_type="CoverageRecomputed",
            payload=payload,
            causation_id=causation_id,
        )
    )


def append_verdict_issued(
    repository: LooporaRepository,
    stream_id: str,
    run_id: str,
    *,
    payload: dict[str, Any],
    causation_id: str | None = None,
):
    return repository.append_domain_event(
        _run_event_request(
            stream_id,
            run_id,
            event_type="VerdictIssued",
            payload=payload,
            causation_id=causation_id,
        )
    )


def append_run_closed(
    repository: LooporaRepository,
    stream_id: str,
    run_id: str,
    *,
    payload: dict[str, Any] | None = None,
    causation_id: str | None = None,
):
    event_payload = {"status": "succeeded"}
    event_payload.update(payload or {})
    return repository.append_domain_event(
        _run_event_request(
            stream_id,
            run_id,
            event_type="RunClosed",
            payload=event_payload,
            causation_id=causation_id,
        )
    )


def append_residual_risk_verdict(repository: LooporaRepository, stream_id: str, run_id: str):
    evidence_event = append_accepted_evidence(
        repository,
        stream_id,
        run_id,
        evidence_id="ev_accept_risk",
    )
    coverage_event = append_covered_coverage(
        repository,
        stream_id,
        run_id,
        causation_id=evidence_event.event_id,
    )
    return append_verdict_issued(
        repository,
        stream_id,
        run_id,
        payload={"status": "passed_with_residual_risk", "buckets": {"residual_risk": managed_residual_risk()}},
        causation_id=coverage_event.event_id,
    )


def append_verdict_allowed_closure(
    repository: LooporaRepository,
    stream_id: str,
    run_id: str,
    *,
    causation_id: str,
):
    return repository.append_domain_event(
        _run_event_request(
            stream_id,
            run_id,
            event_type="VerdictAllowedClosure",
            payload={"verdict_status": "passed_with_residual_risk", "allowed": True},
            causation_id=causation_id,
        )
    )


def append_residual_risk_accepted(
    repository: LooporaRepository,
    stream_id: str,
    run_id: str,
    *,
    causation_id: str,
):
    return repository.append_domain_event(
        _run_event_request(
            stream_id,
            run_id,
            event_type="ResidualRiskAccepted",
            payload={"risk_count": 1, "residual_risk": managed_residual_risk()},
            causation_id=causation_id,
        )
    )


def managed_residual_risk() -> list[dict[str, object]]:
    return [{"label": "Manual review remains.", "managed": True}]
