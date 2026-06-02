from __future__ import annotations

from pathlib import Path

from loopora.db import LooporaRepository
from loopora.engine import RepositoryRunEngine, RunEngineIssueVerdictRequest
from loopora.events import run_stream_id
from loopora.events.store import DomainEventAppendRequest
from loopora.kernel import ActorRef


def test_run_engine_issue_verdict_records_request_issue_and_closure_decision(tmp_path: Path) -> None:
    run_id = "run_verdict_command"
    repository, stream_id = create_verdict_run(tmp_path, run_id, loop_id="loop_verdict_command")

    result = issue_verdict(
        repository,
        run_id,
        {"status": "continue_required", "source": "gatekeeper", "summary": "Proof is incomplete."},
    )

    events = repository.list_domain_events(stream_id)

    assert_tail_event_types(events, "VerdictRequested", "VerdictIssued", "VerdictBlockedClosure")
    assert result.requested_event.event_id == events[-3].event_id
    assert result.issued_event.event_id == events[-2].event_id
    assert result.closure_event.event_id == events[-1].event_id
    assert result.next_gap_event is None
    assert events[-2].causation_id == events[-3].event_id
    assert events[-1].causation_id == events[-2].event_id
    assert events[-1].payload == {"run_id": run_id, "verdict_status": "continue_required", "allowed": False}


def test_run_engine_issue_verdict_selects_next_gap_after_blocked_closure(tmp_path: Path) -> None:
    run_id = "run_verdict_next_gap_command"
    repository, stream_id = create_verdict_run(tmp_path, run_id, loop_id="loop_verdict_next_gap_command")

    result = issue_verdict(
        repository,
        run_id,
        {
            "status": "continue_required",
            "source": "gatekeeper",
            "summary": "More proof is needed.",
            "next_gap": [{"target_id": "done_when.proof", "status": "missing"}],
        },
    )

    events = repository.list_domain_events(stream_id)

    assert_tail_event_types(events, "VerdictRequested", "VerdictIssued", "VerdictBlockedClosure", "NextGapSelected")
    assert result.next_gap_event is not None
    assert result.next_gap_event.event_id == events[-1].event_id
    assert events[-2].causation_id == events[-3].event_id
    assert events[-1].causation_id == events[-2].event_id
    assert events[-1].payload["target_id"] == "done_when.proof"
    assert events[-1].payload["status"] == "missing"


def test_run_engine_issue_verdict_accepts_managed_residual_risk_after_allowed_closure(tmp_path: Path) -> None:
    run_id = "run_verdict_residual_risk_command"
    repository, stream_id = create_verdict_run(tmp_path, run_id, loop_id="loop_verdict_residual_risk_command")
    append_weak_residual_risk_evidence(repository, stream_id, run_id)

    result = issue_verdict(
        repository,
        run_id,
        {
            "status": "passed_with_residual_risk",
            "source": "gatekeeper",
            "summary": "Accepted with managed follow-up.",
            "buckets": {"residual_risk": [{"label": "Manual follow-up remains.", "managed": True}]},
        },
    )

    events = repository.list_domain_events(stream_id)

    assert_tail_event_types(events, "VerdictRequested", "VerdictIssued", "VerdictAllowedClosure", "ResidualRiskAccepted")
    assert result.residual_risk_event is not None
    assert result.residual_risk_event.event_id == events[-1].event_id
    assert events[-1].causation_id == events[-2].event_id
    assert events[-1].payload["risk_count"] == 1
    assert result.next_gap_event is None


def create_verdict_run(tmp_path: Path, run_id: str, *, loop_id: str) -> tuple[LooporaRepository, str]:
    repository = LooporaRepository(tmp_path / "app.db")
    stream_id = run_stream_id(run_id)
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="RunCreated",
            payload={"run_id": run_id, "loop_id": loop_id},
        )
    )
    return repository, stream_id


def issue_verdict(repository: LooporaRepository, run_id: str, verdict: dict):
    return RepositoryRunEngine(repository).issue_verdict(
        RunEngineIssueVerdictRequest(run_id=run_id, actor=ActorRef.verdict_engine(), verdict=verdict)
    )


def append_weak_residual_risk_evidence(repository: LooporaRepository, stream_id: str, run_id: str) -> None:
    evidence_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="EvidenceAccepted",
            payload={"run_id": run_id, "evidence_id": "ev_residual_risk", "verifies": ["target:done_when.proof:covered"]},
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


def assert_tail_event_types(events: list, *event_types: str) -> None:
    assert [event.event_type for event in events[-len(event_types) :]] == list(event_types)
