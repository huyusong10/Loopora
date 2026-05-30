from __future__ import annotations

from loopora.events.envelope import EventEnvelope
from loopora.projections._event_replay_support import EVENT_REPLAY_PROJECTION_SCHEMA_VERSION, latest_sequence, ordered


def replay_evidence_ledger_projection(events: list[EventEnvelope]) -> dict:
    evidence_events = [event for event in ordered(events) if event.event_type == "EvidenceAccepted"]
    entries = [
        {
            "event_id": event.event_id,
            "sequence": event.sequence,
            "occurred_at": event.occurred_at,
            **dict(event.payload),
        }
        for event in evidence_events
    ]
    return {
        "schema_version": EVENT_REPLAY_PROJECTION_SCHEMA_VERSION,
        "kind": "event_replayed_evidence_ledger",
        "source_sequence": latest_sequence(events),
        "evidence_count": len(entries),
        "entries": entries,
    }
