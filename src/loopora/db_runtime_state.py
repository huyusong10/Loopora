from __future__ import annotations

from loopora.db_domain_event_records import RepositoryDomainEventRecordsMixin
from loopora.db_event_records import RepositoryEventRecordsMixin
from loopora.db_run_slots import RepositoryRunSlotsMixin

from collections.abc import Iterable

from dataclasses import dataclass

from pathlib import Path

from loopora.utils import utc_now

import json

import sqlite3

from loopora.db_domain_event_records import json_dict

from loopora.utils import structured_non_negative_int



import logging

from collections.abc import Mapping


from typing import Any

from loopora.db_shared import logger

from loopora.diagnostics import log_event

from loopora.events.projection_cache import rebuild_run_projection_cache_for_connection

from loopora.events.run_record_events import append_run_lifecycle_event_for_connection


@dataclass(frozen=True, kw_only=True)
class RunUpdate:
    status: str | None = None
    current_iter: int | None = None
    active_role: str | None = None
    runner_pid: int | None = None
    child_pid: int | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error_message: str | None = None
    last_verdict: dict | None = None
    task_verdict: dict | None = None
    compiled_spec: dict | None = None
    summary_md: str | None = None
    clear_child_pid: bool = False

class RepositoryRunStateRecordsMixin:
    def update_run(
        self,
        run_id: str,
        update: RunUpdate | None = None,
        **raw_update: Any,
    ) -> dict:
        run_update = _coerce_run_update(update, raw_update)
        updates = _run_update_columns(run_update)
        row = self._persist_run_update(run_id, updates)
        decoded = self._decode_row(row) if row else {}
        self._log_run_update(run_id, decoded=decoded, updates=updates)
        return decoded

    def _persist_run_update(self, run_id: str, updates: dict[str, object]) -> object:
        assignments = ", ".join(f"{column} = ?" for column in updates)
        values = [*updates.values(), run_id]
        with self.transaction() as connection:
            previous_row = connection.execute("SELECT * FROM loop_runs WHERE id = ?", (run_id,)).fetchone()
            connection.execute(f"UPDATE loop_runs SET {assignments} WHERE id = ?", values)
            row = connection.execute("SELECT * FROM loop_runs WHERE id = ?", (run_id,)).fetchone()
            if row:
                connection.execute(
                    "UPDATE loop_definitions SET updated_at = ? WHERE id = ?",
                    (utc_now(), row["loop_id"]),
                )
                previous_status = str(previous_row["status"] or "") if previous_row is not None else ""
                if append_run_lifecycle_event_for_connection(
                    self,
                    connection,
                    row,
                    updates,
                    previous_status=previous_status,
                ):
                    self._refresh_run_projections_for_connection(connection, row["id"])
        return row

    def refresh_run_projection_cache(self, run_id: str) -> dict:
        with self.transaction() as connection:
            return self._refresh_run_projections_for_connection(connection, run_id)

    def _refresh_run_projections_for_connection(self, connection, run_id: str) -> dict:
        return rebuild_run_projection_cache_for_connection(self, connection, run_id)

    def _log_run_update(self, run_id: str, *, decoded: dict, updates: dict[str, object]) -> None:
        interesting_fields = _interesting_run_update_fields(updates)
        if not decoded or not interesting_fields:
            return
        log_event(
            logger,
            logging.INFO,
            "db.run.updated",
            "Persisted run state update",
            run_id=run_id,
            loop_id=decoded.get("loop_id"),
            workdir=decoded.get("workdir"),
            **interesting_fields,
        )

    def request_stop(self, run_id: str) -> dict | None:
        with self.transaction() as connection:
            connection.execute(
                "UPDATE loop_runs SET stop_requested = 1, updated_at = ? WHERE id = ?",
                (utc_now(), run_id),
            )
            row = connection.execute("SELECT * FROM loop_runs WHERE id = ?", (run_id,)).fetchone()
        decoded = self._decode_row(row) if row else None
        if decoded:
            log_event(
                logger,
                logging.INFO,
                "db.run.stop_requested",
                "Persisted stop request for run",
                run_id=run_id,
                loop_id=decoded.get("loop_id"),
                workdir=decoded.get("workdir"),
            )
        return decoded

    def should_stop(self, run_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute("SELECT stop_requested FROM loop_runs WHERE id = ?", (run_id,)).fetchone()
        return bool(row["stop_requested"]) if row else True

    def active_run_count(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM loop_runs WHERE status = 'running'").fetchone()
        return int(row["count"]) if row else 0

def _coerce_run_update(update: RunUpdate | None, raw_update: dict[str, Any]) -> RunUpdate:
    if update is not None and raw_update:
        raise TypeError("run update cannot mix object and keyword fields")
    return update or RunUpdate(**raw_update)

def _run_update_columns(update: RunUpdate) -> dict[str, object]:
    updates: dict[str, object] = {"updated_at": utc_now()}
    for field in (
        "status",
        "current_iter",
        "active_role",
        "runner_pid",
        "child_pid",
        "started_at",
        "finished_at",
        "error_message",
    ):
        value = getattr(update, field)
        if value is not None:
            updates[field] = value
    if update.clear_child_pid:
        updates["child_pid"] = None
    serialized_fields = {
        "last_verdict": "last_verdict_json",
        "task_verdict": "task_verdict_json",
        "compiled_spec": "compiled_spec_json",
    }
    for field, column in serialized_fields.items():
        value = getattr(update, field)
        if value is not None:
            updates[column] = json.dumps(value, ensure_ascii=False)
    if update.summary_md is not None:
        updates["summary_md"] = update.summary_md
    return updates

def _interesting_run_update_fields(updates: Mapping[str, object]) -> dict[str, object]:
    return {
        key: updates[key]
        for key in (
            "status",
            "current_iter",
            "active_role",
            "runner_pid",
            "child_pid",
            "started_at",
            "finished_at",
            "error_message",
        )
        if key in updates
    }

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

@dataclass(frozen=True)
class LocalAssetRootUpsertRequest:
    resource_type: str
    resource_id: str
    path: str | Path
    workdir: str = ""
    owner_id: str = ""
    state: str = "active"

class RepositoryLocalAssetRecordsMixin:
    def upsert_local_asset_root(
        self,
        request: LocalAssetRootUpsertRequest | None = None,
        **raw_request,
    ) -> dict:
        if request is None:
            request = LocalAssetRootUpsertRequest(**raw_request)
        normalized_state = self._normalize_local_asset_state(request.state)
        now = utc_now()
        normalized_path = str(Path(request.path).expanduser())
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO local_asset_roots
                    (resource_type, resource_id, path, workdir, owner_id, state, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(resource_type, resource_id, path) DO UPDATE SET
                    workdir = excluded.workdir,
                    owner_id = excluded.owner_id,
                    state = excluded.state,
                    updated_at = excluded.updated_at
                """,
                (
                    str(request.resource_type or "").strip(),
                    str(request.resource_id or "").strip(),
                    normalized_path,
                    str(request.workdir or "").strip(),
                    str(request.owner_id or "").strip(),
                    normalized_state,
                    now,
                ),
            )
            row = connection.execute(
                """
                SELECT * FROM local_asset_roots
                WHERE resource_type = ? AND resource_id = ? AND path = ?
                """,
                (str(request.resource_type or "").strip(), str(request.resource_id or "").strip(), normalized_path),
            ).fetchone()
        return self._decode_row(row)

    def mark_local_asset_root_state(
        self,
        *,
        resource_type: str,
        resource_id: str,
        state: str,
        path: str | Path | None = None,
    ) -> int:
        normalized_state = self._normalize_local_asset_state(state)
        now = utc_now()
        params: list[object] = [
            normalized_state,
            now,
            str(resource_type or "").strip(),
            str(resource_id or "").strip(),
        ]
        path_clause = ""
        if path is not None:
            path_clause = " AND path = ?"
            params.append(str(Path(path).expanduser()))
        with self.transaction() as connection:
            cursor = connection.execute(
                f"""
                UPDATE local_asset_roots
                SET state = ?, updated_at = ?
                WHERE resource_type = ? AND resource_id = ?{path_clause}
                """,
                params,
            )
        return int(cursor.rowcount or 0)

    def mark_local_asset_root_state_by_path(self, *, path: str | Path, state: str) -> int:
        normalized_state = self._normalize_local_asset_state(state)
        with self.transaction() as connection:
            cursor = connection.execute(
                """
                UPDATE local_asset_roots
                SET state = ?, updated_at = ?
                WHERE path = ?
                """,
                (normalized_state, utc_now(), str(Path(path).expanduser())),
            )
        return int(cursor.rowcount or 0)

    def list_local_asset_roots(
        self,
        *,
        resource_type: str | None = None,
        states: Iterable[str] | None = None,
    ) -> list[dict]:
        clauses: list[str] = []
        params: list[object] = []
        if resource_type:
            clauses.append("resource_type = ?")
            params.append(str(resource_type).strip())
        normalized_states = [
            self._normalize_local_asset_state(state)
            for state in (states or [])
            if str(state or "").strip()
        ]
        if normalized_states:
            placeholders = ", ".join("?" for _ in normalized_states)
            clauses.append(f"state IN ({placeholders})")
            params.extend(normalized_states)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM local_asset_roots
                {where}
                ORDER BY updated_at DESC, resource_type ASC, resource_id ASC
                """,
                params,
            ).fetchall()
        return [self._decode_row(row) for row in rows]

    @staticmethod
    def _normalize_local_asset_state(state: object) -> str:
        normalized = str(state or "active").strip().lower()
        if normalized not in {"active", "cleaned", "orphaned"}:
            return "active"
        return normalized


class RepositoryRuntimeStateMixin(
    RepositoryDomainEventRecordsMixin,
    RepositoryProjectionRecordsMixin,
    RepositoryRunSlotsMixin,
    RepositoryRunStateRecordsMixin,
    RepositoryEventRecordsMixin,
    RepositoryLocalAssetRecordsMixin,
):
    """Aggregate runtime-state persistence behavior for loop runs."""
