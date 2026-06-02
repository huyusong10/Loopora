from __future__ import annotations

from typing import Any

from loopora.web_overviews import _format_timeline_event


def formatted_timeline_event(
    event_type: str,
    payload: Any,
    *,
    event_id: int = 1,
    role: str | None = None,
    created_at: str = "2026-05-05T00:00:00Z",
) -> dict:
    event = {
        "id": event_id,
        "event_type": event_type,
        "created_at": created_at,
        "payload": payload,
    }
    if role is not None:
        event["role"] = role
    return _format_timeline_event(event)
