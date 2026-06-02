from __future__ import annotations

from pathlib import Path

from loopora.db import LooporaRepository
from loopora.engine import (
    RepositoryRunEngine,
    RunEngineClaimStepRequest,
    RunEngineCompleteIterationRequest,
    RunEngineStartIterationRequest,
    RunEngineSubmitStepRequest,
    RunnerStepInstructionRequest,
    runner_step_instruction,
)
from loopora.events import replay_run_snapshot, run_stream_id
from loopora.kernel import ActorRef, RunLifecycleStatus, StepResult, StepResultStatus

from kernel_event_test_support import create_kernel_run


ITERATION_STEP_COUNT = 2


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


def test_run_engine_step_instruction_events_drive_current_step_replay(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="agent", id="codex", adapter="codex")
    instruction = runner_step_instruction(
        RunnerStepInstructionRequest(
            run_id=run["id"],
            contract_ref="contract/run_contract.json",
            compiled_spec={"coverage_targets": [{"id": "done_when.proof"}]},
            iteration=1,
            step={"id": "builder", "role_id": "builder", "objective": "Build proof."},
            role={"id": "builder", "name": "Builder", "archetype": "builder"},
        )
    )

    engine.claim_step(RunEngineClaimStepRequest(instruction=instruction, pending_actor=actor))

    claimed = engine.snapshot(run["id"])
    assert claimed.state.lifecycle_status == RunLifecycleStatus.AWAITING_ACTOR
    assert claimed.state.current_step_id == "builder"
    assert claimed.state.current_iteration == 1
    assert claimed.state.pending_actor == actor

    engine.submit_step(
        RunEngineSubmitStepRequest(
            result=StepResult(
                run_id=run["id"],
                step_id="builder",
                iteration=1,
                actor=actor,
                status=StepResultStatus.COMPLETED,
                summary="Builder completed the proof.",
            )
        )
    )

    committed = engine.snapshot(run["id"])
    assert committed.state.current_step_id is None
    assert committed.state.pending_actor is None


def test_run_engine_records_iteration_lifecycle_events_idempotently(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="runner", id="headless")

    engine.start_iteration(RunEngineStartIterationRequest(run_id=run["id"], iteration=0, actor=actor, step_count=ITERATION_STEP_COUNT))
    engine.start_iteration(RunEngineStartIterationRequest(run_id=run["id"], iteration=0, actor=actor, step_count=ITERATION_STEP_COUNT))
    engine.complete_iteration(
        RunEngineCompleteIterationRequest(
            run_id=run["id"],
            iteration=0,
            actor=actor,
            completed_step_count=ITERATION_STEP_COUNT,
            reason="checkpointed",
        )
    )
    engine.complete_iteration(
        RunEngineCompleteIterationRequest(
            run_id=run["id"],
            iteration=0,
            actor=actor,
            completed_step_count=ITERATION_STEP_COUNT,
            reason="checkpointed",
        )
    )

    events = repository.list_domain_events(run_stream_id(run["id"]))
    snapshot = replay_run_snapshot(events)

    assert [event.event_type for event in events] == ["RunCreated", "IterationStarted", "IterationCompleted"]
    assert snapshot.state.current_iteration == 0
    assert events[-1].payload["completed_step_count"] == ITERATION_STEP_COUNT
