from __future__ import annotations

import sqlite3

from loopora.structured_numbers import structured_non_negative_int
from loopora.utils import make_id, utc_now


def record_artifact_index_for_connection(connection: sqlite3.Connection, payload: dict) -> dict:
    artifact_id = str(payload.get("artifact_id") or payload.get("id") or make_id("artifact"))
    created_by_event_id = str(payload.get("created_by_event_id") or "")
    if not created_by_event_id:
        raise ValueError("artifact_index records require created_by_event_id")
    source_event = connection.execute(
        "SELECT event_id FROM event_store WHERE event_id = ?",
        (created_by_event_id,),
    ).fetchone()
    if source_event is None:
        raise ValueError("artifact_index records require created_by_event_id to reference an event_store event")
    created_at = utc_now()
    connection.execute(
        """
        INSERT OR REPLACE INTO artifact_index (
            artifact_id, run_id, loop_id, kind, uri, content_hash, created_by_event_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            artifact_id,
            str(payload.get("run_id") or ""),
            str(payload.get("loop_id") or ""),
            str(payload.get("kind") or "artifact"),
            str(payload.get("uri") or ""),
            str(payload.get("content_hash") or ""),
            created_by_event_id,
            created_at,
        ),
    )
    return {"artifact_id": artifact_id, "created_at": created_at}


def list_artifact_index_for_connection(
    connection: sqlite3.Connection,
    *,
    run_id: str = "",
    loop_id: str = "",
    created_by_event_id: str = "",
    limit: int = 500,
) -> list[dict]:
    clauses: list[str] = []
    params: list[str | int] = []
    if run_id:
        clauses.append("run_id = ?")
        params.append(run_id)
    if loop_id:
        clauses.append("loop_id = ?")
        params.append(loop_id)
    if created_by_event_id:
        clauses.append("created_by_event_id = ?")
        params.append(created_by_event_id)
    params.append(min(structured_non_negative_int(limit), 500))
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    rows = connection.execute(
        f"""
        SELECT * FROM artifact_index
        {where}
        ORDER BY created_at ASC, artifact_id ASC
        LIMIT ?
        """,
        tuple(params),
    ).fetchall()
    return [_artifact_index_row(row) for row in rows]


def _artifact_index_row(row: sqlite3.Row) -> dict:
    return {
        "artifact_id": row["artifact_id"],
        "run_id": row["run_id"],
        "loop_id": row["loop_id"],
        "kind": row["kind"],
        "uri": row["uri"],
        "content_hash": row["content_hash"],
        "created_by_event_id": row["created_by_event_id"],
        "created_at": row["created_at"],
    }
