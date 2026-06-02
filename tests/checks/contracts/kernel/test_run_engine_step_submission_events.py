from __future__ import annotations

from pathlib import Path

from loopora.db import LooporaRepository
from loopora.engine import RepositoryRunEngine, RunEngineSubmitStepRequest
from loopora.events import run_stream_id
from loopora.kernel import ActorRef, ArtifactRef, StepResult, StepResultStatus

from run_engine_step_submission_test_support import create_step_submission_run, step_submission_result


def test_run_engine_derives_runner_strategy_cursor_from_event_log(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = create_step_submission_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="runner", id="headless")

    engine.submit_step(
        RunEngineSubmitStepRequest(
            result=step_submission_result(run["id"], iteration=0, actor=actor, summary="Builder completed.")
        )
    )

    assert (
        engine.runner_step_index(
            run["id"],
            strategy_steps=[
                {"id": "builder", "role_id": "builder"},
                {"id": "gatekeeper", "role_id": "gatekeeper"},
            ],
            iteration=0,
            fallback_step_index=0,
        )
        == 1
    )


def test_run_engine_submit_step_records_submitted_accepted_and_committed_events(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = create_step_submission_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="agent", id="codex", adapter="codex")

    result = engine.submit_step(
        RunEngineSubmitStepRequest(
            result=StepResult(
                run_id=run["id"],
                step_id="builder",
                iteration=1,
                actor=actor,
                status=StepResultStatus.COMPLETED,
                summary="Builder completed the proof.",
                artifact_refs=(ArtifactRef(kind="workspace", label="report", uri="report.txt", content_hash="sha256:abc"),),
                blocking_items=("none",),
            )
        )
    )

    events = repository.list_domain_events(run_stream_id(run["id"]))
    artifacts = repository.list_artifact_index(run_id=run["id"])

    assert result.submitted_event.event_type == "StepSubmitted"
    assert result.accepted_event.event_type == "StepAccepted"
    assert result.committed_event.event_type == "StepCommitted"
    assert result.strategy_event is not None
    assert result.strategy_event.event_type == "StrategyAdvanced"
    assert [item.event_type for item in events[-4:]] == [
        "StepSubmitted",
        "StepAccepted",
        "StepCommitted",
        "StrategyAdvanced",
    ]
    assert events[-4].payload["summary"] == "Builder completed the proof."
    assert result.accepted_event.causation_id == result.submitted_event.event_id
    assert result.committed_event.causation_id == result.accepted_event.event_id
    assert result.strategy_event.causation_id == result.committed_event.event_id
    assert events[-2].event_id == result.committed_event.event_id
    assert events[-1].event_id == result.strategy_event.event_id
    assert artifacts[0]["loop_id"] == run["loop_id"]
    assert artifacts[0]["kind"] == "workspace"
    assert artifacts[0]["uri"] == "report.txt"
    assert artifacts[0]["content_hash"] == "sha256:abc"
    assert artifacts[0]["created_by_event_id"] == result.submitted_event.event_id
