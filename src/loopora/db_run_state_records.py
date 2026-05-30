from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from loopora.db_shared import logger
from loopora.diagnostics import log_event
from loopora.events.streams import run_stream_id
from loopora.events.store import DomainEventAppendRequest
from loopora.projections import replay_run_projection_bundle
from loopora.utils import utc_now


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
                if self._append_run_lifecycle_domain_event_for_connection(connection, row, updates, previous_status=previous_status):
                    self._refresh_run_projections_for_connection(connection, row["id"])
        return row

    def _append_run_lifecycle_domain_event_for_connection(
        self,
        connection,
        row,
        updates: dict[str, object],
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
        self._append_domain_event_for_connection(
            connection,
            DomainEventAppendRequest(
                stream_id=run_stream_id(row["id"]),
                aggregate_type="run",
                aggregate_id=row["id"],
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

    def refresh_run_projection_cache(self, run_id: str) -> dict:
        with self.transaction() as connection:
            return self._refresh_run_projections_for_connection(connection, run_id)

    def _refresh_run_projections_for_connection(self, connection, run_id: str) -> dict:
        rows = connection.execute(
            """
            SELECT * FROM event_store
            WHERE stream_id = ?
            ORDER BY sequence ASC
            """,
            (run_stream_id(run_id),),
        ).fetchall()
        projections = replay_run_projection_bundle([self._domain_event_from_row(row) for row in rows])
        for name, payload in projections.items():
            self._put_projection_record_for_connection(
                connection,
                name,
                run_id,
                source_sequence=int(payload.get("source_sequence") or 0) if isinstance(payload, dict) else 0,
                payload=payload,
            )
        return projections

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
