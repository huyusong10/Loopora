from __future__ import annotations

from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.events import run_stream_id
from loopora.events.store import DomainEventAppendRequest


def test_domain_event_store_rejects_run_closed_causation_without_passing_verdict(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_closed_verdict_boundary"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id, loop_id="loop_closed_verdict_boundary")

    partial_coverage_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="CoverageRecomputed",
            payload={"run_id": run_id, "status": "partial", "target_count": 1, "missing_target_count": 1},
        )
    )
    nonpassing_verdict = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="VerdictIssued",
            payload={"run_id": run_id, "status": "continue_required"},
            causation_id=partial_coverage_event.event_id,
        )
    )
    with pytest.raises(ValueError, match="passing VerdictIssued"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="RunClosed",
                payload={"run_id": run_id, "status": "succeeded"},
                causation_id=nonpassing_verdict.event_id,
            )
        )

    evidence_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="EvidenceAccepted",
            payload={"run_id": run_id, "evidence_id": "ev_closed", "verifies": ["target:done_when.proof:covered"]},
        )
    )
    passable_coverage_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="CoverageRecomputed",
            payload={"run_id": run_id, "status": "covered", "target_count": 1, "covered_target_count": 1},
            causation_id=evidence_event.event_id,
        )
    )
    passing_verdict = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="VerdictIssued",
            payload={"run_id": run_id, "status": "passed"},
            causation_id=passable_coverage_event.event_id,
        )
    )
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="RunClosed",
            payload={"run_id": run_id, "status": "succeeded"},
            causation_id=passing_verdict.event_id,
        )
    )

    assert [event.event_type for event in repository.list_domain_events(stream_id)][-3:] == [
        "CoverageRecomputed",
        "VerdictIssued",
        "RunClosed",
    ]


def test_domain_event_store_rejects_nonlegacy_run_closed_without_task_proof_causation(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_closed_missing_causation_boundary"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id, loop_id="loop_closed_missing_causation_boundary")

    with pytest.raises(ValueError, match="latest passing VerdictIssued"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="RunClosed",
                payload={"run_id": run_id, "status": "succeeded"},
            )
        )


def test_domain_event_store_allows_explicit_legacy_run_closed_without_task_proof_causation(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_closed_legacy_causation_boundary"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id, loop_id="loop_closed_legacy_causation_boundary")

    closed_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="RunClosed",
            payload={"run_id": run_id, "status": "succeeded", "legacy_compat": True},
        )
    )

    assert closed_event.causation_id is None
    assert closed_event.payload["legacy_compat"] is True


def test_residual_risk_accepted_requires_allowed_closure_causation(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_residual_risk_acceptance_boundary"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id, loop_id="loop_residual_risk_acceptance_boundary")
    verdict_event = _append_residual_risk_verdict(repository, stream_id, run_id)

    with pytest.raises(ValueError, match="requires prior VerdictAllowedClosure"):
        _append_residual_risk_accepted(repository, stream_id, run_id, causation_id=verdict_event.event_id)

    closure_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="VerdictAllowedClosure",
            payload={"run_id": run_id, "verdict_status": "passed_with_residual_risk", "allowed": True},
            causation_id=verdict_event.event_id,
        )
    )
    residual_event = _append_residual_risk_accepted(
        repository,
        stream_id,
        run_id,
        causation_id=closure_event.event_id,
    )

    assert residual_event.payload["risk_count"] == 1
    with pytest.raises(ValueError, match="already accepted residual risk"):
        _append_residual_risk_accepted(repository, stream_id, run_id, causation_id=closure_event.event_id)


def _append_run_created(repository: LooporaRepository, stream_id: str, run_id: str, *, loop_id: str) -> None:
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="RunCreated",
            payload={"run_id": run_id, "loop_id": loop_id},
        )
    )


def _append_residual_risk_verdict(repository: LooporaRepository, stream_id: str, run_id: str):
    evidence_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="EvidenceAccepted",
            payload={
                "run_id": run_id,
                "evidence_id": "ev_accept_risk",
                "verifies": ["target:done_when.proof:covered"],
            },
        )
    )
    coverage_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="CoverageRecomputed",
            payload={"run_id": run_id, "status": "covered", "target_count": 1, "covered_target_count": 1},
            causation_id=evidence_event.event_id,
        )
    )

    return repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="VerdictIssued",
            payload={
                "run_id": run_id,
                "status": "passed_with_residual_risk",
                "buckets": {"residual_risk": _managed_residual_risk()},
            },
            causation_id=coverage_event.event_id,
        )
    )


def _append_residual_risk_accepted(
    repository: LooporaRepository,
    stream_id: str,
    run_id: str,
    *,
    causation_id: str,
):
    return repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="ResidualRiskAccepted",
            payload={"run_id": run_id, "risk_count": 1, "residual_risk": _managed_residual_risk()},
            causation_id=causation_id,
        )
    )


def _managed_residual_risk() -> list[dict[str, object]]:
    return [{"label": "Manual review remains.", "managed": True}]
