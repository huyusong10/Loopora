from __future__ import annotations

from loopora.kernel import StepInstruction


def agent_step_view_projection(instruction: StepInstruction) -> dict:
    return {
        "kind": "agent_step_view",
        "run_id": instruction.run_id,
        "step_id": instruction.step_id,
        "iteration": instruction.iteration,
        "role": _role_projection(instruction),
        "objective": instruction.objective,
        "contract_ref": instruction.contract_ref,
        "evidence_scope": {
            "target_ids": list(instruction.evidence_scope.target_ids),
            "instructions": instruction.evidence_scope.instructions,
        },
        "action_policy": {
            "workspace": instruction.action_policy.workspace,
            "can_finish_run": instruction.action_policy.can_finish_run,
            "can_spawn_parallel": instruction.action_policy.can_spawn_parallel,
        },
        "output_contract": {
            "require_summary": instruction.output_contract.require_summary,
            "require_evidence_claims": instruction.output_contract.require_evidence_claims,
            "require_artifact_refs": instruction.output_contract.require_artifact_refs,
        },
    }


def _role_projection(instruction: StepInstruction) -> dict:
    return {
        "id": instruction.role.id,
        "name": instruction.role.name,
        "archetype": instruction.role.archetype,
        "responsibility": instruction.role.responsibility,
    }
