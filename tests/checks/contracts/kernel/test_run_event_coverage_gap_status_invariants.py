from __future__ import annotations

from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.events import run_stream_id
from loopora.events.store import DomainEventAppendRequest

from run_event_invariant_test_support import append_run_created


def test_partial_coverage_requires_weak_or_missing_target_count(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_partial_coverage_count_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id)

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
    append_run_created(repository, stream_id, run_id)

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
