from __future__ import annotations

import json
from collections.abc import Mapping

from loopora.events.append_requests import RunEventAppend, append_run_event

PASSING_VERDICT_STATUSES = frozenset({"passed", "passed_with_residual_risk"})


def append_run_created_event_for_connection(event_repository, connection, payload: dict) -> None:
    append_run_event(
        event_repository.domain_event_transaction_for_connection(connection),
        RunEventAppend(
            run_id=payload["id"],
            event_type="RunCreated",
            payload={
                "run_id": payload["id"],
                "loop_id": payload["loop_id"],
                "status": payload["status"],
                "workdir": payload["workdir"],
            },
        ),
    )


def append_run_lifecycle_event_for_connection(
    event_repository,
    connection,
    row,
    updates: Mapping[str, object],
    *,
    previous_status: str,
) -> bool:
    if "status" not in updates:
        return False
    next_status = str(updates.get("status") or "")
    if next_status == previous_status:
        return False
    event_type = _domain_event_type_for_transition(previous_status=previous_status, next_status=next_status)
    if not event_type:
        return False
    causation_id = _run_lifecycle_causation_id_for_connection(
        connection,
        stream_id=f"run:{row['id']}",
        event_type=event_type,
    )
    append_run_event(
        event_repository.domain_event_transaction_for_connection(connection),
        RunEventAppend(
            run_id=row["id"],
            event_type=event_type,
            payload={
                "run_id": row["id"],
                "loop_id": row["loop_id"],
                "status": next_status,
                "current_iter": int(row["current_iter"] or 0),
                "active_role": row["active_role"] or "",
            },
            causation_id=causation_id,
        ),
    )
    return True


def _domain_event_type_for_transition(*, previous_status: str, next_status: str) -> str:
    if previous_status == "awaiting_agent" and next_status == "running":
        return "RunResumed"
    return {
        "running": "RunStarted",
        "awaiting_agent": "RunPausedForActor",
        "succeeded": "RunClosed",
        "stopped": "RunStopped",
        "failed": "RunFailed",
    }.get(next_status, "")


def _run_lifecycle_causation_id_for_connection(connection, *, stream_id: str, event_type: str) -> str | None:
    if event_type != "RunClosed":
        return None
    row = connection.execute(
        """
        SELECT event_id, payload_json FROM event_store
        WHERE stream_id = ? AND event_type = 'VerdictIssued'
        ORDER BY sequence DESC
        LIMIT 1
        """,
        (stream_id,),
    ).fetchone()
    if row is None:
        return None
    payload = _json_dict(row["payload_json"])
    if str(payload.get("status") or "").strip().lower() not in PASSING_VERDICT_STATUSES:
        return None
    return str(row["event_id"] or "")


def _json_dict(raw_value: object) -> dict:
    try:
        value = json.loads(str(raw_value or "{}"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}
