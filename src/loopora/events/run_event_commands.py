from __future__ import annotations

from loopora.events.append_requests import RunEventAppend, append_run_event
from loopora.events.envelope import EventEnvelope
from loopora.events.projection_cache import rebuild_run_projection_cache


def append_run_event_and_rebuild_projection_cache(repository, request: RunEventAppend) -> EventEnvelope:
    event = append_run_event(repository, request)
    rebuild_run_projection_cache(repository, request.run_id)
    return event
