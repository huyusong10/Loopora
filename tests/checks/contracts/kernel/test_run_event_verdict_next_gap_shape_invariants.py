from __future__ import annotations

from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.events import run_stream_id
from loopora.events.store import DomainEventAppendRequest

from run_event_invariant_test_support import append_accepted_evidence, append_covered_coverage, append_run_created


def test_verdict_next_gap_must_be_a_list_of_objects(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_verdict_next_gap_shape_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id)
    evidence_event = append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_known")
    coverage_event = append_covered_coverage(repository, stream_id, run_id, causation_id=evidence_event.event_id)

    with pytest.raises(ValueError, match="next_gap must be a list"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="VerdictIssued",
                payload={"run_id": run_id, "status": "passed", "next_gap": "done_when.follow_up"},
                causation_id=coverage_event.event_id,
            )
        )
    with pytest.raises(ValueError, match="next_gap entries must be objects"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="VerdictIssued",
                payload={"run_id": run_id, "status": "passed", "next_gap": ["done_when.follow_up"]},
                causation_id=coverage_event.event_id,
            )
        )


def test_verdict_next_gap_entries_require_target_identity_and_unresolved_status(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_verdict_next_gap_identity_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id)

    with pytest.raises(ValueError, match="entries require target_id"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="VerdictIssued",
                payload={"run_id": run_id, "status": "continue_required", "next_gap": [{"status": "weak"}]},
            )
        )
    with pytest.raises(ValueError, match="unresolved status"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="VerdictIssued",
                payload={
                    "run_id": run_id,
                    "status": "continue_required",
                    "next_gap": [{"target_id": "done_when.proof", "status": "covered"}],
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
                "status": "continue_required",
                "next_gap": [{"target_id": "done_when.proof", "status": "missing"}],
            },
        )
    )

    assert verdict_event.payload["next_gap"][0]["target_id"] == "done_when.proof"
