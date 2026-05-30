from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict

from loopora.kernel import ActionPolicy, EvidenceScope, RoleSpec, StepInstruction, StepOutputContract


def step_instruction_event_payload(instruction: StepInstruction) -> dict:
    return {
        "run_id": instruction.run_id,
        "step_id": instruction.step_id,
        "iteration": instruction.iteration,
        "role": asdict(instruction.role),
        "objective": instruction.objective,
        "contract_ref": instruction.contract_ref,
        "evidence_scope": asdict(instruction.evidence_scope),
        "action_policy": asdict(instruction.action_policy),
        "output_contract": asdict(instruction.output_contract),
    }


def step_instruction_from_event_payload(
    payload: Mapping[str, object],
    *,
    fallback_run_id: str = "",
) -> StepInstruction:
    role = _mapping(payload.get("role"))
    evidence_scope = _mapping(payload.get("evidence_scope"))
    action_policy = _mapping(payload.get("action_policy"))
    output_contract = _mapping(payload.get("output_contract"))
    return StepInstruction(
        run_id=str(payload.get("run_id") or fallback_run_id),
        step_id=str(payload.get("step_id") or ""),
        iteration=_safe_int(payload.get("iteration")),
        role=RoleSpec(
            id=str(role.get("id") or ""),
            name=str(role.get("name") or ""),
            archetype=str(role.get("archetype") or ""),
            responsibility=str(role.get("responsibility") or ""),
        ),
        objective=str(payload.get("objective") or ""),
        contract_ref=str(payload.get("contract_ref") or ""),
        evidence_scope=EvidenceScope(
            target_ids=tuple(str(item) for item in list(evidence_scope.get("target_ids") or []) if str(item).strip()),
            instructions=str(evidence_scope.get("instructions") or ""),
        ),
        action_policy=ActionPolicy(
            workspace=str(action_policy.get("workspace") or "read_only"),
            can_finish_run=bool(action_policy.get("can_finish_run")),
            can_spawn_parallel=bool(action_policy.get("can_spawn_parallel")),
        ),
        output_contract=StepOutputContract(
            require_summary=bool(output_contract.get("require_summary")),
            require_evidence_claims=bool(output_contract.get("require_evidence_claims")),
            require_artifact_refs=bool(output_contract.get("require_artifact_refs")),
        ),
    )


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _safe_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
