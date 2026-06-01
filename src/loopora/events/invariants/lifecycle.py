from __future__ import annotations

import sqlite3

from loopora.events.schemas import RUN_EVENT_TYPES, RUN_TERMINAL_EVENT_TYPES
from loopora.events.store import DomainEventAppendRequest


def require_run_lifecycle_append_allowed(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.aggregate_type != "run" or request.event_type not in RUN_EVENT_TYPES:
        return
    require_non_success_terminal_reason(request)
    placeholders = ",".join("?" for _item in RUN_TERMINAL_EVENT_TYPES)
    row = connection.execute(
        f"""
        SELECT event_type FROM event_store
        WHERE stream_id = ? AND event_type IN ({placeholders})
        ORDER BY sequence DESC
        LIMIT 1
        """,
        (request.stream_id, *sorted(RUN_TERMINAL_EVENT_TYPES)),
    ).fetchone()
    if row is not None:
        raise ValueError(
            "terminal run stream cannot append lifecycle event "
            f"{request.event_type} after {row['event_type']}"
        )


def require_non_success_terminal_reason(request: DomainEventAppendRequest) -> None:
    if request.event_type not in {"RunStopped", "RunFailed"}:
        return
    payload = request.payload or {}
    if not str(payload.get("reason") or "").strip():
        raise ValueError(f"{request.event_type} requires reason")
