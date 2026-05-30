from __future__ import annotations

from loopora.events.envelope import EventEnvelope
from loopora.projections._event_replay_support import EVENT_REPLAY_PROJECTION_SCHEMA_VERSION, latest_event, latest_sequence


def replay_task_verdict_projection(events: list[EventEnvelope]) -> dict:
    event = latest_event(events, "VerdictIssued")
    if event is None:
        return {
            "schema_version": EVENT_REPLAY_PROJECTION_SCHEMA_VERSION,
            "kind": "event_replayed_task_verdict",
            "source_sequence": latest_sequence(events),
            "status": "not_evaluated",
            "source": "",
            "summary": "",
        }
    payload = event.payload
    projection = {
        "schema_version": EVENT_REPLAY_PROJECTION_SCHEMA_VERSION,
        "kind": "event_replayed_task_verdict",
        "source_sequence": event.sequence,
        "status": str(payload.get("status") or "not_evaluated"),
        "source": str(payload.get("source") or ""),
        "summary": str(payload.get("summary") or ""),
    }
    buckets = _dict_list_payload(payload.get("buckets"))
    if buckets:
        projection["buckets"] = buckets
    next_gap = _dict_entries(payload.get("next_gap"))
    if next_gap:
        projection["next_gap"] = next_gap
    return projection


def _dict_list_payload(value: object) -> dict:
    if not isinstance(value, dict):
        return {}
    result = {}
    for key, items in value.items():
        if not isinstance(items, list):
            continue
        result[str(key)] = _dict_entries(items)
    return result


def _dict_entries(value: object) -> list[dict]:
    return [dict(item) for item in list(value or []) if isinstance(item, dict)]
