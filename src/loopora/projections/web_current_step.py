from __future__ import annotations

from loopora.kernel import StepInstruction


def web_current_step_projection(instruction: StepInstruction) -> dict:
    return {
        "kind": "web_current_step",
        "identity": {
            "run_id": instruction.run_id,
            "step_id": instruction.step_id,
            "iteration": instruction.iteration,
        },
        "role": _role_projection(instruction),
        "objective": instruction.objective,
        "evidence_target_ids": list(instruction.evidence_scope.target_ids),
        "can_finish_run": instruction.action_policy.can_finish_run,
    }


def _role_projection(instruction: StepInstruction) -> dict:
    return {
        "id": instruction.role.id,
        "name": instruction.role.name,
        "archetype": instruction.role.archetype,
        "responsibility": instruction.role.responsibility,
    }
