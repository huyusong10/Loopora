from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from loopora.kernel import ActionPolicy, EvidenceScope, RoleSpec, StepInstruction, StepOutputContract


@dataclass(frozen=True, slots=True)
class RunnerStepInstructionRequest:
    run_id: str
    contract_ref: str
    compiled_spec: Mapping[str, object]
    iteration: int
    step: Mapping[str, object]
    role: Mapping[str, object]


def runner_step_instruction(request: RunnerStepInstructionRequest) -> StepInstruction:
    step_id = _text(request.step.get("id"), fallback="step")
    role_id = _text(request.role.get("id") or request.step.get("role_id"), fallback="role")
    action_policy = _mapping(request.step.get("action_policy"))
    return StepInstruction(
        run_id=request.run_id,
        step_id=step_id,
        iteration=request.iteration,
        role=RoleSpec(
            id=role_id,
            name=_text(request.role.get("name"), fallback=role_id),
            archetype=_text(request.role.get("archetype")),
            responsibility=_text(request.role.get("responsibility") or request.role.get("description")),
        ),
        objective=_text(request.step.get("objective") or request.step.get("description") or request.step.get("prompt")),
        contract_ref=request.contract_ref,
        evidence_scope=EvidenceScope(
            target_ids=tuple(
                _text(target.get("id"))
                for target in _mapping_list(request.compiled_spec.get("coverage_targets"))
                if _text(target.get("id"))
            )
        ),
        action_policy=ActionPolicy(
            workspace=_text(action_policy.get("workspace"), fallback="read_only"),
            can_finish_run=bool(action_policy.get("can_finish_run") or request.step.get("can_finish_run")),
            can_spawn_parallel=bool(request.step.get("parallel_group")),
        ),
        output_contract=StepOutputContract(
            require_summary=True,
            require_evidence_claims=True,
            require_artifact_refs=False,
        ),
    )


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _mapping_list(value: object) -> list[Mapping[str, object]]:
    return [item for item in list(value or []) if isinstance(item, Mapping)]


def _text(value: object, *, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback
