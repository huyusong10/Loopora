from pathlib import Path

from loopora.db import LooporaRepository
from loopora.engine import RunEngineClaimStepRequest, RunnerStepInstructionRequest, runner_step_instruction
from loopora.kernel import ActorRef

from kernel_event_test_support import create_kernel_run


def create_lifecycle_replay_run(repository: LooporaRepository, tmp_path: Path) -> dict:
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


def headless_runner_actor() -> ActorRef:
    return ActorRef(kind="runner", id="headless")


def codex_agent_actor() -> ActorRef:
    return ActorRef(kind="agent", id="codex", adapter="codex")


def claim_builder_step(engine, run_id: str, *, actor: ActorRef | None = None) -> ActorRef:
    pending_actor = actor or codex_agent_actor()
    engine.claim_step(
        RunEngineClaimStepRequest(
            instruction=runner_step_instruction(
                RunnerStepInstructionRequest(
                    run_id=run_id,
                    contract_ref="contract/run_contract.json",
                    compiled_spec={"coverage_targets": [{"id": "done_when.proof"}]},
                    iteration=1,
                    step={"id": "builder", "role_id": "builder", "objective": "Build proof."},
                    role={"id": "builder", "name": "Builder", "archetype": "builder"},
                )
            ),
            pending_actor=pending_actor,
        )
    )
    return pending_actor


__all__ = [
    "claim_builder_step",
    "codex_agent_actor",
    "create_lifecycle_replay_run",
    "headless_runner_actor",
]
