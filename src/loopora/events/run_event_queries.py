from __future__ import annotations

from loopora.events.streams import run_stream_id
from loopora.structured_numbers import coerced_int


def list_run_events(repository, run_id: str):
    return repository.list_domain_events(run_stream_id(run_id))


def find_iteration_event(repository, run_id: str, event_type: str, iteration: int):
    return next(
        (
            event
            for event in list_run_events(repository, run_id)
            if event.event_type == event_type and coerced_int(event.payload.get("iteration"), default=-1) == iteration
        ),
        None,
    )
