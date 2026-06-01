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
from loopora.kernel import ActorRef, ArtifactRef, StepResult, StepResultStatus


def _create_run(repository: LooporaRepository, tmp_path: Path) -> dict:
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    spec_path = tmp_path / "spec.md"
    spec_markdown = "# Task\n\nProve it.\n"
    spec_path.write_text(spec_markdown, encoding="utf-8")
    loop = repository.create_loop(
        {
            "id": "loop_step_submission",
            "name": "Step Submission Loop",
            "workdir": str(workdir),
            "spec_path": str(spec_path),
            "spec_markdown": spec_markdown,
            "compiled_spec": {"goal": "Prove it.", "checks": [{"id": "proof", "title": "Proof"}]},
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
            "max_iters": 1,
            "max_role_retries": 1,
            "delta_threshold": 0.1,
            "trigger_window": 1,
            "regression_window": 1,
            "role_models": {},
        }
    )
    run_dir = workdir / ".loopora" / "runs" / "run_step_submission"
    run_dir.mkdir(parents=True)
    return repository.create_run(
        {
            "id": "run_step_submission",
            "loop_id": loop["id"],
            "workdir": str(workdir),
            "spec_path": str(spec_path),
            "spec_markdown": spec_markdown,
            "compiled_spec": {"goal": "Prove it.", "checks": [{"id": "proof", "title": "Proof"}]},
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
            "max_iters": 1,
            "max_role_retries": 1,
            "delta_threshold": 0.1,
            "trigger_window": 1,
            "regression_window": 1,
            "role_models": {},
            "status": "queued",
            "runs_dir": str(run_dir),
        }
    )


def _step_result(run_id: str, *, actor: ActorRef, **overrides) -> StepResult:
    return StepResult(
        run_id=run_id,
        step_id=overrides.get("step_id", "builder"),
        iteration=overrides.get("iteration", 1),
        actor=actor,
        status=StepResultStatus.COMPLETED,
        summary=overrides.get("summary", "Builder completed the proof."),
    )


def _instruction(run_id: str, *, step_id: str = "builder") -> RunnerStepInstructionRequest:
    return RunnerStepInstructionRequest(
        run_id=run_id,
        contract_ref="contract/run_contract.json",
        compiled_spec={"coverage_targets": [{"id": "done_when.proof"}]},
        iteration=1,
        step={"id": step_id, "role_id": "builder", "objective": "Build proof."},
        role={"id": "builder", "name": "Builder", "archetype": "builder"},
    )


def test_run_engine_claim_runner_step_freezes_step_instruction(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="runner", id="headless")

    claimed = engine.claim_runner_step(
        RunEngineClaimRunnerStepRequest(
            instruction=runner_step_instruction(_instruction(run["id"])),
            pending_actor=actor,
        )
    )

    events = repository.list_domain_events(run_stream_id(run["id"]))
    planned_event = events[-3]
    claimed_event = events[-2]
    event = events[-1]

    assert claimed.instruction.step_id == "builder"
    assert claimed.instruction.evidence_scope.target_ids == ("done_when.proof",)
    assert planned_event.event_type == "StepPlanned"
    assert planned_event.payload == {"run_id": run["id"], "step_id": "builder", "iteration": 1}
    assert claimed_event.event_type == "StepClaimed"
    assert claimed_event.causation_id == planned_event.event_id
    assert claimed_event.payload == {
        "run_id": run["id"],
        "step_id": "builder",
        "iteration": 1,
        "pending_actor": actor.to_dict(),
    }
    assert event.event_type == "StepInstructionIssued"
    assert event.causation_id == claimed_event.event_id
    assert event.payload["step_id"] == claimed.instruction.step_id
    assert event.payload["pending_actor"] == actor.to_dict()


def test_run_engine_derives_runner_strategy_cursor_from_event_log(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="runner", id="headless")

    engine.submit_step(
        RunEngineSubmitStepRequest(result=_step_result(run["id"], iteration=0, actor=actor, summary="Builder completed."))
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
    run = _create_run(repository, tmp_path)
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


def test_run_engine_rejects_step_result_that_does_not_match_current_instruction(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="agent", id="codex", adapter="codex")

    engine.claim_step(
        RunEngineClaimStepRequest(
            instruction=runner_step_instruction(_instruction(run["id"])),
            pending_actor=actor,
        )
    )

    with pytest.raises(ValueError, match="does not match current StepInstruction"):
        engine.submit_step(
            RunEngineSubmitStepRequest(
                result=_step_result(
                    run["id"],
                    step_id="gatekeeper",
                    actor=actor,
                    summary="Stale result for a different step.",
                )
            )
        )

    events = repository.list_domain_events(run_stream_id(run["id"]))
    assert [event.event_type for event in events[-3:]] == ["StepPlanned", "StepClaimed", "StepInstructionIssued"]


def test_run_engine_claim_step_returns_step_instruction(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="agent", id="codex", adapter="codex")
    instruction = runner_step_instruction(_instruction(run["id"]))

    claimed = engine.claim_step(
        RunEngineClaimStepRequest(
            instruction=instruction,
            pending_actor=actor,
        )
    )

    assert claimed == instruction
    assert repository.list_domain_events(run_stream_id(run["id"]))[-1].event_type == "StepInstructionIssued"


def test_run_engine_rejects_duplicate_step_result_commit(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="runner", id="headless")
    request = RunEngineSubmitStepRequest(result=_step_result(run["id"], actor=actor))

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
    run = _create_run(repository, tmp_path)
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
            result=_step_result(
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
