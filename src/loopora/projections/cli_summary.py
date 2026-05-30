from __future__ import annotations

from loopora.kernel import StepInstruction


def cli_summary_projection(instruction: StepInstruction) -> dict:
    return {
        "kind": "cli_summary",
        "run_id": instruction.run_id,
        "step_id": instruction.step_id,
        "iteration": instruction.iteration,
        "role_name": instruction.role.name,
        "role_archetype": instruction.role.archetype,
        "target_count": len(instruction.evidence_scope.target_ids),
        "can_finish_run": instruction.action_policy.can_finish_run,
    }


def cli_step_summary_projection(instruction: StepInstruction) -> dict:
    return {**cli_summary_projection(instruction), "kind": "cli_step_summary"}
