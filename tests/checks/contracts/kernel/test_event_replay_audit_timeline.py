from __future__ import annotations

from pathlib import Path

from loopora.db import LooporaRepository
from loopora.engine import (
    RepositoryRunEngine,
    RunEngineCompleteIterationRequest,
    RunEngineStartIterationRequest,
)
from loopora.events.projection_cache import replay_run_projections
from loopora.kernel import ActorRef

from kernel_event_test_support import create_kernel_run


def _create_run(repository: LooporaRepository, tmp_path: Path) -> dict:
    return create_kernel_run(
        repository,
        tmp_path,
        {
            "run_id": "run_audit_timeline_projection",
            "loop_id": "loop_audit_timeline_projection",
            "loop_name": "Audit Timeline Projection Loop",
            "task": "Prove audit timeline projection.",
        },
    )


def test_event_replayed_audit_timeline_includes_iteration_lifecycle(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="runner", id="headless")

    engine.start_iteration(RunEngineStartIterationRequest(run_id=run["id"], iteration=0, actor=actor, step_count=2))
    engine.complete_iteration(
        RunEngineCompleteIterationRequest(
            run_id=run["id"],
            iteration=0,
            actor=actor,
            completed_step_count=2,
            reason="checkpointed",
        )
    )

    timeline = replay_run_projections(repository, run["id"])["audit_timeline"]

    assert [event["event_type"] for event in timeline["events"][-2:]] == ["IterationStarted", "IterationCompleted"]
    assert timeline["events"][-1]["summary"] == "checkpointed"
