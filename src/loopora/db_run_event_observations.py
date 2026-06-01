from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import sqlite3

from loopora.structured_numbers import structured_non_negative_int


@dataclass(frozen=True)
class RunObservationSnapshotRowsRequest:
    run_id: str
    timeline_event_types: Iterable[str]
    progress_event_types: Iterable[str]
    timeline_limit: int = 40
    console_limit: int = 160
    progress_limit: int = 2000


class RepositoryRunEventObservationMixin:
    @staticmethod
    def _recent_event_rows_for_connection(
        connection: sqlite3.Connection,
        run_id: str,
        *,
        event_types: Iterable[str] | None = None,
        max_event_id: int | None = None,
        limit: int = 200,
    ) -> list[sqlite3.Row]:
        normalized_limit = min(structured_non_negative_int(limit), 5000)
        if normalized_limit <= 0:
            return []
        types = sorted({str(event_type or "").strip() for event_type in (event_types or []) if str(event_type or "").strip()})
        params: list[object] = [run_id]
        where = "run_id = ?"
        if types:
            placeholders = ", ".join("?" for _ in types)
            where = f"{where} AND event_type IN ({placeholders})"
            params.extend(types)
        if max_event_id is not None:
            where = f"{where} AND id <= ?"
            params.append(structured_non_negative_int(max_event_id))
        params.append(normalized_limit)
        rows = connection.execute(
            f"""
            SELECT * FROM run_events
            WHERE {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        return list(reversed(rows))

    def _latest_takeaway_projection_for_connection(
        self,
        connection: sqlite3.Connection,
        run_id: str,
        *,
        max_source_event_id: int,
    ) -> dict | None:
        normalized_max_source_event_id = structured_non_negative_int(max_source_event_id)
        if normalized_max_source_event_id <= 0:
            return None
        row = connection.execute(
            """
            SELECT * FROM run_takeaway_projections
            WHERE run_id = ? AND source_event_id <= ?
            ORDER BY source_event_id DESC
            LIMIT 1
            """,
            (run_id, normalized_max_source_event_id),
        ).fetchone()
        if row is None:
            return None
        payload = self._decode_json_column(
            f"{run_id}:{row['source_event_id']}",
            "payload_json",
            row["payload_json"],
        )
        payload["source_event_id"] = int(row["source_event_id"])
        return payload

    def latest_event_id_for_types(self, run_id: str, event_types: Iterable[str]) -> int:
        types = sorted({str(event_type or "").strip() for event_type in event_types if str(event_type or "").strip()})
        if not types:
            return 0
        placeholders = ", ".join("?" for _ in types)
        with self._connect() as connection:
            row = connection.execute(
                f"""
                SELECT id FROM run_events
                WHERE run_id = ? AND event_type IN ({placeholders})
                ORDER BY id DESC
                LIMIT 1
                """,
                [run_id, *types],
            ).fetchone()
        return int(row["id"]) if row else 0

    def run_observation_snapshot_rows(
        self,
        request: RunObservationSnapshotRowsRequest,
    ) -> dict | None:
        with self._connect() as connection:
            connection.execute("BEGIN")
            try:
                run_row = connection.execute("SELECT * FROM loop_runs WHERE id = ?", (request.run_id,)).fetchone()
                if run_row is None:
                    connection.rollback()
                    return None
                latest_row = connection.execute(
                    """
                    SELECT id FROM run_events
                    WHERE run_id = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (request.run_id,),
                ).fetchone()
                latest_event_id = int(latest_row["id"]) if latest_row else 0
                timeline_rows = self._recent_event_rows_for_connection(
                    connection,
                    request.run_id,
                    event_types=request.timeline_event_types,
                    max_event_id=latest_event_id,
                    limit=request.timeline_limit,
                )
                console_rows = self._recent_event_rows_for_connection(
                    connection,
                    request.run_id,
                    max_event_id=latest_event_id,
                    limit=request.console_limit,
                )
                progress_rows = self._recent_event_rows_for_connection(
                    connection,
                    request.run_id,
                    event_types=request.progress_event_types,
                    max_event_id=latest_event_id,
                    limit=request.progress_limit,
                )
                key_takeaway_projection = self._latest_takeaway_projection_for_connection(
                    connection,
                    request.run_id,
                    max_source_event_id=latest_event_id,
                )
                loop_row = connection.execute(
                    "SELECT name FROM loop_definitions WHERE id = ?",
                    (run_row["loop_id"],),
                ).fetchone()
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        run = self._decode_row(run_row)
        if loop_row:
            run["loop_name"] = loop_row["name"]
        return {
            "run": run,
            "latest_event_id": latest_event_id,
            "timeline_events": [self._decode_row(row) for row in timeline_rows],
            "console_events": [self._decode_row(row) for row in console_rows],
            "progress_events": [self._decode_row(row) for row in progress_rows],
            "key_takeaway_projection": key_takeaway_projection,
        }
