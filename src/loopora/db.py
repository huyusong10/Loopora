from __future__ import annotations

import logging
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from collections.abc import Iterator

from loopora.diagnostics import log_event, log_exception
from loopora.db_alignment_records import RepositoryAlignmentRecordsMixin
from loopora.db_row_decoding import RepositoryRowDecodingMixin
from loopora.db_runtime_state import RepositoryRuntimeStateMixin
from loopora.run_artifacts import append_jsonl_with_mirrors



from loopora.db_loop_records import RepositoryLoopRecordsMixin


import json


from loopora.db_bundle_graph_records import RepositoryBundleGraphRecordsMixin

from loopora.db_shared import logger


from loopora.utils import utc_now














from loopora.events.run_record_events import append_run_created_event_for_connection

from loopora.service_types import ACTIVE_RUN_STATUSES, LooporaConflictError





from loopora.db_schema_v3 import CURRENT_SCHEMA_VERSION, V3_SCHEMA_SQL, schema_has_current_v3_shape



class RepositorySchemaMixin:
    def _init_db(self) -> None:
        with self.transaction(configure_journal_mode=True) as connection:
            connection.executescript(V3_SCHEMA_SQL)
            self._run_schema_migrations(connection)
        log_event(
            logger,
            logging.INFO,
            "db.schema.ready",
            "Database schema is ready",
            path=self.path,
            schema_version=CURRENT_SCHEMA_VERSION,
        )

    @classmethod
    def _run_schema_migrations(cls, connection: sqlite3.Connection) -> None:
        version = cls._schema_user_version(connection)
        if version > CURRENT_SCHEMA_VERSION:
            log_event(
                logger,
                logging.WARNING,
                "db.schema.future_version",
                "Database schema was created by a newer Loopora version",
                database_version=version,
                supported_version=CURRENT_SCHEMA_VERSION,
            )
            return
        if version == CURRENT_SCHEMA_VERSION:
            return
        if version == 0 and schema_has_current_v3_shape(connection):
            cls._set_schema_user_version(connection, CURRENT_SCHEMA_VERSION)
            return
        raise LooporaConflictError(
            "Loopora v3 development reset required: existing local database schema "
            f"version {version} is not compatible. Delete LOOPORA_HOME or run `loopora dev reset --workdir <project>`."
        )

    @staticmethod
    def _schema_user_version(connection: sqlite3.Connection) -> int:
        row = connection.execute("PRAGMA user_version").fetchone()
        return int(row[0] or 0)

    @staticmethod
    def _set_schema_user_version(connection: sqlite3.Connection, version: int) -> None:
        connection.execute(f"PRAGMA user_version = {int(version)}")

class RepositoryRunRecordsMixin:
    def create_run(self, payload: dict) -> dict:
        now = utc_now()
        with self.transaction() as connection:
            if payload["status"] in ACTIVE_RUN_STATUSES:
                active_run = connection.execute(
                    """
                    SELECT id
                    FROM loop_runs
                    WHERE workdir = ? AND status IN ('queued', 'running', 'awaiting_agent')
                    LIMIT 1
                    """,
                    (payload["workdir"],),
                ).fetchone()
                if active_run and active_run["id"] != payload["id"]:
                    raise LooporaConflictError(f"another active run is already using {payload['workdir']}")
            connection.execute(
                """
                INSERT INTO loop_runs (
                    id, loop_id, orchestration_id, orchestration_name, workdir, spec_path, spec_markdown, compiled_spec_json,
                    executor_kind, executor_mode, command_cli, command_args_text,
                    model, reasoning_effort, completion_mode, iteration_interval_seconds,
                    max_iters, max_role_retries, delta_threshold,
                    trigger_window, regression_window, role_models_json, workflow_json, status, stop_requested,
                    current_iter, active_role, runner_pid, child_pid, queued_at, started_at,
                    finished_at, error_message, last_verdict_json, summary_md, runs_dir,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["id"],
                    payload["loop_id"],
                    payload.get("orchestration_id", ""),
                    payload.get("orchestration_name", ""),
                    payload["workdir"],
                    payload["spec_path"],
                    payload["spec_markdown"],
                    json.dumps(payload["compiled_spec"], ensure_ascii=False),
                    payload.get("executor_kind", "codex"),
                    payload.get("executor_mode", "preset"),
                    payload.get("command_cli", ""),
                    payload.get("command_args_text", ""),
                    payload["model"],
                    payload["reasoning_effort"],
                    payload.get("completion_mode", "gatekeeper"),
                    payload.get("iteration_interval_seconds", 0.0),
                    payload["max_iters"],
                    payload["max_role_retries"],
                    payload["delta_threshold"],
                    payload["trigger_window"],
                    payload["regression_window"],
                    json.dumps(payload.get("role_models", {}), ensure_ascii=False),
                    json.dumps(payload.get("workflow", {}), ensure_ascii=False),
                    payload["status"],
                    0,
                    0,
                    None,
                    None,
                    None,
                    now,
                    None,
                    None,
                    None,
                    None,
                    payload.get("summary_md", ""),
                    payload["runs_dir"],
                    now,
                    now,
                ),
            )
            connection.execute(
                "UPDATE loop_definitions SET latest_run_id = ?, updated_at = ? WHERE id = ?",
                (payload["id"], now, payload["loop_id"]),
            )
            connection.execute(
                """
                INSERT INTO local_asset_roots
                    (resource_type, resource_id, path, workdir, owner_id, state, updated_at)
                VALUES ('run', ?, ?, ?, ?, 'active', ?)
                ON CONFLICT(resource_type, resource_id, path) DO UPDATE SET
                    workdir = excluded.workdir,
                    owner_id = excluded.owner_id,
                    state = 'active',
                    updated_at = excluded.updated_at
                """,
                (
                    payload["id"],
                    payload["runs_dir"],
                    payload["workdir"],
                    payload["loop_id"],
                    now,
                ),
            )
            append_run_created_event_for_connection(self, connection, payload)
            self._refresh_run_projections_for_connection(connection, payload["id"])
        run = self.get_run(payload["id"])
        log_event(
            logger,
            logging.INFO,
            "db.run.created",
            "Persisted run record",
            run_id=payload["id"],
            loop_id=payload["loop_id"],
            orchestration_id=payload.get("orchestration_id", ""),
            workdir=payload["workdir"],
            status=payload["status"],
        )
        return run

    def get_run(self, run_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM loop_runs WHERE id = ?", (run_id,)).fetchone()
        return self._decode_row(row) if row else None

    def list_runs_for_loop(self, loop_id: str, limit: int = 20) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM loop_runs WHERE loop_id = ? ORDER BY created_at DESC LIMIT ?",
                (loop_id, limit),
            ).fetchall()
        return [self._decode_row(row) for row in rows]

    def list_active_runs(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM loop_runs WHERE status IN ('queued', 'running', 'awaiting_agent') ORDER BY created_at DESC"
            ).fetchall()
        return [self._decode_row(row) for row in rows]

    def list_terminal_runs_without_takeaway_projection(self, *, limit: int = 5000) -> list[dict]:
        normalized_limit = max(0, min(int(limit), 5000))
        if normalized_limit <= 0:
            return []
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT r.*
                FROM loop_runs r
                WHERE r.status IN ('succeeded', 'failed', 'stopped')
                  AND NOT EXISTS (
                    SELECT 1
                    FROM run_takeaway_projections p
                    WHERE p.run_id = r.id
                  )
                ORDER BY r.created_at DESC
                LIMIT ?
                """,
                (normalized_limit,),
            ).fetchall()
        return [self._decode_row(row) for row in rows]

