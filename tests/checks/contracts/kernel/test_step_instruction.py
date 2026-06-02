from __future__ import annotations

from loopora.engine import RunnerStepInstructionRequest, runner_step_instruction


KERNEL_STEP_ITERATION = 2


def test_runner_step_instruction_is_core_next_step_not_surface_capsule() -> None:
    instruction = runner_step_instruction(
        RunnerStepInstructionRequest(
            run_id="run_kernel",
            contract_ref="contract/run_contract.json",
            compiled_spec={
                "coverage_targets": [
                    {"id": "done_when.permission", "required": True},
                    {"id": "gatekeeper.finish", "required": True},
                ]
            },
            iteration=KERNEL_STEP_ITERATION,
            step={
                "id": "gatekeeper",
                "role_id": "gatekeeper",
                "objective": "Judge evidence.",
                "action_policy": {"can_finish_run": True},
            },
            role={"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper"},
        )
    )

    assert instruction.run_id == "run_kernel"
    assert instruction.step_id == "gatekeeper"
    assert instruction.iteration == KERNEL_STEP_ITERATION
    assert instruction.role.archetype == "gatekeeper"
    assert instruction.evidence_scope.target_ids == ("done_when.permission", "gatekeeper.finish")
    assert instruction.action_policy.can_finish_run is True
