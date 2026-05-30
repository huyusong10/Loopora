from __future__ import annotations

from collections.abc import Mapping

from loopora.events.append_requests import RunEventAppend, append_run_event


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
