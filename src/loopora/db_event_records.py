from __future__ import annotations

import json
from collections.abc import Iterable
import sqlite3

from loopora.db_event_mirrors import mirror_run_event_record
from loopora.db_run_event_observations import RepositoryRunEventObservationMixin, RunObservationSnapshotRowsRequest
from loopora.event_redaction import redact_run_event_payload
from loopora.structured_numbers import structured_non_negative_int
from loopora.utils import utc_now


class RepositoryEventRecordsMixin(RepositoryRunEventObservationMixin):
    def append_event(self, run_id: str, event_type: str, payload: dict, role: str | None = None) -> dict:
        now = utc_now()
        redacted_payload = redact_run_event_payload(event_type, payload)
        payload_json = json.dumps(redacted_payload, ensure_ascii=False)
        with self.transaction() as connection:
            cursor = connection.execute(
                """
                INSERT INTO run_events (run_id, created_at, event_type, role, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, now, event_type, role, payload_json),
            )
            row_id = cursor.lastrowid
            run = connection.execute("SELECT * FROM loop_runs WHERE id = ?", (run_id,)).fetchone()
        record = {
            "id": row_id,
            "run_id": run_id,
            "created_at": now,
            "event_type": event_type,
            "role": role,
            "payload": redacted_payload,
        }
        mirror_run_event_record(run, record, run_id=run_id, role=role, event_type=event_type)
        return record

    def list_events(self, run_id: str, *, after_id: int = 0, limit: int = 200) -> list[dict]:
        normalized_after_id = structured_non_negative_int(after_id)
        normalized_limit = min(structured_non_negative_int(limit), 5000)
        if normalized_limit <= 0:
            return []
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM run_events
                WHERE run_id = ? AND id > ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (run_id, normalized_after_id, normalized_limit),
            ).fetchall()
        return [self._decode_row(row) for row in rows]

    def list_recent_events(
        self,
        run_id: str,
        *,
        event_types: Iterable[str] | None = None,
        max_event_id: int | None = None,
        limit: int = 200,
    ) -> list[dict]:
        with self._connect() as connection:
            rows = self._recent_event_rows_for_connection(
                connection,
                run_id,
                event_types=event_types,
                max_event_id=max_event_id,
                limit=limit,
            )
        return [self._decode_row(row) for row in rows]

    def latest_event_id(self, run_id: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id FROM run_events
                WHERE run_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (run_id,),
            ).fetchone()
        return int(row["id"]) if row else 0

    def list_run_events_for_redaction_audit(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT e.*, r.runs_dir
                FROM run_events e
                JOIN loop_runs r ON r.id = e.run_id
                ORDER BY e.id ASC
                """
            ).fetchall()
        return [self._decode_row(row) for row in rows]

    def update_run_event_payload_for_redaction(self, event_id: int, payload: dict) -> bool:
        normalized_event_id = structured_non_negative_int(event_id)
        if normalized_event_id <= 0:
            return False
        payload_json = json.dumps(payload, ensure_ascii=False)
        with self.transaction() as connection:
            cursor = connection.execute(
                "UPDATE run_events SET payload_json = ? WHERE id = ?",
                (payload_json, normalized_event_id),
            )
        return cursor.rowcount > 0

    def record_run_takeaway_projection(self, run_id: str, source_event_id: int, payload: dict) -> bool:
        normalized_source_event_id = structured_non_negative_int(source_event_id)
        if normalized_source_event_id <= 0:
            return False
        with self.transaction() as connection:
            run = connection.execute("SELECT * FROM loop_runs WHERE id = ?", (run_id,)).fetchone()
            if run is None:
                return False
            self._insert_takeaway_projection_for_connection(
                connection,
                run_id=run_id,
                source_event_id=normalized_source_event_id,
                payload=payload,
            )
        return True

    @staticmethod
    def _insert_takeaway_projection_for_connection(
        connection: sqlite3.Connection,
        *,
        run_id: str,
        source_event_id: int,
        payload: dict,
    ) -> None:
        normalized_source_event_id = structured_non_negative_int(source_event_id)
        if normalized_source_event_id <= 0:
            return
        projection = dict(payload or {})
        projection["source_event_id"] = normalized_source_event_id
        connection.execute(
            """
            INSERT OR REPLACE INTO run_takeaway_projections
                (run_id, source_event_id, payload_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (run_id, normalized_source_event_id, json.dumps(projection, ensure_ascii=False), utc_now()),
        )

__all__ = ["RepositoryEventRecordsMixin", "RunObservationSnapshotRowsRequest"]
