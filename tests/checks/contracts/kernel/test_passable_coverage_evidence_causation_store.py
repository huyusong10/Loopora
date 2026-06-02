from __future__ import annotations

from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.events import run_stream_id
from loopora.events.store import DomainEventAppendRequest


def test_domain_event_store_rejects_passable_coverage_without_evidence_causation(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_coverage_evidence_boundary"
    stream_id = run_stream_id(run_id)

    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="RunCreated",
            payload={"run_id": run_id, "loop_id": "loop_coverage_evidence_boundary"},
        )
    )
    with pytest.raises(ValueError, match="requires prior EvidenceAccepted"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="CoverageRecomputed",
                payload={"run_id": run_id, "status": "covered", "target_count": 1, "covered_target_count": 1},
            )
        )
    step_only_evidence_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="EvidenceAccepted",
            payload={"run_id": run_id, "evidence_id": "ev_step_only", "verifies": ["step_result:builder:completed"]},
        )
    )
    with pytest.raises(ValueError, match="verify a target or evidence ref"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="CoverageRecomputed",
                payload={
                    "run_id": run_id,
                    "status": "weak",
                    "target_count": 2,
                    "covered_target_count": 1,
                    "weak_target_count": 1,
                },
                causation_id=step_only_evidence_event.event_id,
            )
        )
    evidence_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="EvidenceAccepted",
            payload={"run_id": run_id, "evidence_id": "ev_coverage", "verifies": ["target:done_when.proof:weak"]},
        )
    )
    with pytest.raises(ValueError, match="requires causation_id"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="CoverageRecomputed",
                payload={
                    "run_id": run_id,
                    "status": "weak",
                    "target_count": 2,
                    "covered_target_count": 1,
                    "weak_target_count": 1,
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
                "status": "weak",
                "target_count": 2,
                "covered_target_count": 1,
                "weak_target_count": 1,
            },
            causation_id=evidence_event.event_id,
        )
    )

    assert coverage_event.causation_id == evidence_event.event_id
    assert [event.event_type for event in repository.list_domain_events(stream_id)] == [
        "RunCreated",
        "EvidenceAccepted",
        "EvidenceAccepted",
        "CoverageRecomputed",
    ]
