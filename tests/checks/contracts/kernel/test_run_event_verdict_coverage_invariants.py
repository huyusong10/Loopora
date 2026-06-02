from __future__ import annotations

from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.events import run_stream_id
from loopora.events.store import DomainEventAppendRequest

from run_event_invariant_test_support import append_accepted_evidence, append_covered_coverage, append_run_created


def test_blocked_coverage_requires_blocked_verdict(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_blocked_coverage_verdict_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id)
    coverage_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="CoverageRecomputed",
            payload={"run_id": run_id, "status": "blocked", "target_count": 1, "blocked_target_count": 1},
        )
    )

    with pytest.raises(ValueError, match="must be blocked"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="VerdictIssued",
                payload={"run_id": run_id, "status": "continue_required"},
                causation_id=coverage_event.event_id,
            )
        )
    verdict_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="VerdictIssued",
            payload={"run_id": run_id, "status": "blocked"},
            causation_id=coverage_event.event_id,
        )
    )

    assert verdict_event.payload["status"] == "blocked"


def test_passed_with_residual_risk_requires_managed_residual_risk_bucket(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_residual_risk_verdict_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id)
    evidence_event = append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_risk")
    coverage_event = append_covered_coverage(repository, stream_id, run_id, causation_id=evidence_event.event_id)

    with pytest.raises(ValueError, match="requires residual_risk bucket"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="VerdictIssued",
                payload={"run_id": run_id, "status": "passed_with_residual_risk"},
                causation_id=coverage_event.event_id,
            )
        )
    with pytest.raises(ValueError, match="require management path"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="VerdictIssued",
                payload={
                    "run_id": run_id,
                    "status": "passed_with_residual_risk",
                    "buckets": {"residual_risk": [{"label": "Manual review remains."}]},
                },
                causation_id=coverage_event.event_id,
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
                "status": "passed_with_residual_risk",
                "buckets": {"residual_risk": [{"label": "Manual review remains.", "managed": True}]},
            },
            causation_id=coverage_event.event_id,
        )
    )

    assert verdict_event.payload["buckets"]["residual_risk"][0]["managed"] is True
