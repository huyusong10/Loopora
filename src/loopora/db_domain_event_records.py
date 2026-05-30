from __future__ import annotations

import json
import sqlite3

from loopora.events.envelope import EventEnvelope
from loopora.events.schemas import CORE_EVENT_AGGREGATE_TYPES, CORE_EVENT_TYPES
from loopora.events.store import DomainEventAppendRequest
from loopora.kernel.actors import ActorRef
from loopora.structured_numbers import structured_non_negative_int
from loopora.utils import make_id, utc_now


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

    def _append_domain_event_for_connection(
        self,
        connection: sqlite3.Connection,
        request: DomainEventAppendRequest,
    ) -> EventEnvelope:
        if request.event_type not in CORE_EVENT_TYPES:
            raise ValueError(f"unsupported core domain event type: {request.event_type}")
        expected_aggregate_type = CORE_EVENT_AGGREGATE_TYPES.get(request.event_type)
        if expected_aggregate_type and request.aggregate_type != expected_aggregate_type:
            raise ValueError(
                f"core domain event {request.event_type} requires aggregate_type {expected_aggregate_type}, got {request.aggregate_type}"
            )
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

    def list_domain_events(self, stream_id: str, *, after_sequence: int = 0, limit: int = 5000) -> list[EventEnvelope]:
        normalized_after = structured_non_negative_int(after_sequence)
        normalized_limit = min(structured_non_negative_int(limit), 5000)
        if normalized_limit <= 0:
            return []
        with self._connect() as connection:
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

    def get_projection_record(self, projection_name: str, projection_key: str) -> dict:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM projection_store
                WHERE projection_name = ? AND projection_key = ?
                """,
                (projection_name, projection_key),
            ).fetchone()
        if row is None:
            return {}
        return {
            "projection_name": row["projection_name"],
            "projection_key": row["projection_key"],
            "source_sequence": int(row["source_sequence"]),
            "payload": _json_dict(row["payload_json"]),
            "updated_at": row["updated_at"],
        }

    def put_projection_record(self, projection_name: str, projection_key: str, *, source_sequence: int, payload: dict) -> dict:
        with self.transaction() as connection:
            self._put_projection_record_for_connection(
                connection,
                projection_name,
                projection_key,
                source_sequence=source_sequence,
                payload=payload,
            )
        return self.get_projection_record(projection_name, projection_key)

    def _put_projection_record_for_connection(
        self,
        connection: sqlite3.Connection,
        projection_name: str,
        projection_key: str,
        *,
        source_sequence: int,
        payload: dict,
    ) -> None:
        updated_at = utc_now()
        connection.execute(
            """
            INSERT INTO projection_store (projection_name, projection_key, source_sequence, payload_json, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(projection_name, projection_key) DO UPDATE SET
                source_sequence = excluded.source_sequence,
                payload_json = excluded.payload_json,
                updated_at = excluded.updated_at
            """,
            (
                projection_name,
                projection_key,
                structured_non_negative_int(source_sequence),
                json.dumps(payload or {}, ensure_ascii=False),
                updated_at,
            ),
        )

    def record_artifact_index(self, payload: dict) -> dict:
        artifact_id = str(payload.get("artifact_id") or payload.get("id") or make_id("artifact"))
        created_at = utc_now()
        with self.transaction() as connection:
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
                    str(payload.get("created_by_event_id") or ""),
                    created_at,
                ),
            )
        return {"artifact_id": artifact_id, "created_at": created_at}

    def list_artifact_index(
        self,
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
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM artifact_index
                {where}
                ORDER BY created_at ASC, artifact_id ASC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        return [
            {
                "artifact_id": row["artifact_id"],
                "run_id": row["run_id"],
                "loop_id": row["loop_id"],
                "kind": row["kind"],
                "uri": row["uri"],
                "content_hash": row["content_hash"],
                "created_by_event_id": row["created_by_event_id"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

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
            actor=ActorRef.from_dict(_json_dict(row["actor_json"])),
            correlation_id=row["correlation_id"],
            causation_id=row["causation_id"],
            payload=_json_dict(row["payload_json"]),
        )


def _json_dict(raw_value: object) -> dict:
    try:
        value = json.loads(str(raw_value or "{}"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}
