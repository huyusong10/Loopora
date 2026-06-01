from __future__ import annotations

from pathlib import Path

from loopora.db import LooporaRepository
from loopora.engine import RepositoryRunEngine, RunEngineIssueVerdictRequest
from loopora.events import run_stream_id
from loopora.events.store import DomainEventAppendRequest
from loopora.kernel import ActorRef


def test_run_engine_issue_verdict_records_request_issue_and_closure_decision(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_verdict_command"
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=run_stream_id(run_id),
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="RunCreated",
            payload={"run_id": run_id, "loop_id": "loop_verdict_command"},
        )
    )

    result = RepositoryRunEngine(repository).issue_verdict(
        RunEngineIssueVerdictRequest(
            run_id=run_id,
            actor=ActorRef.verdict_engine(),
            verdict={"status": "continue_required", "source": "gatekeeper", "summary": "Proof is incomplete."},
        )
    )

    events = repository.list_domain_events(run_stream_id(run_id))

    assert [event.event_type for event in events[-3:]] == [
        "VerdictRequested",
        "VerdictIssued",
        "VerdictBlockedClosure",
    ]
    assert result.requested_event.event_id == events[-3].event_id
    assert result.issued_event.event_id == events[-2].event_id
    assert result.closure_event.event_id == events[-1].event_id
    assert result.next_gap_event is None
    assert events[-2].causation_id == events[-3].event_id
    assert events[-1].causation_id == events[-2].event_id
    assert events[-1].payload == {"run_id": run_id, "verdict_status": "continue_required", "allowed": False}


def test_run_engine_issue_verdict_selects_next_gap_after_blocked_closure(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_verdict_next_gap_command"
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=run_stream_id(run_id),
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="RunCreated",
            payload={"run_id": run_id, "loop_id": "loop_verdict_next_gap_command"},
        )
    )

    result = RepositoryRunEngine(repository).issue_verdict(
        RunEngineIssueVerdictRequest(
            run_id=run_id,
            actor=ActorRef.verdict_engine(),
            verdict={
                "status": "continue_required",
                "source": "gatekeeper",
                "summary": "More proof is needed.",
                "next_gap": [{"target_id": "done_when.proof", "status": "missing"}],
            },
        )
    )

    events = repository.list_domain_events(run_stream_id(run_id))

    assert [event.event_type for event in events[-4:]] == [
        "VerdictRequested",
        "VerdictIssued",
        "VerdictBlockedClosure",
        "NextGapSelected",
    ]
    assert result.next_gap_event is not None
    assert result.next_gap_event.event_id == events[-1].event_id
    assert events[-2].causation_id == events[-3].event_id
    assert events[-1].causation_id == events[-2].event_id
    assert events[-1].payload["target_id"] == "done_when.proof"
    assert events[-1].payload["status"] == "missing"


def test_run_engine_issue_verdict_accepts_managed_residual_risk_after_allowed_closure(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_verdict_residual_risk_command"
    stream_id = run_stream_id(run_id)
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="RunCreated",
            payload={"run_id": run_id, "loop_id": "loop_verdict_residual_risk_command"},
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
                "evidence_id": "ev_residual_risk",
                "verifies": ["target:done_when.proof:covered"],
            },
        )
    )
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="CoverageRecomputed",
            payload={"run_id": run_id, "status": "weak", "target_count": 1, "weak_target_count": 1},
            causation_id=evidence_event.event_id,
        )
    )

    result = RepositoryRunEngine(repository).issue_verdict(
        RunEngineIssueVerdictRequest(
            run_id=run_id,
            actor=ActorRef.verdict_engine(),
            verdict={
                "status": "passed_with_residual_risk",
                "source": "gatekeeper",
                "summary": "Accepted with managed follow-up.",
                "buckets": {"residual_risk": [{"label": "Manual follow-up remains.", "managed": True}]},
            },
        )
    )

    events = repository.list_domain_events(stream_id)

    assert [event.event_type for event in events[-4:]] == [
        "VerdictRequested",
        "VerdictIssued",
        "VerdictAllowedClosure",
        "ResidualRiskAccepted",
    ]
    assert result.residual_risk_event is not None
    assert result.residual_risk_event.event_id == events[-1].event_id
    assert events[-1].causation_id == events[-2].event_id
    assert events[-1].payload["risk_count"] == 1
    assert result.next_gap_event is None
