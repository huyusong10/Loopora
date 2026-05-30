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
