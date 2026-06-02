from __future__ import annotations

from pathlib import Path

from loopora.db import LooporaRepository
from loopora.engine import RunnerStepInstructionRequest
from loopora.kernel import ActorRef, StepResult, StepResultStatus

from kernel_event_test_support import create_kernel_run


def create_step_submission_run(repository: LooporaRepository, tmp_path: Path) -> dict:
    return create_kernel_run(
        repository,
        tmp_path,
        {
            "run_id": "run_step_submission",
            "loop_id": "loop_step_submission",
            "loop_name": "Step Submission Loop",
            "task": "Prove it.",
        },
    )


def step_submission_result(run_id: str, *, actor: ActorRef, **overrides) -> StepResult:
    return StepResult(
        run_id=run_id,
        step_id=overrides.get("step_id", "builder"),
        iteration=overrides.get("iteration", 1),
        actor=actor,
        status=StepResultStatus.COMPLETED,
        summary=overrides.get("summary", "Builder completed the proof."),
    )


def step_submission_instruction(run_id: str, *, step_id: str = "builder") -> RunnerStepInstructionRequest:
    return RunnerStepInstructionRequest(
        run_id=run_id,
        contract_ref="contract/run_contract.json",
        compiled_spec={"coverage_targets": [{"id": "done_when.proof"}]},
        iteration=1,
        step={"id": step_id, "role_id": "builder", "objective": "Build proof."},
        role={"id": "builder", "name": "Builder", "archetype": "builder"},
    )
