from __future__ import annotations

import json
import sqlite3

from loopora.db_record_json import json_dict
from loopora.structured_numbers import structured_non_negative_int
from loopora.utils import utc_now


class RepositoryProjectionRecordsMixin:
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
            "payload": json_dict(row["payload_json"]),
            "updated_at": row["updated_at"],
        }

    def put_projection_record(self, projection_name: str, projection_key: str, *, source_sequence: int, payload: dict) -> dict:
        with self.transaction() as connection:
            self.put_projection_record_for_connection(
                connection,
                projection_name,
                projection_key,
                source_sequence=source_sequence,
                payload=payload,
            )
        return self.get_projection_record(projection_name, projection_key)

    def put_projection_record_for_connection(
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
