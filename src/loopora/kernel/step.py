from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from loopora.kernel.actors import ActorRef
from loopora.kernel.evidence import ArtifactRef, EvidenceClaim
from loopora.kernel.strategy import RoleSpec


class StepResultStatus(StrEnum):
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class EvidenceScope:
    target_ids: tuple[str, ...] = field(default_factory=tuple)
    instructions: str = ""


@dataclass(frozen=True, slots=True)
class ActionPolicy:
    workspace: str = "read_only"
    can_finish_run: bool = False
    can_spawn_parallel: bool = False


@dataclass(frozen=True, slots=True)
class StepOutputContract:
    require_summary: bool = True
    require_evidence_claims: bool = True
    require_artifact_refs: bool = False


@dataclass(frozen=True, slots=True)
class StepInstruction:
    run_id: str
    step_id: str
    iteration: int
    role: RoleSpec
    objective: str
    contract_ref: str
    evidence_scope: EvidenceScope = field(default_factory=EvidenceScope)
    action_policy: ActionPolicy = field(default_factory=ActionPolicy)
    output_contract: StepOutputContract = field(default_factory=StepOutputContract)


@dataclass(frozen=True, slots=True)
class StepResult:
    run_id: str
    step_id: str
    iteration: int
    actor: ActorRef
    status: StepResultStatus
    summary: str
    evidence_claims: tuple[EvidenceClaim, ...] = field(default_factory=tuple)
    artifact_refs: tuple[ArtifactRef, ...] = field(default_factory=tuple)
    blocking_items: tuple[str, ...] = field(default_factory=tuple)
    residual_risks: tuple[str, ...] = field(default_factory=tuple)
