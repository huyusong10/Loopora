from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from loopora.kernel.evidence import ArtifactRef


class EvidenceTargetStatus(StrEnum):
    MISSING = "missing"
    WEAK = "weak"
    COVERED = "covered"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class EvidenceTargetState:
    target_id: str
    label: str
    required: bool
    status: EvidenceTargetStatus = EvidenceTargetStatus.MISSING
    reason: str = ""
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    artifact_refs: tuple[ArtifactRef, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class EvidenceGap:
    target_id: str
    label: str
    status: EvidenceTargetStatus
    required: bool
    reason: str


@dataclass(frozen=True, slots=True)
class CoverageState:
    run_id: str
    target_states: tuple[EvidenceTargetState, ...] = field(default_factory=tuple)
    top_gaps: tuple[EvidenceGap, ...] = field(default_factory=tuple)
    residual_risks: tuple[str, ...] = field(default_factory=tuple)
