from __future__ import annotations

from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.events import run_stream_id
from loopora.events.run_event_payloads import verdict_issued_payload
from loopora.events.store import DomainEventAppendRequest


def test_verdict_evidence_refs_must_reference_accepted_evidence(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_verdict_evidence_ref_boundary"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id)
    evidence_event = _append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_known")
    coverage_event = _append_covered_coverage(repository, stream_id, run_id, causation_id=evidence_event.event_id)

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
    _append_run_created(repository, stream_id, run_id)
    evidence_event = _append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_known")
    coverage_event = _append_covered_coverage(repository, stream_id, run_id, causation_id=evidence_event.event_id)

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
    _append_run_created(repository, stream_id, run_id)
    evidence_event = _append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_known")
    coverage_event = _append_covered_coverage(repository, stream_id, run_id, causation_id=evidence_event.event_id)

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


def test_verdict_next_gap_must_be_a_list_of_objects(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_verdict_next_gap_shape_boundary"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id)
    evidence_event = _append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_known")
    coverage_event = _append_covered_coverage(repository, stream_id, run_id, causation_id=evidence_event.event_id)

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
    _append_run_created(repository, stream_id, run_id)

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


def test_plain_passed_verdict_cannot_select_next_gap(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_passing_verdict_next_gap_boundary"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id)
    evidence_event = _append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_pass_next_gap")
    coverage_event = _append_covered_coverage(repository, stream_id, run_id, causation_id=evidence_event.event_id)

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


def test_verdict_status_must_be_kernel_verdict_status(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_verdict_status_boundary"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id)

    with pytest.raises(ValueError, match="kernel verdict status"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="VerdictIssued",
                payload={"run_id": run_id, "status": "failed"},
            )
        )


@pytest.mark.parametrize(
    ("legacy_status", "kernel_status"),
    [
        ("insufficient_evidence", "continue_required"),
        ("failed", "blocked"),
    ],
)
def test_verdict_payload_normalizes_legacy_statuses_before_append(
    tmp_path: Path,
    legacy_status: str,
    kernel_status: str,
) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = f"run_legacy_verdict_status_{kernel_status}"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id)

    verdict_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="VerdictIssued",
            payload=verdict_issued_payload(run_id, {"status": legacy_status}),
        )
    )

    assert verdict_event.payload["status"] == kernel_status


def test_coverage_top_gaps_require_target_identity_and_unresolved_status(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_coverage_gap_identity_boundary"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id)

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
                payload={"run_id": run_id, "status": "partial", "top_gaps": [{"target_id": "done_when.proof", "status": "covered"}]},
            )
        )
    coverage_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="CoverageRecomputed",
            payload={"run_id": run_id, "status": "partial", "top_gaps": [{"target_id": "done_when.proof", "status": "missing"}]},
        )
    )

    assert coverage_event.payload["top_gaps"][0]["status"] == "missing"


def test_covered_coverage_cannot_include_top_gaps(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_covered_top_gap_boundary"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id)
    evidence_event = _append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_covered_top_gap")

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
    _append_run_created(repository, stream_id, run_id)

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


def test_accepted_evidence_verified_evidence_refs_must_reference_prior_accepted_evidence(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_evidence_ref_boundary"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id)

    with pytest.raises(ValueError, match="verifies evidence refs must reference prior accepted evidence"):
        _append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_bad_link", verifies=["evidence:ev_missing"])
    with pytest.raises(ValueError, match="verifies evidence refs must reference prior accepted evidence"):
        _append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_self_claim", verifies=["evidence:ev_self_claim"])
    _append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_base")
    self_measured_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="EvidenceAccepted",
            payload={
                "run_id": run_id,
                "evidence_id": "ev_self_measured",
                "verifies": ["evidence:ev_self_measured"],
                "measured_evidence": True,
            },
        )
    )
    linked_event = _append_accepted_evidence(
        repository,
        stream_id,
        run_id,
        evidence_id="ev_linked",
        verifies=["evidence:ev_base"],
    )

    assert self_measured_event.payload["measured_evidence"] is True
    assert linked_event.sequence == self_measured_event.sequence + 1
    assert linked_event.payload["verifies"] == ["evidence:ev_base"]


def test_accepted_evidence_verifies_must_be_a_list(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_evidence_verifies_shape_boundary"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id)

    with pytest.raises(ValueError, match="verifies must be a list"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="EvidenceAccepted",
                payload={"run_id": run_id, "evidence_id": "ev_bad_shape", "verifies": "target:done_when.proof"},
            )
        )


def test_blocked_coverage_requires_blocked_verdict(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_blocked_coverage_verdict_boundary"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id)
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
    _append_run_created(repository, stream_id, run_id)
    evidence_event = _append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_risk")
    coverage_event = _append_covered_coverage(repository, stream_id, run_id, causation_id=evidence_event.event_id)

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


def test_coverage_classified_target_counts_cannot_exceed_target_count(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_coverage_classified_count_boundary"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id)
    evidence_event = _append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_coverage_counts")

    with pytest.raises(ValueError, match="classified target counts"):
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
                    "missing_target_count": 1,
                },
                causation_id=evidence_event.event_id,
            )
        )


def test_blocked_coverage_requires_blocked_target_count(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_blocked_coverage_count_boundary"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id)

    with pytest.raises(ValueError, match="blocked_target_count"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="CoverageRecomputed",
                payload={"run_id": run_id, "status": "blocked", "target_count": 1},
            )
        )


def test_weak_coverage_requires_weak_or_missing_target_count(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_weak_coverage_count_boundary"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id)
    evidence_event = _append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_weak_counts")

    with pytest.raises(ValueError, match="weak or missing targets"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="CoverageRecomputed",
                payload={"run_id": run_id, "status": "weak", "target_count": 1, "covered_target_count": 1},
                causation_id=evidence_event.event_id,
            )
        )


def _append_run_created(repository: LooporaRepository, stream_id: str, run_id: str) -> None:
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="RunCreated",
            payload={"run_id": run_id, "loop_id": "loop_verdict_evidence_ref_boundary"},
        )
    )


def _append_accepted_evidence(
    repository: LooporaRepository,
    stream_id: str,
    run_id: str,
    *,
    evidence_id: str,
    verifies: list[str] | None = None,
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
                "verifies": verifies or ["target:done_when.proof:covered"],
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
