from __future__ import annotations

from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.events import loop_stream_id, run_stream_id
from loopora.events.store import DomainEventAppendRequest


def test_domain_event_store_rejects_surface_event_types(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")

    with pytest.raises(ValueError, match="unsupported core domain event type"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=run_stream_id("run_surface"),
                aggregate_type="run",
                aggregate_id="run_surface",
                event_type="HostTraceObserved",
                payload={"trace": "diagnostic only"},
            )
        )

    assert repository.list_domain_events(run_stream_id("run_surface")) == []


def test_domain_event_transaction_rolls_back_when_later_event_is_rejected(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    stream_id = run_stream_id("run_atomic_boundary")

    with pytest.raises(ValueError, match="unsupported core domain event type"):
        repository.append_domain_event_transaction(
            lambda event_transaction: (
                event_transaction.append_domain_event(
                    DomainEventAppendRequest(
                        stream_id=stream_id,
                        aggregate_type="run",
                        aggregate_id="run_atomic_boundary",
                        event_type="RunStarted",
                        payload={"run_id": "run_atomic_boundary"},
                    )
                ),
                event_transaction.append_domain_event(
                    DomainEventAppendRequest(
                        stream_id=stream_id,
                        aggregate_type="run",
                        aggregate_id="run_atomic_boundary",
                        event_type="HostTraceObserved",
                        payload={"trace": "diagnostic only"},
                    )
                ),
            )
        )

    assert repository.list_domain_events(stream_id) == []


def test_domain_event_store_exposes_latest_sequence_without_replay(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    stream_id = run_stream_id("run_latest_sequence")

    assert repository.latest_domain_event_sequence(stream_id) == 0
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id="run_latest_sequence",
            event_type="RunCreated",
            payload={"run_id": "run_latest_sequence", "loop_id": "loop_latest_sequence"},
        )
    )
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id="run_latest_sequence",
            event_type="RunStarted",
            payload={"run_id": "run_latest_sequence"},
        )
    )

    assert repository.latest_domain_event_sequence(stream_id) == 2


def test_domain_event_store_rejects_run_lifecycle_events_after_terminal(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    stream_id = run_stream_id("run_terminal_boundary")

    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id="run_terminal_boundary",
            event_type="RunCreated",
            payload={"run_id": "run_terminal_boundary", "loop_id": "loop_terminal_boundary"},
        )
    )
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id="run_terminal_boundary",
            event_type="RunClosed",
            payload={"run_id": "run_terminal_boundary"},
        )
    )

    with pytest.raises(ValueError, match="terminal run stream"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id="run_terminal_boundary",
                event_type="RunStarted",
                payload={"run_id": "run_terminal_boundary"},
            )
        )

    assert [event.event_type for event in repository.list_domain_events(stream_id)] == ["RunCreated", "RunClosed"]


def test_domain_event_store_rejects_accepted_evidence_without_identity(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_evidence_identity_boundary"
    stream_id = run_stream_id(run_id)

    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="RunCreated",
            payload={"run_id": run_id, "loop_id": "loop_evidence_identity_boundary"},
        )
    )
    with pytest.raises(ValueError, match="requires evidence_id"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="EvidenceAccepted",
                payload={"run_id": run_id, "claim": "Anonymous proof."},
            )
        )
    with pytest.raises(ValueError, match="requires at least one verifies"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="EvidenceAccepted",
                payload={"run_id": run_id, "evidence_id": "ev_identity", "claim": "Unlinked proof."},
            )
        )
    evidence_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="EvidenceAccepted",
            payload={
                "run_id": run_id,
                "evidence_id": "ev_identity",
                "claim": "Named proof.",
                "verifies": ["target:done_when.proof:covered"],
            },
        )
    )

    assert evidence_event.payload["evidence_id"] == "ev_identity"
    assert [event.event_type for event in repository.list_domain_events(stream_id)] == ["RunCreated", "EvidenceAccepted"]


