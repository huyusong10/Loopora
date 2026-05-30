from __future__ import annotations

from dataclasses import dataclass

from loopora.events.envelope import EventEnvelope


@dataclass(frozen=True, slots=True)
class StepSubmissionEventsResult:
    submitted_event: EventEnvelope
    committed_event: EventEnvelope


@dataclass(frozen=True, slots=True)
class StepEvidenceEventsResult:
    evidence_event: EventEnvelope
    coverage_event: EventEnvelope
