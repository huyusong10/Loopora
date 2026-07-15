from __future__ import annotations

from pathlib import Path

from loopora.db import LooporaRepository
from loopora.db_runtime_state import RunUpdate
from loopora.engine import RepositoryRunEngine, RunEngineIssueVerdictRequest, RunEngineRecordStepEvidenceRequest
from loopora.events import replay_run_snapshot, run_stream_id
from loopora.kernel import ActorRef, RunLifecycleStatus

from kernel_event_test_support import create_kernel_run


CREATED_RUN_SOURCE_SEQUENCE = 1
STARTED_RUN_SOURCE_SEQUENCE = 2
RESUMED_RUN_SOURCE_SEQUENCE = 3
PROJECTION_STORE_SOURCE_SEQUENCE = 7
CLOSED_RUN_SOURCE_SEQUENCE = 10


def _create_run(repository: LooporaRepository, tmp_path: Path) -> dict:
    return create_kernel_run(
        repository,
        tmp_path,
        {
            "run_id": "run_event_core",
            "loop_id": "loop_event_core",
            "loop_name": "Event Core Loop",
            "task": "Prove it.",
        },
    )


def test_run_creation_and_status_updates_are_replayable_domain_events(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    created_cache = repository.get_projection_record("run_snapshot", run["id"])
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="runner", id="headless")

    repository.update_run(run["id"], RunUpdate(status="running", started_at="2026-01-01T00:00:00+00:00"))
    engine.record_step_evidence(
        RunEngineRecordStepEvidenceRequest(
            run_id=run["id"],
            actor=actor,
            evidence_entry={
                "id": "ev_lifecycle_close",
                "step_id": "builder",
                "role_id": "builder",
                "claim": "Lifecycle closure proof exists.",
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
            verdict={"status": "passed", "source": "gatekeeper", "summary": "Lifecycle closure is proven."},
        )
    )
    repository.update_run(run["id"], RunUpdate(status="succeeded", finished_at="2026-01-01T00:01:00+00:00"))

    events = repository.list_domain_events(run_stream_id(run["id"]))
    snapshot = replay_run_snapshot(events)
    engine_snapshot = RepositoryRunEngine(repository).snapshot(run["id"])

    assert [event.event_type for event in events] == [
        "RunCreated",
        "RunStarted",
        "EvidenceSubmitted",
        "EvidenceAccepted",
        "EvidenceLinkedToTarget",
        "CoverageRecomputed",
        "VerdictRequested",
        "VerdictIssued",
        "VerdictAllowedClosure",
        "RunClosed",
    ]
    assert events[-3].causation_id == events[-4].event_id
    assert events[-2].causation_id == events[-3].event_id
    assert events[-1].causation_id == events[-3].event_id
    assert [event.sequence for event in events] == list(range(1, 11))
    assert snapshot.state.id == run["id"]
    assert snapshot.state.loop_id == run["loop_id"]
    assert snapshot.state.lifecycle_status == RunLifecycleStatus.CLOSED
    assert engine_snapshot.state.lifecycle_status == RunLifecycleStatus.CLOSED
    assert created_cache["source_sequence"] == CREATED_RUN_SOURCE_SEQUENCE
    assert created_cache["payload"]["lifecycle_status"] == "created"
    cached_snapshot = repository.get_projection_record("run_snapshot", run["id"])
    assert cached_snapshot["source_sequence"] == CLOSED_RUN_SOURCE_SEQUENCE
    assert cached_snapshot["payload"]["lifecycle_status"] == "closed"


def test_run_lifecycle_events_ignore_repeated_status_updates(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)

    repository.update_run(run["id"], RunUpdate(status="running", started_at="2026-01-01T00:00:00+00:00"))
    repository.update_run(run["id"], RunUpdate(status="running", current_iter=1, active_role="builder"))

    events = repository.list_domain_events(run_stream_id(run["id"]))
    cached_snapshot = repository.get_projection_record("run_snapshot", run["id"])

    assert [event.event_type for event in events] == ["RunCreated", "RunStarted"]
    assert cached_snapshot["source_sequence"] == STARTED_RUN_SOURCE_SEQUENCE
    assert cached_snapshot["payload"]["lifecycle_status"] == "running"


def test_run_lifecycle_events_distinguish_resume_from_initial_start(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)

    repository.update_run(run["id"], RunUpdate(status="awaiting_agent", current_iter=1, active_role="builder"))
    repository.update_run(run["id"], RunUpdate(status="running", active_role=""))

    events = repository.list_domain_events(run_stream_id(run["id"]))
    snapshot = replay_run_snapshot(events)
    cached_snapshot = repository.get_projection_record("run_snapshot", run["id"])

    assert [event.event_type for event in events] == ["RunCreated", "RunPausedForActor", "RunResumed"]
    assert snapshot.state.lifecycle_status == RunLifecycleStatus.RUNNING
    assert snapshot.state.pending_actor is None
    assert cached_snapshot["source_sequence"] == RESUMED_RUN_SOURCE_SEQUENCE
    assert cached_snapshot["payload"]["lifecycle_status"] == "running"


def test_projection_store_records_replay_source_sequence(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")

    record = repository.put_projection_record(
        "run_snapshot",
        "run_projection",
        source_sequence=PROJECTION_STORE_SOURCE_SEQUENCE,
        payload={"status": "closed"},
    )

    assert record["projection_name"] == "run_snapshot"
    assert record["projection_key"] == "run_projection"
    assert record["source_sequence"] == PROJECTION_STORE_SOURCE_SEQUENCE
    assert record["payload"] == {"status": "closed"}
