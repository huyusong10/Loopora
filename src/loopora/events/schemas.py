from __future__ import annotations

LOOP_EVENT_TYPES = frozenset(
    {
        "LoopDraftCreated",
        "LoopContractCompiled",
        "LoopStrategyCompiled",
        "LoopReviewed",
        "LoopActivated",
        "LoopArchived",
    }
)

RUN_EVENT_TYPES = frozenset(
    {
        "RunCreated",
        "RunStarted",
        "RunPausedForActor",
        "RunResumed",
        "RunStopped",
        "RunFailed",
        "RunClosed",
    }
)

STEP_EVENT_TYPES = frozenset(
    {
        "StepPlanned",
        "StepClaimed",
        "StepInstructionIssued",
        "StepSubmitted",
        "StepSubmissionRejected",
        "StepAccepted",
        "StepCommitted",
    }
)

EVIDENCE_EVENT_TYPES = frozenset(
    {
        "EvidenceSubmitted",
        "EvidenceAccepted",
        "EvidenceRejected",
        "EvidenceLinkedToTarget",
        "CoverageRecomputed",
    }
)

VERDICT_EVENT_TYPES = frozenset(
    {
        "VerdictRequested",
        "VerdictIssued",
        "VerdictBlockedClosure",
        "VerdictAllowedClosure",
        "ResidualRiskAccepted",
    }
)

ITERATION_EVENT_TYPES = frozenset(
    {
        "IterationStarted",
        "IterationCompleted",
        "NextGapSelected",
        "StrategyAdvanced",
    }
)

CORE_EVENT_TYPES = (
    LOOP_EVENT_TYPES
    | RUN_EVENT_TYPES
    | STEP_EVENT_TYPES
    | EVIDENCE_EVENT_TYPES
    | VERDICT_EVENT_TYPES
    | ITERATION_EVENT_TYPES
)

CORE_EVENT_AGGREGATE_TYPES = {
    **{event_type: "loop" for event_type in LOOP_EVENT_TYPES},
    **{
        event_type: "run"
        for event_type in (
            RUN_EVENT_TYPES
            | STEP_EVENT_TYPES
            | EVIDENCE_EVENT_TYPES
            | VERDICT_EVENT_TYPES
            | ITERATION_EVENT_TYPES
        )
    },
}


def require_core_event_family(event_type: str, aggregate_type: str) -> None:
    expected_aggregate_type = CORE_EVENT_AGGREGATE_TYPES.get(event_type)
    if expected_aggregate_type is None:
        raise ValueError(f"unsupported core domain event type: {event_type}")
    if expected_aggregate_type != aggregate_type:
        raise ValueError(
            f"core domain event {event_type} requires aggregate_type {expected_aggregate_type}, got {aggregate_type}"
        )
