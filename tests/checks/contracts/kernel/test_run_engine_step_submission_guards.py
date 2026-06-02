from __future__ import annotations

from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.engine import (
    RepositoryRunEngine,
    RunEngineClaimRunnerStepRequest,
    RunEngineClaimStepRequest,
    RunEngineSubmitStepRequest,
    RunnerStepInstructionRequest,
    runner_step_instruction,
)
from loopora.events import run_stream_id
from loopora.kernel import ActorRef

from run_engine_step_submission_test_support import (
    create_step_submission_run,
    step_submission_instruction,
    step_submission_result,
)


def test_run_engine_rejects_step_result_that_does_not_match_current_instruction(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = create_step_submission_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="agent", id="codex", adapter="codex")

    engine.claim_step(
        RunEngineClaimStepRequest(
            instruction=runner_step_instruction(step_submission_instruction(run["id"])),
            pending_actor=actor,
        )
    )

    with pytest.raises(ValueError, match="does not match current StepInstruction"):
        engine.submit_step(
            RunEngineSubmitStepRequest(
                result=step_submission_result(
                    run["id"],
                    step_id="gatekeeper",
                    actor=actor,
                    summary="Stale result for a different step.",
                )
            )
        )

    events = repository.list_domain_events(run_stream_id(run["id"]))
    assert [event.event_type for event in events[-3:]] == ["StepPlanned", "StepClaimed", "StepInstructionIssued"]


def test_run_engine_rejects_duplicate_step_result_commit(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = create_step_submission_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="runner", id="headless")
    request = RunEngineSubmitStepRequest(result=step_submission_result(run["id"], actor=actor))

    engine.submit_step(request)

    with pytest.raises(ValueError, match="already committed"):
        engine.submit_step(request)

    assert [event.event_type for event in repository.list_domain_events(run_stream_id(run["id"]))] == [
        "RunCreated",
        "StepSubmitted",
        "StepAccepted",
        "StepCommitted",
        "StrategyAdvanced",
    ]


def test_run_engine_accepts_open_parallel_step_result_when_current_projection_points_to_peer(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = create_step_submission_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="runner", id="headless")

    for step_id in ("inspect_a", "inspect_b"):
        engine.claim_runner_step(
            RunEngineClaimRunnerStepRequest(
                instruction=runner_step_instruction(
                    RunnerStepInstructionRequest(
                        run_id=run["id"],
                        contract_ref="contract/run_contract.json",
                        compiled_spec={"coverage_targets": [{"id": "done_when.proof"}]},
                        iteration=1,
                        step={"id": step_id, "role_id": "inspector", "objective": "Inspect proof.", "parallel_group": "review"},
                        role={"id": "inspector", "name": "Inspector", "archetype": "inspector"},
                    )
                ),
                pending_actor=actor,
            )
        )

    result = engine.submit_step(
        RunEngineSubmitStepRequest(
            result=step_submission_result(
                run["id"],
                step_id="inspect_a",
                actor=actor,
                summary="First parallel inspector completed.",
            )
        )
    )

    assert result.committed_event.payload["step_id"] == "inspect_a"
    assert [event.event_type for event in repository.list_domain_events(run_stream_id(run["id"]))[-4:]] == [
        "StepSubmitted",
        "StepAccepted",
        "StepCommitted",
        "StrategyAdvanced",
    ]
