from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RoleSpec:
    id: str
    name: str
    archetype: str = ""
    responsibility: str = ""


@dataclass(frozen=True, slots=True)
class StrategyStep:
    id: str
    role_id: str
    objective: str = ""
    can_finish_run: bool = False
    parallel_group: str = ""


@dataclass(frozen=True, slots=True)
class EvidenceFlow:
    required_target_ids: tuple[str, ...] = field(default_factory=tuple)
    gatekeeper_step_id: str = ""


@dataclass(frozen=True, slots=True)
class IterationPolicy:
    max_iterations: int = 1
    max_step_retries: int = 1


@dataclass(frozen=True, slots=True)
class FinishPolicy:
    require_verdict_pass: bool = True
    allow_residual_risk: bool = True


@dataclass(frozen=True, slots=True)
class LoopStrategy:
    id: str
    roles: tuple[RoleSpec, ...] = field(default_factory=tuple)
    steps: tuple[StrategyStep, ...] = field(default_factory=tuple)
    evidence_flow: EvidenceFlow = field(default_factory=EvidenceFlow)
    iteration_policy: IterationPolicy = field(default_factory=IterationPolicy)
    finish_policy: FinishPolicy = field(default_factory=FinishPolicy)

    def role_by_id(self) -> dict[str, RoleSpec]:
        return {role.id: role for role in self.roles}
