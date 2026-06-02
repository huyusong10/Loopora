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

RUN_TERMINAL_EVENT_TYPES = frozenset({"RunClosed", "RunStopped", "RunFailed"})

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
    **dict.fromkeys(LOOP_EVENT_TYPES, "loop"),
    **dict.fromkeys(
        (
            RUN_EVENT_TYPES
            | STEP_EVENT_TYPES
            | EVIDENCE_EVENT_TYPES
            | VERDICT_EVENT_TYPES
            | ITERATION_EVENT_TYPES
        ),
        "run",
    ),
}


def require_core_event_family(event_type: str, aggregate_type: str) -> None:
    expected_aggregate_type = CORE_EVENT_AGGREGATE_TYPES.get(event_type)
    if expected_aggregate_type is None:
        raise ValueError(f"unsupported core domain event type: {event_type}")
    if expected_aggregate_type != aggregate_type:
        raise ValueError(
            f"core domain event {event_type} requires aggregate_type {expected_aggregate_type}, got {aggregate_type}"
        )


def core_event_stream_id(*, event_type: str, aggregate_type: str, aggregate_id: str) -> str:
    require_core_event_family(event_type, aggregate_type)
    if aggregate_type == "loop":
        return f"loop:{aggregate_id}"
    return f"run:{aggregate_id}"


def require_core_event_stream_boundary(
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    stream_id: str,
) -> None:
    expected_stream_id = core_event_stream_id(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
    )
    if stream_id != expected_stream_id:
        raise ValueError(f"core domain event {event_type} requires stream_id {expected_stream_id}, got {stream_id}")


def require_core_event_payload_identity(*, aggregate_type: str, aggregate_id: str, payload: dict) -> None:
    identity_field = {"loop": "loop_id", "run": "run_id"}.get(aggregate_type)
    if identity_field is None or identity_field not in payload:
        return
    payload_id = str(payload.get(identity_field) or "").strip()
    if payload_id != aggregate_id:
        raise ValueError(f"{aggregate_type} event payload {identity_field} must match aggregate_id")
