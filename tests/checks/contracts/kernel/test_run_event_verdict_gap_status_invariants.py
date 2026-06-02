from __future__ import annotations

from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.events import run_stream_id
from loopora.events.store import DomainEventAppendRequest

from run_event_invariant_test_support import append_accepted_evidence, append_covered_coverage, append_run_created


def test_blocked_verdict_next_gap_requires_blocked_status(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_blocked_verdict_gap_status_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id)

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
    append_run_created(repository, stream_id, run_id)
    evidence_event = append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_residual_risk_gap")
    coverage_event = append_covered_coverage(repository, stream_id, run_id, causation_id=evidence_event.event_id)

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


def test_plain_passed_verdict_cannot_select_next_gap(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_passing_verdict_next_gap_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id)
    evidence_event = append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_pass_next_gap")
    coverage_event = append_covered_coverage(repository, stream_id, run_id, causation_id=evidence_event.event_id)

    with pytest.raises(ValueError, match="cannot include unresolved next_gap"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="VerdictIssued",
                payload={
                    "run_id": run_id,
                    "status": "passed",
                    "next_gap": [{"target_id": "done_when.proof", "status": "weak"}],
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
            payload={"run_id": run_id, "status": "passed", "next_gap": []},
            causation_id=coverage_event.event_id,
        )
    )

    assert verdict_event.payload["next_gap"] == []