class RepositoryRoleDefinitionRecordsMixin:
    def create_role_definition(self, payload: dict) -> dict:
        now = utc_now()
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO role_definitions (
                    id, name, description, archetype, prompt_ref, prompt_markdown, posture_notes,
                    executor_kind, executor_mode, command_cli, command_args_text, model, reasoning_effort,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["id"],
                    payload["name"],
                    payload.get("description", ""),
                    payload["archetype"],
                    payload["prompt_ref"],
                    payload["prompt_markdown"],
                    payload.get("posture_notes", ""),
                    payload.get("executor_kind", "codex"),
                    payload.get("executor_mode", "preset"),
                    payload.get("command_cli", "codex"),
                    payload.get("command_args_text", ""),
                    payload.get("model", ""),
                    payload.get("reasoning_effort", ""),
                    now,
                    now,
                ),
            )
        role_definition = self.get_role_definition(payload["id"])
        log_event(
            logger,
            logging.INFO,
            "db.role_definition.created",
            "Persisted role definition",
            role_definition_id=payload["id"],
            archetype=payload["archetype"],
            executor_kind=payload.get("executor_kind", "codex"),
            role_name=payload["name"],
        )
        return role_definition

    def update_role_definition(self, role_definition_id: str, payload: dict) -> dict | None:
        now = utc_now()
        with self.transaction() as connection:
            row = connection.execute("SELECT 1 FROM role_definitions WHERE id = ?", (role_definition_id,)).fetchone()
            if row is None:
                return None
            connection.execute(
                """
                UPDATE role_definitions
                SET name = ?, description = ?, archetype = ?, prompt_ref = ?, prompt_markdown = ?, posture_notes = ?,
                    executor_kind = ?, executor_mode = ?, command_cli = ?, command_args_text = ?, model = ?, reasoning_effort = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    payload["name"],
                    payload.get("description", ""),
                    payload["archetype"],
                    payload["prompt_ref"],
                    payload["prompt_markdown"],
                    payload.get("posture_notes", ""),
                    payload.get("executor_kind", "codex"),
                    payload.get("executor_mode", "preset"),
                    payload.get("command_cli", "codex"),
                    payload.get("command_args_text", ""),
                    payload.get("model", ""),
                    payload.get("reasoning_effort", ""),
                    now,
                    role_definition_id,
                ),
            )
        role_definition = self.get_role_definition(role_definition_id)
        log_event(
            logger,
            logging.INFO,
            "db.role_definition.updated",
            "Updated role definition",
            role_definition_id=role_definition_id,
            archetype=payload["archetype"],
            executor_kind=payload.get("executor_kind", "codex"),
            role_name=payload["name"],
        )
        return role_definition

    def get_role_definition(self, role_definition_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM role_definitions WHERE id = ?", (role_definition_id,)).fetchone()
        return self._decode_row(row) if row else None

    def list_role_definitions(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM role_definitions ORDER BY updated_at DESC, created_at DESC").fetchall()
        return [self._decode_row(row) for row in rows]

    def delete_role_definition(self, role_definition_id: str) -> bool:
        with self.transaction() as connection:
            row = connection.execute("SELECT 1 FROM role_definitions WHERE id = ?", (role_definition_id,)).fetchone()
            if row is None:
                return False
            connection.execute("DELETE FROM role_definitions WHERE id = ?", (role_definition_id,))
        log_event(
            logger,
            logging.INFO,
            "db.role_definition.deleted",
            "Deleted role definition",
            role_definition_id=role_definition_id,
        )
        return True

class RepositoryOrchestrationRecordsMixin:
    def create_orchestration(self, payload: dict) -> dict:
        now = utc_now()
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO orchestration_definitions (
                    id, name, description, workflow_json, prompt_files_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["id"],
                    payload["name"],
                    payload.get("description", ""),
                    json.dumps(payload["workflow"], ensure_ascii=False),
                    json.dumps(payload.get("prompt_files", {}), ensure_ascii=False),
                    now,
                    now,
                ),
            )
        orchestration = self.get_orchestration(payload["id"])
        log_event(
            logger,
            logging.INFO,
            "db.orchestration.created",
            "Persisted orchestration definition",
            orchestration_id=payload["id"],
            orchestration_name=payload["name"],
            role_count=len(payload["workflow"].get("roles", [])),
            step_count=len(payload["workflow"].get("steps", [])),
        )
        return orchestration

    def update_orchestration(self, orchestration_id: str, payload: dict) -> dict | None:
        now = utc_now()
        with self.transaction() as connection:
            row = connection.execute("SELECT 1 FROM orchestration_definitions WHERE id = ?", (orchestration_id,)).fetchone()
            if row is None:
                return None
            connection.execute(
                """
                UPDATE orchestration_definitions
                SET name = ?, description = ?, workflow_json = ?, prompt_files_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    payload["name"],
                    payload.get("description", ""),
                    json.dumps(payload["workflow"], ensure_ascii=False),
                    json.dumps(payload.get("prompt_files", {}), ensure_ascii=False),
                    now,
                    orchestration_id,
                ),
            )
        orchestration = self.get_orchestration(orchestration_id)
        log_event(
            logger,
            logging.INFO,
            "db.orchestration.updated",
            "Updated orchestration definition",
            orchestration_id=orchestration_id,
            orchestration_name=payload["name"],
            role_count=len(payload["workflow"].get("roles", [])),
            step_count=len(payload["workflow"].get("steps", [])),
        )
        return orchestration

    def get_orchestration(self, orchestration_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM orchestration_definitions WHERE id = ?", (orchestration_id,)).fetchone()
        return self._decode_row(row) if row else None

    def list_orchestrations(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM orchestration_definitions ORDER BY updated_at DESC, created_at DESC").fetchall()
        return [self._decode_row(row) for row in rows]

    def delete_orchestration(self, orchestration_id: str) -> bool:
        with self.transaction() as connection:
            row = connection.execute("SELECT 1 FROM orchestration_definitions WHERE id = ?", (orchestration_id,)).fetchone()
            if row is None:
                return False
            connection.execute("DELETE FROM orchestration_definitions WHERE id = ?", (orchestration_id,))
        log_event(
            logger,
            logging.INFO,
            "db.orchestration.deleted",
            "Deleted orchestration definition",
            orchestration_id=orchestration_id,
        )
        return True

class RepositoryBundleRecordsMixin(RepositoryBundleGraphRecordsMixin):
    def create_bundle(self, payload: dict) -> dict:
        now = utc_now()
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO bundle_definitions (
                    id, name, description, collaboration_summary, workdir, loop_id, orchestration_id,
                    role_definition_ids_json, source_bundle_id, revision, imported_from_path,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["id"],
                    payload["name"],
                    payload.get("description", ""),
                    payload.get("collaboration_summary", ""),
                    payload.get("workdir", ""),
                    payload.get("loop_id", ""),
                    payload.get("orchestration_id", ""),
                    json.dumps(payload.get("role_definition_ids", []), ensure_ascii=False),
                    payload.get("source_bundle_id", ""),
                    int(payload.get("revision", 1) or 1),
                    payload.get("imported_from_path", ""),
                    now,
                    now,
                ),
            )
            self._replace_bundle_asset_ownership_for_connection(connection, payload, now=now)
            self._upsert_bundle_local_asset_root_for_connection(connection, payload, now=now)
        bundle = self.get_bundle(payload["id"])
        log_event(
            logger,
            logging.INFO,
            "db.bundle.created",
            "Persisted bundle definition",
            bundle_id=payload["id"],
            bundle_name=payload["name"],
            loop_id=payload.get("loop_id", ""),
            orchestration_id=payload.get("orchestration_id", ""),
        )
        return bundle

    def update_bundle(self, bundle_id: str, payload: dict) -> dict | None:
        now = utc_now()
        with self.transaction() as connection:
            row = connection.execute("SELECT 1 FROM bundle_definitions WHERE id = ?", (bundle_id,)).fetchone()
            if row is None:
                return None
            connection.execute(
                """
                UPDATE bundle_definitions
                SET name = ?, description = ?, collaboration_summary = ?, workdir = ?, loop_id = ?, orchestration_id = ?,
                    role_definition_ids_json = ?, source_bundle_id = ?, revision = ?, imported_from_path = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    payload["name"],
                    payload.get("description", ""),
                    payload.get("collaboration_summary", ""),
                    payload.get("workdir", ""),
                    payload.get("loop_id", ""),
                    payload.get("orchestration_id", ""),
                    json.dumps(payload.get("role_definition_ids", []), ensure_ascii=False),
                    payload.get("source_bundle_id", ""),
                    int(payload.get("revision", 1) or 1),
                    payload.get("imported_from_path", ""),
                    now,
                    bundle_id,
                ),
            )
            ownership_payload = {**payload, "id": bundle_id}
            self._replace_bundle_asset_ownership_for_connection(connection, ownership_payload, now=now)
            self._upsert_bundle_local_asset_root_for_connection(connection, ownership_payload, now=now)
        bundle = self.get_bundle(bundle_id)
        log_event(
            logger,
            logging.INFO,
            "db.bundle.updated",
            "Updated bundle definition",
            bundle_id=bundle_id,
            bundle_name=payload["name"],
            loop_id=payload.get("loop_id", ""),
            orchestration_id=payload.get("orchestration_id", ""),
        )
        return bundle

    def get_bundle(self, bundle_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM bundle_definitions WHERE id = ?", (bundle_id,)).fetchone()
        return self._decode_row(row) if row else None

    def get_bundle_by_loop_id(self, loop_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM bundle_definitions
                WHERE loop_id = ?
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """,
                (loop_id,),
            ).fetchone()
        return self._decode_row(row) if row else None

    def list_bundles(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM bundle_definitions ORDER BY updated_at DESC, created_at DESC").fetchall()
        return [self._decode_row(row) for row in rows]

    def delete_bundle(self, bundle_id: str) -> bool:
        with self.transaction() as connection:
            row = connection.execute("SELECT 1 FROM bundle_definitions WHERE id = ?", (bundle_id,)).fetchone()
            if row is None:
                return False
            connection.execute("DELETE FROM bundle_definitions WHERE id = ?", (bundle_id,))
        log_event(
            logger,
            logging.INFO,
            "db.bundle.deleted",
            "Deleted bundle definition",
            bundle_id=bundle_id,
        )
        return True

    def list_bundle_asset_ownership(self, bundle_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM bundle_asset_ownership
                WHERE bundle_id = ?
                ORDER BY asset_type ASC, asset_id ASC
                """,
                (bundle_id,),
            ).fetchall()
        return [self._decode_row(row) for row in rows]

    def get_bundle_asset_owner(self, asset_type: str, asset_id: str) -> str:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT bundle_id FROM bundle_asset_ownership
                WHERE asset_type = ? AND asset_id = ?
                """,
                (asset_type, asset_id),
            ).fetchone()
        return str(row["bundle_id"]) if row else ""

class RepositoryDefinitionRecordsMixin(
    RepositoryBundleRecordsMixin,
    RepositoryRunRecordsMixin,
    RepositoryLoopRecordsMixin,
):
    def get_loop_or_run(self, identifier: str) -> tuple[str, dict] | None:
        if loop := self.get_loop(identifier):
            return "loop", loop
        if run := self.get_run(identifier):
            return "run", run
        return None

class RepositoryAssetRecordsMixin(
    RepositoryRoleDefinitionRecordsMixin,
    RepositoryOrchestrationRecordsMixin,
):
    """Aggregate asset persistence behavior for orchestrations and role definitions."""

__all__ = ["LooporaRepository", "append_jsonl_with_mirrors", "os"]


class LooporaRepository(
    RepositorySchemaMixin,
    RepositoryRuntimeStateMixin,
    RepositoryDefinitionRecordsMixin,
    RepositoryAssetRecordsMixin,
    RepositoryAlignmentRecordsMixin,
    RepositoryRowDecodingMixin,
):
    def __init__(self, path: Path) -> None:
        self.path = path.expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self, *, configure_journal_mode: bool = False) -> sqlite3.Connection:
        for attempt in range(3):
            connection: sqlite3.Connection | None = None
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                connection = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
                connection.row_factory = sqlite3.Row
                connection.execute("PRAGMA foreign_keys=ON")
                connection.execute("PRAGMA busy_timeout=30000")
                if configure_journal_mode:
                    connection.execute("PRAGMA journal_mode=WAL").fetchone()
                return connection
            except sqlite3.OperationalError as exc:
                if connection is not None:
                    connection.close()
                retryable = self._is_retryable_connect_error(exc)
                attempt_number = attempt + 1
                if attempt == 2 or not retryable:
                    log_exception(
                        logger,
                        "db.connect.failed",
                        "Database connection failed",
                        error=exc,
                        path=self.path,
                        attempt=attempt_number,
                        configure_journal_mode=configure_journal_mode,
                        retryable=retryable,
                    )
                    raise
                sleep_seconds = 0.1 * attempt_number
                log_event(
                    logger,
                    logging.INFO,
                    "db.connect.retry",
                    "Retrying database connection after a transient failure",
                    path=self.path,
                    attempt=attempt_number,
                    configure_journal_mode=configure_journal_mode,
                    retryable=True,
                    sleep_seconds=sleep_seconds,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
                time.sleep(sleep_seconds)
        raise RuntimeError("sqlite connection retry loop exited unexpectedly")

    @staticmethod
    def _is_retryable_connect_error(exc: sqlite3.OperationalError) -> bool:
        message = str(exc).lower()
        return any(
            marker in message
            for marker in (
                "unable to open database file",
                "database is locked",
                "disk i/o error",
            )
        )

    @contextmanager
    def transaction(self, *, configure_journal_mode: bool = False) -> Iterator[sqlite3.Connection]:
        connection = self._connect(configure_journal_mode=configure_journal_mode)
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
