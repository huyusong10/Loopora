from __future__ import annotations

from loopora.events.envelope import EventEnvelope
from loopora.projections._event_replay_support import EVENT_REPLAY_PROJECTION_SCHEMA_VERSION, latest_event, latest_sequence, safe_int


def replay_coverage_projection(events: list[EventEnvelope]) -> dict:
    event = latest_event(events, "CoverageRecomputed")
    if event is None:
        return {
            "schema_version": EVENT_REPLAY_PROJECTION_SCHEMA_VERSION,
            "kind": "event_replayed_coverage",
            "source_sequence": latest_sequence(events),
            "status": "pending",
            "target_count": 0,
            "covered_target_count": 0,
            "weak_target_count": 0,
            "missing_target_count": 0,
            "blocked_target_count": 0,
            "top_gaps": [],
        }
    payload = event.payload
    return {
        "schema_version": EVENT_REPLAY_PROJECTION_SCHEMA_VERSION,
        "kind": "event_replayed_coverage",
        "source_sequence": event.sequence,
        "status": str(payload.get("status") or "pending"),
        "target_count": safe_int(payload.get("target_count")),
        "covered_target_count": safe_int(payload.get("covered_target_count")),
        "weak_target_count": safe_int(payload.get("weak_target_count")),
        "missing_target_count": safe_int(payload.get("missing_target_count")),
        "blocked_target_count": safe_int(payload.get("blocked_target_count")),
        "top_gaps": [dict(item) for item in list(payload.get("top_gaps") or []) if isinstance(item, dict)],
    }
