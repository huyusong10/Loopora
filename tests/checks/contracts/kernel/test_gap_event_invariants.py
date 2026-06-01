from __future__ import annotations

from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.events import run_stream_id
from loopora.events.store import DomainEventAppendRequest


def test_partial_coverage_requires_weak_or_missing_target_count(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_partial_coverage_count_boundary"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id)

    with pytest.raises(ValueError, match="partial CoverageRecomputed requires weak or missing targets"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="CoverageRecomputed",
                payload={
                    "run_id": run_id,
                    "status": "partial",
                    "target_count": 1,
                    "covered_target_count": 1,
                },
            )
        )
    with pytest.raises(ValueError, match="partial CoverageRecomputed cannot include blocked targets"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="CoverageRecomputed",
                payload={
                    "run_id": run_id,
                    "status": "partial",
                    "target_count": 1,
                    "blocked_target_count": 1,
                },
            )
        )


def test_blocked_coverage_top_gap_requires_blocked_status(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_blocked_coverage_gap_status_boundary"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id)

    with pytest.raises(ValueError, match="blocked CoverageRecomputed top_gaps require blocked status"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="CoverageRecomputed",
                payload={
                    "run_id": run_id,
                    "status": "partial",
                    "target_count": 1,
                    "missing_target_count": 1,
                    "top_gaps": [{"target_id": "done_when.proof", "status": "blocked"}],
                },
            )
        )

    coverage_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="CoverageRecomputed",
            payload={
                "run_id": run_id,
                "status": "blocked",
                "target_count": 1,
                "blocked_target_count": 1,
                "top_gaps": [{"target_id": "done_when.proof", "status": "blocked"}],
            },
        )
    )

    assert coverage_event.payload["status"] == "blocked"


def test_blocked_verdict_next_gap_requires_blocked_status(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_blocked_verdict_gap_status_boundary"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id)

    with pytest.raises(ValueError, match="blocked VerdictIssued next_gap requires blocked status"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="VerdictIssued",
                payload={
                    "run_id": run_id,
                    "status": "continue_required",
                    "next_gap": [{"target_id": "done_when.proof", "status": "blocked"}],
                },
            )
        )

    verdict_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="VerdictIssued",
            payload={
                "run_id": run_id,
                "status": "blocked",
                "next_gap": [{"target_id": "done_when.proof", "status": "blocked"}],
            },
        )
    )

    assert verdict_event.payload["status"] == "blocked"


def test_passed_with_residual_risk_verdict_cannot_select_next_gap(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_residual_risk_next_gap_boundary"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id)
    evidence_event = _append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_residual_risk_gap")
    coverage_event = _append_covered_coverage(repository, stream_id, run_id, causation_id=evidence_event.event_id)

    with pytest.raises(ValueError, match="passing VerdictIssued cannot include unresolved next_gap"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="VerdictIssued",
                payload={
                    "run_id": run_id,
                    "status": "passed_with_residual_risk",
                    "buckets": {"residual_risk": [{"label": "Manual follow-up remains.", "managed": True}]},
                    "next_gap": [{"target_id": "done_when.follow_up", "status": "weak"}],
                },
                causation_id=coverage_event.event_id,
            )
        )


def test_next_gap_selected_requires_blocked_closure_causation(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_next_gap_selected_boundary"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id)
    verdict_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="VerdictIssued",
            payload={
                "run_id": run_id,
                "status": "continue_required",
                "next_gap": [{"target_id": "done_when.proof", "status": "missing"}],
            },
        )
    )
    closure_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="VerdictBlockedClosure",
            payload={"run_id": run_id, "verdict_status": "continue_required", "allowed": False},
            causation_id=verdict_event.event_id,
        )
    )

    with pytest.raises(ValueError, match="causation_id to reference latest VerdictBlockedClosure"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="NextGapSelected",
                payload={
                    "run_id": run_id,
                    "target_id": "done_when.proof",
                    "status": "missing",
                    "next_gap": [{"target_id": "done_when.proof", "status": "missing"}],
                },
                causation_id=verdict_event.event_id,
            )
        )

    selected_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="NextGapSelected",
            payload={
                "run_id": run_id,
                "target_id": "done_when.proof",
                "status": "missing",
                "next_gap": [{"target_id": "done_when.proof", "status": "missing"}],
            },
            causation_id=closure_event.event_id,
        )
    )

    assert selected_event.payload["target_id"] == "done_when.proof"


def _append_run_created(repository: LooporaRepository, stream_id: str, run_id: str) -> None:
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="RunCreated",
            payload={"run_id": run_id, "loop_id": "loop_gap_event_invariants"},
        )
    )


def _append_accepted_evidence(
    repository: LooporaRepository,
    stream_id: str,
    run_id: str,
    *,
    evidence_id: str,
):
    return repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="EvidenceAccepted",
            payload={
                "run_id": run_id,
                "evidence_id": evidence_id,
                "verifies": ["target:done_when.proof:covered"],
            },
        )
    )


def _append_covered_coverage(repository: LooporaRepository, stream_id: str, run_id: str, *, causation_id: str):
    return repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="CoverageRecomputed",
            payload={"run_id": run_id, "status": "covered", "target_count": 1, "covered_target_count": 1},
            causation_id=causation_id,
        )
    )