def test_domain_event_store_rejects_step_result_events_without_causation_chain(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_step_result_boundary"
    stream_id = run_stream_id(run_id)

    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="RunCreated",
            payload={"run_id": run_id, "loop_id": "loop_step_result_boundary"},
        )
    )
    with pytest.raises(ValueError, match="requires prior StepAccepted"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="StepCommitted",
                payload={"run_id": run_id, "step_id": "builder", "iteration": 1, "result_status": "completed"},
            )
        )
    submitted_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="StepSubmitted",
            payload={"run_id": run_id, "step_id": "builder", "iteration": 1, "status": "completed"},
        )
    )
    with pytest.raises(ValueError, match="requires causation_id"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="StepSubmissionRejected",
                payload={"run_id": run_id, "step_id": "builder", "iteration": 1, "reason": "invalid result"},
            )
        )
    with pytest.raises(ValueError, match="requires causation_id"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="StepAccepted",
                payload={"run_id": run_id, "step_id": "builder", "iteration": 1, "result_status": "completed"},
            )
        )
    accepted_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="StepAccepted",
            payload={"run_id": run_id, "step_id": "builder", "iteration": 1, "result_status": "completed"},
            causation_id=submitted_event.event_id,
        )
    )
    with pytest.raises(ValueError, match="requires causation_id"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="StepCommitted",
                payload={"run_id": run_id, "step_id": "builder", "iteration": 1, "result_status": "completed"},
            )
        )
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="StepCommitted",
            payload={"run_id": run_id, "step_id": "builder", "iteration": 1, "result_status": "completed"},
            causation_id=accepted_event.event_id,
        )
    )

    assert [event.event_type for event in repository.list_domain_events(stream_id)] == [
        "RunCreated",
        "StepSubmitted",
        "StepAccepted",
        "StepCommitted",
    ]


def test_domain_event_store_rejects_passing_verdict_without_passable_coverage(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_verdict_coverage_boundary"
    stream_id = run_stream_id(run_id)

    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="RunCreated",
            payload={"run_id": run_id, "loop_id": "loop_verdict_coverage_boundary"},
        )
    )
    with pytest.raises(ValueError, match="requires latest CoverageRecomputed"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="VerdictIssued",
                payload={"run_id": run_id, "status": "passed"},
            )
        )
    partial_coverage_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="CoverageRecomputed",
            payload={"run_id": run_id, "status": "partial", "target_count": 1, "missing_target_count": 1},
        )
    )
    with pytest.raises(ValueError, match="VerdictIssued requires causation_id"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="VerdictIssued",
                payload={"run_id": run_id, "status": "passed_with_residual_risk"},
            )
        )
    with pytest.raises(ValueError, match="requires latest CoverageRecomputed"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="VerdictIssued",
                payload={"run_id": run_id, "status": "passed_with_residual_risk"},
                causation_id=partial_coverage_event.event_id,
            )
        )
    evidence_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="EvidenceAccepted",
            payload={"run_id": run_id, "evidence_id": "ev_verdict_coverage", "verifies": ["target:done_when.proof:weak"]},
        )
    )
    coverage_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="CoverageRecomputed",
            payload={"run_id": run_id, "status": "weak", "target_count": 2, "covered_target_count": 1, "weak_target_count": 1},
            causation_id=evidence_event.event_id,
        )
    )
    with pytest.raises(ValueError, match="requires causation_id"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="VerdictIssued",
                payload={"run_id": run_id, "status": "passed_with_residual_risk"},
            )
        )
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
            },
            causation_id=coverage_event.event_id,
        )
    )

    assert [event.event_type for event in repository.list_domain_events(stream_id)] == [
        "RunCreated",
        "CoverageRecomputed",
        "EvidenceAccepted",
        "CoverageRecomputed",
        "VerdictIssued",
    ]


def test_domain_event_store_requires_verdict_causation_when_coverage_exists(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_verdict_causation_boundary"
    stream_id = run_stream_id(run_id)

    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="RunCreated",
            payload={"run_id": run_id, "loop_id": "loop_verdict_causation_boundary"},
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
    with pytest.raises(ValueError, match="VerdictIssued requires causation_id"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="VerdictIssued",
                payload={"run_id": run_id, "status": "continue_required"},
            )
        )
    verdict_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="VerdictIssued",
            payload={"run_id": run_id, "status": "continue_required"},
            causation_id=coverage_event.event_id,
        )
    )

    assert verdict_event.causation_id == coverage_event.event_id
    assert [event.event_type for event in repository.list_domain_events(stream_id)] == [
        "RunCreated",
        "CoverageRecomputed",
        "VerdictIssued",
    ]


def test_domain_event_store_rejects_run_closed_causation_without_passing_verdict(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_closed_verdict_boundary"
    stream_id = run_stream_id(run_id)

    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="RunCreated",
            payload={"run_id": run_id, "loop_id": "loop_closed_verdict_boundary"},
        )
    )
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
                payload={"run_id": run_id, "status": "weak", "target_count": 2, "covered_target_count": 1, "weak_target_count": 1},
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
                payload={"run_id": run_id, "status": "weak", "target_count": 2, "covered_target_count": 1, "weak_target_count": 1},
            )
        )
    coverage_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="CoverageRecomputed",
            payload={"run_id": run_id, "status": "weak", "target_count": 2, "covered_target_count": 1, "weak_target_count": 1},
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


