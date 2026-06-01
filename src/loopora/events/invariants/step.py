from __future__ import annotations

from loopora.events.store import DomainEventAppendRequest


def require_step_claim_event_identity(request: DomainEventAppendRequest) -> None:
    if request.aggregate_type != "run" or request.event_type not in {"StepPlanned", "StepClaimed", "StepInstructionIssued"}:
        return
    payload = request.payload or {}
    if not str(payload.get("step_id") or "").strip():
        raise ValueError(f"{request.event_type} requires step_id")
    if payload.get("iteration") is None or not str(payload.get("iteration")).strip():
        raise ValueError(f"{request.event_type} requires iteration")
    if request.event_type == "StepPlanned":
        return
    if not isinstance(payload.get("pending_actor"), dict):
        raise ValueError(f"{request.event_type} requires pending_actor")


def require_step_result_event_identity(request: DomainEventAppendRequest) -> None:
    if request.aggregate_type != "run" or request.event_type not in {
        "StepSubmitted",
        "StepAccepted",
        "StepSubmissionRejected",
        "StepCommitted",
    }:
        return
    payload = request.payload or {}
    if not str(payload.get("step_id") or "").strip():
        raise ValueError(f"{request.event_type} requires step_id")
    if payload.get("iteration") is None or not str(payload.get("iteration")).strip():
        raise ValueError(f"{request.event_type} requires iteration")
