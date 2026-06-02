from __future__ import annotations

from pathlib import Path

from loopora.db import LooporaRepository
from loopora.engine import (
    RepositoryRunEngine,
    RunEngineAcceptEvidenceRequest,
    RunEngineCoverageRecomputedRequest,
    RunEngineIssueVerdictRequest,
)
from loopora.events import run_stream_id
from loopora.events.projection_cache import replay_run_projections
from loopora.kernel import ActorRef

from event_replay_evidence_verdict_projection_support import create_event_projection_run


VERDICT_CLOSURE_SOURCE_SEQUENCE = 6


def test_run_engine_replays_evidence_coverage_verdict_and_audit_projections(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = create_event_projection_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="runner", id="headless")

    engine.accept_evidence(
        RunEngineAcceptEvidenceRequest(
            run_id=run["id"],
            actor=actor,
            evidence_entry={
                "id": "ev_replay",
                "step_id": "builder",
                "role_id": "builder",
                "archetype": "builder",
                "claim": "Replay proof exists.",
                "method": "pytest",
                "result": "passed",
                "verifies": ["target:done_when.proof:covered"],
                "artifact_refs": [{"kind": "workspace"}],
            },
        )
    )
    engine.recompute_coverage(
        RunEngineCoverageRecomputedRequest(
            run_id=run["id"],
            actor=actor,
            coverage_projection={
                "status": "covered",
                "target_count": 1,
                "covered_target_count": 1,
                "top_gaps": [],
            },
        )
    )
    engine.issue_verdict(
        RunEngineIssueVerdictRequest(
            run_id=run["id"],
            actor=actor,
            verdict={"status": "passed", "source": "gatekeeper", "summary": "Replay says pass."},
        )
    )

    projections = replay_run_projections(repository, run["id"])
    cached_coverage = repository.get_projection_record("coverage", run["id"])
    cached_verdict = repository.get_projection_record("task_verdict", run["id"])

    assert projections["run_snapshot"]["run_id"] == run["id"]
    assert projections["current_step"]["claimable"] is False
    assert projections["evidence_ledger"]["entries"][0]["evidence_id"] == "ev_replay"
    assert projections["evidence_ledger"]["entries"][0]["claim"] == "Replay proof exists."
    assert projections["coverage"]["status"] == "covered"
    assert projections["coverage"]["covered_target_count"] == 1
    assert projections["coverage"]["top_gaps"] == []
    assert projections["task_verdict"] == {
        "schema_version": 1,
        "kind": "event_replayed_task_verdict",
        "source_sequence": VERDICT_CLOSURE_SOURCE_SEQUENCE,
        "status": "passed",
        "source": "gatekeeper",
        "summary": "Replay says pass.",
    }
    assert cached_coverage["source_sequence"] == VERDICT_CLOSURE_SOURCE_SEQUENCE
    assert cached_coverage["payload"]["source_sequence"] == VERDICT_CLOSURE_SOURCE_SEQUENCE
    assert cached_verdict["source_sequence"] == VERDICT_CLOSURE_SOURCE_SEQUENCE
    assert cached_verdict["payload"]["status"] == "passed"
    assert projections["audit_timeline"]["events"][2]["event_type"] == "CoverageRecomputed"
    events = repository.list_domain_events(run_stream_id(run["id"]))
    coverage_event = events[2]
    evidence_event = events[1]
    requested_event = events[3]
    verdict_event = events[4]
    closure_event = events[5]
    assert coverage_event.causation_id == evidence_event.event_id
    assert requested_event.causation_id == coverage_event.event_id
    assert verdict_event.causation_id == requested_event.event_id
    assert closure_event.causation_id == verdict_event.event_id
    assert [event["event_type"] for event in projections["audit_timeline"]["events"]] == [
        "RunCreated",
        "EvidenceAccepted",
        "CoverageRecomputed",
        "VerdictRequested",
        "VerdictIssued",
        "VerdictAllowedClosure",
    ]
