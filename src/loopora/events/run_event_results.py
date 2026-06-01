from __future__ import annotations

from dataclasses import dataclass

from loopora.events.envelope import EventEnvelope


@dataclass(frozen=True, slots=True)
class StepSubmissionEventsResult:
    submitted_event: EventEnvelope
    accepted_event: EventEnvelope
    committed_event: EventEnvelope
    strategy_event: EventEnvelope | None = None


@dataclass(frozen=True, slots=True)
class StepClaimEventsResult:
    planned_event: EventEnvelope
    claimed_event: EventEnvelope
    instruction_event: EventEnvelope


@dataclass(frozen=True, slots=True)
class StepEvidenceEventsResult:
    evidence_event: EventEnvelope
    coverage_event: EventEnvelope
    submitted_event: EventEnvelope | None = None
    linked_event: EventEnvelope | None = None


@dataclass(frozen=True, slots=True)
class VerdictEventsResult:
    requested_event: EventEnvelope
    issued_event: EventEnvelope
    closure_event: EventEnvelope
    residual_risk_event: EventEnvelope | None = None
    next_gap_event: EventEnvelope | None = None
