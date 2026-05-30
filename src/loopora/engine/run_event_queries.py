from __future__ import annotations

from loopora.events.streams import run_stream_id


def find_iteration_event(repository, run_id: str, event_type: str, iteration: int):
    return next(
        (
            event
            for event in repository.list_domain_events(run_stream_id(run_id))
            if event.event_type == event_type and _safe_int(event.payload.get("iteration"), default=-1) == iteration
        ),
        None,
    )


def _safe_int(value: object, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
