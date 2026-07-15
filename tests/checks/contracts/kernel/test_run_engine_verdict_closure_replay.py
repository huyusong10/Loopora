from __future__ import annotations

from pathlib import Path

from loopora.db import LooporaRepository
from loopora.db_runtime_state import RunUpdate
from loopora.engine import (
    RepositoryRunEngine,
    RunEngineAdvanceStatus,
    RunEngineCoverageRecomputedRequest,
    RunEngineIssueVerdictRequest,
    RunEngineRecordStepEvidenceRequest,
)
from loopora.events import run_stream_id

from run_engine_lifecycle_replay_test_support import create_lifecycle_replay_run, headless_runner_actor


def test_run_engine_advance_closes_passing_verdict(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = create_lifecycle_replay_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = headless_runner_actor()

    engine.start(run["id"])
    engine.record_step_evidence(
        RunEngineRecordStepEvidenceRequest(
            run_id=run["id"],
            actor=actor,
            evidence_entry={
                "id": "ev_close",
                "step_id": "builder",
                "role_id": "builder",
                "claim": "Closure proof exists.",
                "result": "passed",
                "verifies": ["target:done_when.proof:covered"],
            },
            coverage_projection={"status": "covered", "target_count": 1, "covered_target_count": 1},
        )
    )
    engine.issue_verdict(
        RunEngineIssueVerdictRequest(
            run_id=run["id"],
            actor=actor,
            verdict={"status": "passed", "source": "gatekeeper", "summary": "Evidence is enough."},
        )
    )

    outcome = engine.advance(run["id"])
    events = repository.list_domain_events(run_stream_id(run["id"]))
    cached_snapshot = repository.get_projection_record("run_snapshot", run["id"])

    assert outcome.status == RunEngineAdvanceStatus.CLOSED
    assert outcome.next_action == "complete"
    assert outcome.verdict_status.value == "passed"
    passing_verdict = [event for event in events if event.event_type == "VerdictIssued"][-1]
    assert events[-1].event_type == "RunClosed"
    assert events[-1].causation_id == passing_verdict.event_id
    assert [event.event_type for event in events[-4:]] == [
        "VerdictRequested",
        "VerdictIssued",
        "VerdictAllowedClosure",
        "RunClosed",
    ]
    assert cached_snapshot["payload"]["lifecycle_status"] == "closed"


def test_legacy_run_lifecycle_close_does_not_causally_promote_nonpassing_verdict(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = create_lifecycle_replay_run(repository, tmp_path)
    actor = headless_runner_actor()
    engine = RepositoryRunEngine(repository)

    engine.recompute_coverage(
        RunEngineCoverageRecomputedRequest(
            run_id=run["id"],
            actor=actor,
            coverage_projection={"status": "partial", "target_count": 1, "missing_target_count": 1},
        )
    )
    engine.issue_verdict(
        RunEngineIssueVerdictRequest(
            run_id=run["id"], actor=actor, verdict={"status": "continue_required", "summary": "More proof is needed."}
        )
    )
    repository.update_run(run["id"], RunUpdate(status="succeeded", finished_at="2026-01-01T00:01:00+00:00"))
    events = repository.list_domain_events(run_stream_id(run["id"]))

    assert [event.event_type for event in events[-5:]] == [
        "CoverageRecomputed",
        "VerdictRequested",
        "VerdictIssued",
        "VerdictBlockedClosure",
        "RunClosed",
    ]
    assert events[-1].causation_id is None
    assert events[-1].payload["legacy_compat"] is True
