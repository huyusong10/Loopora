from __future__ import annotations

from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.events import run_stream_id
from loopora.events.store import DomainEventAppendRequest

from run_event_invariant_test_support import append_accepted_evidence, append_run_created


def test_coverage_top_gaps_require_target_identity_and_unresolved_status(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_coverage_gap_identity_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id)

    with pytest.raises(ValueError, match="top_gaps must be a list"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="CoverageRecomputed",
                payload={"run_id": run_id, "status": "partial", "top_gaps": "done_when.proof"},
            )
        )
    with pytest.raises(ValueError, match="top_gaps entries must be objects"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="CoverageRecomputed",
                payload={"run_id": run_id, "status": "partial", "top_gaps": ["done_when.proof"]},
            )
        )
    with pytest.raises(ValueError, match="entries require target_id"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="CoverageRecomputed",
                payload={"run_id": run_id, "status": "partial", "top_gaps": [{"status": "missing"}]},
            )
        )
    with pytest.raises(ValueError, match="unresolved status"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="CoverageRecomputed",
                payload={
                    "run_id": run_id,
                    "status": "partial",
                    "top_gaps": [{"target_id": "done_when.proof", "status": "covered"}],
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
                "status": "partial",
                "top_gaps": [{"target_id": "done_when.proof", "status": "missing"}],
            },
        )
    )

    assert coverage_event.payload["top_gaps"][0]["status"] == "missing"


def test_covered_coverage_cannot_include_top_gaps(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_covered_top_gap_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id)
    evidence_event = append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_covered_top_gap")

    with pytest.raises(ValueError, match="covered CoverageRecomputed cannot include top_gaps"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="CoverageRecomputed",
                payload={
                    "run_id": run_id,
                    "status": "covered",
                    "target_count": 1,
                    "covered_target_count": 1,
                    "top_gaps": [{"target_id": "gatekeeper.finish", "status": "missing"}],
                },
                causation_id=evidence_event.event_id,
            )
        )


def test_coverage_status_must_be_kernel_coverage_status(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_coverage_status_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id)

    with pytest.raises(ValueError, match="kernel coverage status"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="CoverageRecomputed",
                payload={"run_id": run_id, "status": "pending"},
            )
        )
    coverage_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="CoverageRecomputed",
            payload={"run_id": run_id, "status": "partial", "target_count": 1, "missing_target_count": 1},
        )
    )

    assert coverage_event.payload["status"] == "partial"
