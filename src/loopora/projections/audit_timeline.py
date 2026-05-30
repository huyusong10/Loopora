from __future__ import annotations

from loopora.events.envelope import EventEnvelope
from loopora.projections._event_replay_support import EVENT_REPLAY_PROJECTION_SCHEMA_VERSION, latest_sequence, ordered


def replay_audit_timeline_projection(events: list[EventEnvelope]) -> dict:
    rows = [
        {
            "event_id": event.event_id,
            "sequence": event.sequence,
            "event_type": event.event_type,
            "occurred_at": event.occurred_at,
            "actor": event.actor.to_dict(),
            "summary": _event_summary(event),
        }
        for event in ordered(events)
    ]
    return {
        "schema_version": EVENT_REPLAY_PROJECTION_SCHEMA_VERSION,
        "kind": "event_replayed_audit_timeline",
        "source_sequence": latest_sequence(events),
        "event_count": len(rows),
        "events": rows,
    }


def _event_summary(event: EventEnvelope) -> str:
    payload = event.payload
    summary_fields = {
        "EvidenceAccepted": ("claim", "evidence_id"),
        "CoverageRecomputed": ("status",),
        "VerdictIssued": ("summary", "status"),
        "StepInstructionIssued": ("step_id",),
        "StepSubmitted": ("summary", "status"),
        "StepAccepted": ("result_status", "step_id"),
        "StepCommitted": ("result_status", "step_id"),
        "IterationStarted": ("iteration",),
        "IterationCompleted": ("reason", "iteration"),
    }
    for field in summary_fields.get(event.event_type, ("status", "reason")):
        value = str(payload.get(field) or "").strip()
        if value:
            return value
    if event.event_type == "CoverageRecomputed":
        return "coverage recomputed"
    return str(payload.get("status") or payload.get("reason") or "").strip()
