from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from loopora.kernel.actors import ActorRef


class EvidenceStrength(StrEnum):
    STRONG = "strong"
    WEAK = "weak"
    BLOCKING = "blocking"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    kind: str
    label: str
    uri: str
    content_hash: str | None = None
    created_by_event_id: str = ""


@dataclass(frozen=True, slots=True)
class EvidenceTargetRef:
    target_id: str
    result: str = "covered"


@dataclass(frozen=True, slots=True)
class EvidenceClaim:
    claim: str
    method: str = ""
    result: str = ""
    supports: tuple[EvidenceTargetRef, ...] = field(default_factory=tuple)
    strength: EvidenceStrength = EvidenceStrength.WEAK
    artifact_refs: tuple[ArtifactRef, ...] = field(default_factory=tuple)
    residual_risk: str | None = None


@dataclass(frozen=True, slots=True)
class EvidenceEntry:
    id: str
    run_id: str
    source_step_id: str
    actor: ActorRef
    claim: str
    method: str
    result: str
    supports: tuple[EvidenceTargetRef, ...] = field(default_factory=tuple)
    strength: EvidenceStrength = EvidenceStrength.WEAK
    artifact_refs: tuple[ArtifactRef, ...] = field(default_factory=tuple)
    residual_risk: str | None = None