def test_domain_event_store_rejects_inconsistent_coverage_status_counts(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_coverage_counts_boundary"
    stream_id = run_stream_id(run_id)

    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="RunCreated",
            payload={"run_id": run_id, "loop_id": "loop_coverage_counts_boundary"},
        )
    )
    evidence_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="EvidenceAccepted",
            payload={"run_id": run_id, "evidence_id": "ev_counts", "verifies": ["target:done_when.proof:covered"]},
        )
    )
    with pytest.raises(ValueError, match="covered_target_count"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="CoverageRecomputed",
                payload={"run_id": run_id, "status": "covered", "target_count": 2, "covered_target_count": 1},
                causation_id=evidence_event.event_id,
            )
        )
    with pytest.raises(ValueError, match="cannot include blocked"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="CoverageRecomputed",
                payload={"run_id": run_id, "status": "weak", "target_count": 2, "blocked_target_count": 1},
                causation_id=evidence_event.event_id,
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

    assert coverage_event.payload["covered_target_count"] == 1
    assert [event.event_type for event in repository.list_domain_events(stream_id)] == [
        "RunCreated",
        "EvidenceAccepted",
        "CoverageRecomputed",
    ]


def test_domain_event_transaction_rolls_back_event_derived_artifact_indexes(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    stream_id = run_stream_id("run_atomic_artifact")

    def append_artifact_then_rejected_event(event_transaction) -> None:
        source_event = event_transaction.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id="run_atomic_artifact",
                event_type="RunCreated",
                payload={"run_id": "run_atomic_artifact", "loop_id": "loop_atomic_artifact"},
            )
        )
        event_transaction.record_artifact_index(
            {
                "artifact_id": "artifact_atomic",
                "run_id": "run_atomic_artifact",
                "loop_id": "loop_atomic_artifact",
                "kind": "workspace",
                "uri": "proof.txt",
                "created_by_event_id": source_event.event_id,
            }
        )
        event_transaction.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id="run_atomic_artifact",
                event_type="HostTraceObserved",
                payload={"trace": "diagnostic only"},
            )
        )

    with pytest.raises(ValueError, match="unsupported core domain event type"):
        repository.append_domain_event_transaction(append_artifact_then_rejected_event)

    assert repository.list_artifact_index(run_id="run_atomic_artifact") == []
    assert repository.list_domain_events(stream_id) == []


def test_artifact_index_requires_existing_domain_event_source(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")

    with pytest.raises(ValueError, match="created_by_event_id"):
        repository.record_artifact_index(
            {
                "artifact_id": "artifact_orphan",
                "run_id": "run_orphan",
                "loop_id": "loop_orphan",
                "kind": "workspace",
                "uri": "proof.txt",
            }
        )

    with pytest.raises(ValueError, match="event_store event"):
        repository.record_artifact_index(
            {
                "artifact_id": "artifact_unknown_source",
                "run_id": "run_orphan",
                "loop_id": "loop_orphan",
                "kind": "workspace",
                "uri": "proof.txt",
                "created_by_event_id": "event_missing",
            }
        )

    assert repository.list_artifact_index(run_id="run_orphan") == []


def test_domain_event_store_rejects_aggregate_type_mismatches(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")

    with pytest.raises(ValueError, match="requires aggregate_type loop"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=run_stream_id("run_wrong_loop_event"),
                aggregate_type="run",
                aggregate_id="run_wrong_loop_event",
                event_type="LoopArchived",
                payload={"loop_id": "loop_wrong"},
            )
        )
    with pytest.raises(ValueError, match="requires aggregate_type run"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=loop_stream_id("loop_wrong_run_event"),
                aggregate_type="loop",
                aggregate_id="loop_wrong_run_event",
                event_type="RunStarted",
                payload={"run_id": "run_wrong"},
            )
        )

    assert repository.list_domain_events(run_stream_id("run_wrong_loop_event")) == []
    assert repository.list_domain_events(loop_stream_id("loop_wrong_run_event")) == []


def test_domain_event_store_rejects_stream_id_mismatches(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")

    with pytest.raises(ValueError, match="requires stream_id run:run_stream_boundary"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=loop_stream_id("loop_wrong_stream"),
                aggregate_type="run",
                aggregate_id="run_stream_boundary",
                event_type="RunStarted",
                payload={"run_id": "run_stream_boundary"},
            )
        )
    with pytest.raises(ValueError, match="requires stream_id loop:loop_stream_boundary"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=run_stream_id("run_wrong_stream"),
                aggregate_type="loop",
                aggregate_id="loop_stream_boundary",
                event_type="LoopArchived",
                payload={"loop_id": "loop_stream_boundary"},
            )
        )

    assert repository.list_domain_events(loop_stream_id("loop_wrong_stream")) == []
    assert repository.list_domain_events(run_stream_id("run_wrong_stream")) == []
