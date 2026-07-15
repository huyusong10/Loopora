from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from typing import TypeVar

from loopora.events.envelope import EventEnvelope
from loopora.events.run_event_invariants import require_run_event_append_invariants
from loopora.events.schemas import require_core_event_payload_identity, require_core_event_stream_boundary
from loopora.events.store import DomainEventAppendRequest, DomainEventTransaction
from loopora.kernel.actors import ActorRef
from loopora.utils import structured_non_negative_int
from loopora.utils import make_id, utc_now





def json_dict(raw_value: object) -> dict:
    try:
        value = json.loads(str(raw_value or "{}"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}

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

T = TypeVar("T")


class RepositoryDomainEventRecordsMixin:
    def append_domain_event(
        self,
        request: DomainEventAppendRequest | None = None,
        **raw_request,
    ) -> EventEnvelope:
        append_request = request or DomainEventAppendRequest(**raw_request)
        with self.transaction() as connection:
            return self._append_domain_event_for_connection(
                connection,
                append_request,
            )

    def append_domain_event_transaction(self, handler: Callable[[DomainEventTransaction], T]) -> T:
        with self.transaction() as connection:
            return handler(self.domain_event_transaction_for_connection(connection))

    def domain_event_transaction_for_connection(self, connection: sqlite3.Connection) -> DomainEventTransaction:
        return _RepositoryDomainEventTransaction(self, connection)

    def _append_domain_event_for_connection(
        self,
        connection: sqlite3.Connection,
        request: DomainEventAppendRequest,
    ) -> EventEnvelope:
        require_core_event_stream_boundary(
            event_type=request.event_type,
            aggregate_type=request.aggregate_type,
            aggregate_id=request.aggregate_id,
            stream_id=request.stream_id,
        )
        require_core_event_payload_identity(
            aggregate_type=request.aggregate_type,
            aggregate_id=request.aggregate_id,
            payload=request.payload or {},
        )
        self._require_causation_event_exists_for_connection(connection, request)
        require_run_event_append_invariants(connection, request)
        event_id = make_id("event")
        normalized_actor = request.actor or ActorRef.system()
        row = connection.execute(
            "SELECT COALESCE(MAX(sequence), 0) AS latest_sequence FROM event_store WHERE stream_id = ?",
            (request.stream_id,),
        ).fetchone()
        sequence = int(row["latest_sequence"] or 0) + 1
        occurred_at = utc_now()
        envelope = EventEnvelope(
            event_id=event_id,
            stream_id=request.stream_id,
            aggregate_type=request.aggregate_type,
            aggregate_id=request.aggregate_id,
            sequence=sequence,
            event_type=request.event_type,
            schema_version=int(request.schema_version),
            occurred_at=occurred_at,
            actor=normalized_actor,
            correlation_id=request.correlation_id or event_id,
            causation_id=request.causation_id,
            payload=dict(request.payload or {}),
        )
        connection.execute(
            """
            INSERT INTO event_store (
                event_id, stream_id, aggregate_type, aggregate_id, sequence, event_type,
                schema_version, occurred_at, actor_json, correlation_id, causation_id, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                envelope.event_id,
                envelope.stream_id,
                envelope.aggregate_type,
                envelope.aggregate_id,
                envelope.sequence,
                envelope.event_type,
                envelope.schema_version,
                envelope.occurred_at,
                json.dumps(envelope.actor.to_dict(), ensure_ascii=False),
                envelope.correlation_id,
                envelope.causation_id,
                json.dumps(envelope.payload, ensure_ascii=False),
            ),
        )
        return envelope

    def _require_causation_event_exists_for_connection(
        self,
        connection: sqlite3.Connection,
        request: DomainEventAppendRequest,
    ) -> None:
        if not request.causation_id:
            return
        row = connection.execute(
            "SELECT event_id FROM event_store WHERE event_id = ? LIMIT 1",
            (request.causation_id,),
        ).fetchone()
        if row is None:
            raise ValueError("core domain event causation_id must reference existing event")

    def list_domain_events(self, stream_id: str, *, after_sequence: int = 0, limit: int = 5000) -> list[EventEnvelope]:
        with self._connect() as connection:
            return self.list_domain_events_for_connection(
                connection,
                stream_id,
                after_sequence=after_sequence,
                limit=limit,
            )

    def latest_domain_event_sequence(self, stream_id: str) -> int:
        with self._connect() as connection:
            return self.latest_domain_event_sequence_for_connection(connection, stream_id)

    def latest_domain_event_sequence_for_connection(self, connection: sqlite3.Connection, stream_id: str) -> int:
        row = connection.execute(
            "SELECT COALESCE(MAX(sequence), 0) AS latest_sequence FROM event_store WHERE stream_id = ?",
            (stream_id,),
        ).fetchone()
        return int(row["latest_sequence"] or 0)

    def list_domain_events_for_connection(
        self,
        connection: sqlite3.Connection,
        stream_id: str,
        *,
        after_sequence: int = 0,
        limit: int = 5000,
    ) -> list[EventEnvelope]:
        normalized_after = structured_non_negative_int(after_sequence)
        normalized_limit = min(structured_non_negative_int(limit), 5000)
        if normalized_limit <= 0:
            return []
        rows = connection.execute(
            """
            SELECT * FROM event_store
            WHERE stream_id = ? AND sequence > ?
            ORDER BY sequence ASC
            LIMIT ?
            """,
            (stream_id, normalized_after, normalized_limit),
        ).fetchall()
        return [self._domain_event_from_row(row) for row in rows]

    def record_artifact_index(self, payload: dict) -> dict:
        with self.transaction() as connection:
            return self._record_artifact_index_for_connection(connection, payload)

    def _record_artifact_index_for_connection(self, connection: sqlite3.Connection, payload: dict) -> dict:
        return record_artifact_index_for_connection(connection, payload)

    def list_artifact_index(
        self,
        *,
        run_id: str = "",
        loop_id: str = "",
        created_by_event_id: str = "",
        limit: int = 500,
    ) -> list[dict]:
        with self._connect() as connection:
            return list_artifact_index_for_connection(
                connection,
                run_id=run_id,
                loop_id=loop_id,
                created_by_event_id=created_by_event_id,
                limit=limit,
            )

    @staticmethod
    def _domain_event_from_row(row: sqlite3.Row) -> EventEnvelope:
        return EventEnvelope(
            event_id=row["event_id"],
            stream_id=row["stream_id"],
            aggregate_type=row["aggregate_type"],
            aggregate_id=row["aggregate_id"],
            sequence=int(row["sequence"]),
            event_type=row["event_type"],
            schema_version=int(row["schema_version"]),
            occurred_at=row["occurred_at"],
            actor=ActorRef.from_dict(json_dict(row["actor_json"])),
            correlation_id=row["correlation_id"],
            causation_id=row["causation_id"],
            payload=json_dict(row["payload_json"]),
        )


class _RepositoryDomainEventTransaction:
    def __init__(self, repository: RepositoryDomainEventRecordsMixin, connection: sqlite3.Connection) -> None:
        self._repository = repository
        self._connection = connection

    def append_domain_event(self, request: DomainEventAppendRequest) -> EventEnvelope:
        return self._repository._append_domain_event_for_connection(self._connection, request)

    def record_artifact_index(self, payload: dict) -> dict:
        return self._repository._record_artifact_index_for_connection(self._connection, payload)
