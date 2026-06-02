from __future__ import annotations

from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.events import run_stream_id
from loopora.events.store import DomainEventAppendRequest

from run_event_invariant_test_support import append_accepted_evidence, append_covered_coverage, append_run_created


def test_verdict_evidence_refs_must_reference_accepted_evidence(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_verdict_evidence_ref_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id)
    evidence_event = append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_known")
    coverage_event = append_covered_coverage(repository, stream_id, run_id, causation_id=evidence_event.event_id)

    with pytest.raises(ValueError, match="evidence_refs must reference accepted EvidenceAccepted"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="VerdictIssued",
                payload={
                    "run_id": run_id,
                    "status": "passed",
                    "buckets": {"proven": [{"label": "Claim", "evidence_refs": ["ev_missing"]}]},
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
                "status": "passed",
                "buckets": {"proven": [{"label": "Claim", "evidence_refs": ["ev_known"]}]},
            },
            causation_id=coverage_event.event_id,
        )
    )

    assert verdict_event.payload["buckets"]["proven"][0]["evidence_refs"] == ["ev_known"]


def test_verdict_evidence_refs_must_be_a_list(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_verdict_evidence_ref_shape_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id)
    evidence_event = append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_known")
    coverage_event = append_covered_coverage(repository, stream_id, run_id, causation_id=evidence_event.event_id)

    with pytest.raises(ValueError, match="evidence_refs must be a list"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="VerdictIssued",
                payload={
                    "run_id": run_id,
                    "status": "passed",
                    "buckets": {"proven": [{"label": "Claim", "evidence_refs": "ev_known"}]},
                },
                causation_id=coverage_event.event_id,
            )
        )


def test_verdict_bucket_entries_must_be_lists(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_verdict_bucket_shape_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id)
    evidence_event = append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_known")
    coverage_event = append_covered_coverage(repository, stream_id, run_id, causation_id=evidence_event.event_id)

    with pytest.raises(ValueError, match="bucket entries must be lists"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="VerdictIssued",
                payload={
                    "run_id": run_id,
                    "status": "passed",
                    "buckets": {"proven": {"label": "Claim", "evidence_refs": ["ev_known"]}},
                },
                causation_id=coverage_event.event_id,
            )
        )
