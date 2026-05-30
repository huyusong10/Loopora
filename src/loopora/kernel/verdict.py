from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from loopora.kernel.coverage import EvidenceGap


class VerdictStatus(StrEnum):
    NOT_EVALUATED = "not_evaluated"
    CONTINUE_REQUIRED = "continue_required"
    BLOCKED = "blocked"
    PASSED = "passed"
    PASSED_WITH_RESIDUAL_RISK = "passed_with_residual_risk"


class VerdictSource(StrEnum):
    SYSTEM = "system"
    GATEKEEPER = "gatekeeper"
    HUMAN = "human"


@dataclass(frozen=True, slots=True)
class VerdictBuckets:
    proven: tuple[str, ...] = field(default_factory=tuple)
    weak: tuple[str, ...] = field(default_factory=tuple)
    unproven: tuple[str, ...] = field(default_factory=tuple)
    blocking: tuple[str, ...] = field(default_factory=tuple)
    residual_risk: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Verdict:
    run_id: str
    status: VerdictStatus
    source: VerdictSource
    summary: str
    buckets: VerdictBuckets = field(default_factory=VerdictBuckets)
    next_gap: tuple[EvidenceGap, ...] = field(default_factory=tuple)
