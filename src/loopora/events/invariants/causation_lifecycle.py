from __future__ import annotations

import sqlite3

from loopora.events.invariants.common import PASSING_VERDICT_STATUSES, json_dict, latest_event_row
from loopora.events.store import DomainEventAppendRequest


def require_run_closed_causation_references_passing_verdict(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.aggregate_type != "run" or request.event_type != "RunClosed":
        return
    if not request.causation_id:
        if (request.payload or {}).get("legacy_compat") is True:
            return
        raise ValueError("RunClosed requires causation_id to reference latest passing VerdictIssued")
    row = connection.execute(
        """
        SELECT event_id, event_type, payload_json FROM event_store
        WHERE stream_id = ? AND event_id = ?
        LIMIT 1
        """,
        (request.stream_id, request.causation_id),
    ).fetchone()
    if row is None or row["event_type"] != "VerdictIssued":
        raise ValueError("RunClosed causation_id must reference VerdictIssued")
    payload = json_dict(row["payload_json"])
    status = str(payload.get("status") or "").strip().lower()
    if status not in PASSING_VERDICT_STATUSES:
        raise ValueError("RunClosed causation_id must reference passing VerdictIssued")
    latest_row = latest_event_row(connection, request.stream_id, "VerdictIssued")
    if latest_row is not None and request.causation_id != latest_row["event_id"]:
        raise ValueError("RunClosed causation_id must reference latest VerdictIssued")
