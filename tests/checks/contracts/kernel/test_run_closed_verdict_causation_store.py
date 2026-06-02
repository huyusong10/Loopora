from __future__ import annotations

from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.events import run_stream_id

from run_event_invariant_test_support import (
    append_accepted_evidence,
    append_coverage_recomputed,
    append_covered_coverage,
    append_run_closed,
    append_run_created,
    append_verdict_issued,
)


def test_domain_event_store_rejects_run_closed_causation_without_passing_verdict(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_closed_verdict_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id, loop_id="loop_closed_verdict_boundary")

    partial_coverage_event = append_coverage_recomputed(
        repository,
        stream_id,
        run_id,
        payload={"status": "partial", "target_count": 1, "missing_target_count": 1},
    )
    nonpassing_verdict = append_verdict_issued(
        repository,
        stream_id,
        run_id,
        payload={"status": "continue_required"},
        causation_id=partial_coverage_event.event_id,
    )
    with pytest.raises(ValueError, match="passing VerdictIssued"):
        append_run_closed(repository, stream_id, run_id, causation_id=nonpassing_verdict.event_id)

    evidence_event = append_accepted_evidence(
        repository,
        stream_id,
        run_id,
        evidence_id="ev_closed",
        verifies=["target:done_when.proof:covered"],
    )
    passable_coverage_event = append_covered_coverage(
        repository,
        stream_id,
        run_id,
        causation_id=evidence_event.event_id,
    )
    passing_verdict = append_verdict_issued(
        repository,
        stream_id,
        run_id,
        payload={"status": "passed"},
        causation_id=passable_coverage_event.event_id,
    )
    append_run_closed(repository, stream_id, run_id, causation_id=passing_verdict.event_id)

    assert [event.event_type for event in repository.list_domain_events(stream_id)][-3:] == [
        "CoverageRecomputed",
        "VerdictIssued",
        "RunClosed",
    ]


def test_domain_event_store_rejects_nonlegacy_run_closed_without_task_proof_causation(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_closed_missing_causation_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id, loop_id="loop_closed_missing_causation_boundary")

    with pytest.raises(ValueError, match="latest passing VerdictIssued"):
        append_run_closed(repository, stream_id, run_id)


def test_domain_event_store_allows_explicit_legacy_run_closed_without_task_proof_causation(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_closed_legacy_causation_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id, loop_id="loop_closed_legacy_causation_boundary")

    closed_event = append_run_closed(repository, stream_id, run_id, payload={"legacy_compat": True})

    assert closed_event.causation_id is None
    assert closed_event.payload["legacy_compat"] is True
