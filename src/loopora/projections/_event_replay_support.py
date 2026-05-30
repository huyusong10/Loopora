from __future__ import annotations

from loopora.events.envelope import EventEnvelope


EVENT_REPLAY_PROJECTION_SCHEMA_VERSION = 1


def latest_event(events: list[EventEnvelope], event_type: str) -> EventEnvelope | None:
    return next((event for event in reversed(ordered(events)) if event.event_type == event_type), None)


def latest_sequence(events: list[EventEnvelope]) -> int:
    return max((event.sequence for event in events), default=0)


def ordered(events: list[EventEnvelope]) -> list[EventEnvelope]:
    return sorted(events, key=lambda event: event.sequence)


def safe_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
