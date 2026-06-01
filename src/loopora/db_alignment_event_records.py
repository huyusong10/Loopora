from __future__ import annotations

import json

from loopora.db_alignment_event_artifacts import append_alignment_event_artifact
from loopora.event_redaction import redact_alignment_event_payload
from loopora.structured_numbers import structured_non_negative_int
from loopora.utils import utc_now


class RepositoryAlignmentEventRecordsMixin:
    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict:
        now = utc_now()
        redacted_payload = redact_alignment_event_payload(event_type, payload)
        payload_json = json.dumps(redacted_payload, ensure_ascii=False)
        with self.transaction() as connection:
            cursor = connection.execute(
                """
                INSERT INTO alignment_events (session_id, created_at, event_type, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, now, event_type, payload_json),
            )
            row_id = cursor.lastrowid
            session_row = connection.execute(
                "SELECT bundle_path FROM alignment_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
        event = {
            "id": row_id,
            "session_id": session_id,
            "created_at": now,
            "event_type": event_type,
            "payload": redacted_payload,
        }
        if session_row:
            append_alignment_event_artifact(session_row["bundle_path"], event)
        return event

    def list_alignment_events(self, session_id: str, *, after_id: int = 0, limit: int = 200) -> list[dict]:
        normalized_after_id = structured_non_negative_int(after_id)
        normalized_limit = min(structured_non_negative_int(limit), 5000)
        if normalized_limit <= 0:
            return []
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM alignment_events
                WHERE session_id = ? AND id > ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (session_id, normalized_after_id, normalized_limit),
            ).fetchall()
        return [self._decode_row(row) for row in rows]

    def latest_alignment_event_id(self, session_id: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT MAX(id) AS latest_id
                FROM alignment_events
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        return int(row["latest_id"] or 0) if row else 0

    def list_alignment_events_for_redaction_audit(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT e.*, s.bundle_path
                FROM alignment_events e
                JOIN alignment_sessions s ON s.id = e.session_id
                ORDER BY e.id ASC
                """
            ).fetchall()
        return [self._decode_row(row) for row in rows]

    def update_alignment_event_payload_for_redaction(self, event_id: int, payload: dict) -> bool:
        normalized_event_id = structured_non_negative_int(event_id)
        if normalized_event_id <= 0:
            return False
        payload_json = json.dumps(payload, ensure_ascii=False)
        with self.transaction() as connection:
            cursor = connection.execute(
                "UPDATE alignment_events SET payload_json = ? WHERE id = ?",
                (payload_json, normalized_event_id),
            )
        return cursor.rowcount > 0
