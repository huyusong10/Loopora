from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ResidualRiskPolicy(StrEnum):
    DISALLOW = "disallow"
    ALLOW_MANAGED = "allow_managed"
    ALLOW_ANY = "allow_any"


@dataclass(frozen=True, slots=True)
class DoneCriterion:
    id: str
    title: str
    details: str = ""
    required: bool = True


@dataclass(frozen=True, slots=True)
class EvidenceExpectation:
    id: str
    label: str
    method: str = ""
    required: bool = False


@dataclass(frozen=True, slots=True)
class EvidenceTarget:
    id: str
    kind: str
    label: str
    text: str = ""
    required: bool = False


@dataclass(frozen=True, slots=True)
class LoopContract:
    id: str
    task: str
    done_when: tuple[DoneCriterion, ...] = field(default_factory=tuple)
    guardrails: tuple[str, ...] = field(default_factory=tuple)
    fake_done: tuple[str, ...] = field(default_factory=tuple)
    evidence_needed: tuple[EvidenceExpectation, ...] = field(default_factory=tuple)
    blocking_risks: tuple[str, ...] = field(default_factory=tuple)
    residual_risk_policy: ResidualRiskPolicy = ResidualRiskPolicy.ALLOW_MANAGED
    evidence_targets: tuple[EvidenceTarget, ...] = field(default_factory=tuple)

    def target_by_id(self) -> dict[str, EvidenceTarget]:
        return {target.id: target for target in self.evidence_targets}
