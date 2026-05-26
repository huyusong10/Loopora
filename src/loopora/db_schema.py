from __future__ import annotations

import logging
import sqlite3

from loopora.db_shared import logger
from loopora.diagnostics import log_event
from loopora.service_types import LooporaConflictError

CURRENT_SCHEMA_VERSION = 3


class RepositorySchemaMixin:
    def _init_db(self) -> None:
        with self.transaction(configure_journal_mode=True) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS loop_definitions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    orchestration_id TEXT NOT NULL DEFAULT '',
                    orchestration_name TEXT NOT NULL DEFAULT '',
                    workdir TEXT NOT NULL,
                    spec_path TEXT NOT NULL,
                    spec_markdown TEXT NOT NULL,
                    compiled_spec_json TEXT NOT NULL,
                    executor_kind TEXT NOT NULL DEFAULT 'codex',
                    executor_mode TEXT NOT NULL DEFAULT 'preset',
                    command_cli TEXT NOT NULL DEFAULT '',
                    command_args_text TEXT NOT NULL DEFAULT '',
                    model TEXT NOT NULL,
                    reasoning_effort TEXT NOT NULL,
                    completion_mode TEXT NOT NULL DEFAULT 'gatekeeper',
                    iteration_interval_seconds REAL NOT NULL DEFAULT 0,
                    max_iters INTEGER NOT NULL,
                    max_role_retries INTEGER NOT NULL,
                    delta_threshold REAL NOT NULL,
                    trigger_window INTEGER NOT NULL,
                    regression_window INTEGER NOT NULL,
                    role_models_json TEXT NOT NULL,
                    workflow_json TEXT NOT NULL DEFAULT '{}',
                    latest_run_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS loop_runs (
                    id TEXT PRIMARY KEY,
                    loop_id TEXT NOT NULL REFERENCES loop_definitions(id),
                    orchestration_id TEXT NOT NULL DEFAULT '',
                    orchestration_name TEXT NOT NULL DEFAULT '',
                    workdir TEXT NOT NULL,
                    spec_path TEXT NOT NULL,
                    spec_markdown TEXT NOT NULL,
                    compiled_spec_json TEXT NOT NULL,
                    executor_kind TEXT NOT NULL DEFAULT 'codex',
                    executor_mode TEXT NOT NULL DEFAULT 'preset',
                    command_cli TEXT NOT NULL DEFAULT '',
                    command_args_text TEXT NOT NULL DEFAULT '',
                    model TEXT NOT NULL,
                    reasoning_effort TEXT NOT NULL,
                    completion_mode TEXT NOT NULL DEFAULT 'gatekeeper',
                    iteration_interval_seconds REAL NOT NULL DEFAULT 0,
                    max_iters INTEGER NOT NULL,
                    max_role_retries INTEGER NOT NULL,
                    delta_threshold REAL NOT NULL,
                    trigger_window INTEGER NOT NULL,
                    regression_window INTEGER NOT NULL,
                    role_models_json TEXT NOT NULL,
                    workflow_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL,
                    stop_requested INTEGER NOT NULL DEFAULT 0,
                    current_iter INTEGER NOT NULL DEFAULT 0,
                    active_role TEXT,
                    runner_pid INTEGER,
                    child_pid INTEGER,
                    queued_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    error_message TEXT,
                    last_verdict_json TEXT,
                    task_verdict_json TEXT,
                    summary_md TEXT,
                    runs_dir TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS run_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL REFERENCES loop_runs(id),
                    created_at TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    role TEXT,
                    payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS run_takeaway_projections (
                    run_id TEXT NOT NULL REFERENCES loop_runs(id) ON DELETE CASCADE,
                    source_event_id INTEGER NOT NULL REFERENCES run_events(id) ON DELETE CASCADE,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (run_id, source_event_id)
                );

                CREATE TABLE IF NOT EXISTS workdir_locks (
                    workdir TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES loop_runs(id),
                    acquired_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS orchestration_definitions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    workflow_json TEXT NOT NULL,
                    prompt_files_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS role_definitions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    archetype TEXT NOT NULL,
                    prompt_ref TEXT NOT NULL,
                    prompt_markdown TEXT NOT NULL,
                    posture_notes TEXT NOT NULL DEFAULT '',
                    executor_kind TEXT NOT NULL DEFAULT 'codex',
                    executor_mode TEXT NOT NULL DEFAULT 'preset',
                    command_cli TEXT NOT NULL DEFAULT 'codex',
                    command_args_text TEXT NOT NULL DEFAULT '',
                    model TEXT NOT NULL DEFAULT '',
                    reasoning_effort TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS bundle_definitions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    collaboration_summary TEXT NOT NULL DEFAULT '',
                    workdir TEXT NOT NULL DEFAULT '',
                    loop_id TEXT NOT NULL DEFAULT '',
                    orchestration_id TEXT NOT NULL DEFAULT '',
                    role_definition_ids_json TEXT NOT NULL DEFAULT '[]',
                    source_bundle_id TEXT NOT NULL DEFAULT '',
                    revision INTEGER NOT NULL DEFAULT 1,
                    imported_from_path TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS bundle_asset_ownership (
                    bundle_id TEXT NOT NULL REFERENCES bundle_definitions(id) ON DELETE CASCADE,
                    asset_type TEXT NOT NULL CHECK (asset_type IN ('loop', 'orchestration', 'role_definition')),
                    asset_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (bundle_id, asset_type, asset_id),
                    UNIQUE (asset_type, asset_id)
                );

                CREATE TABLE IF NOT EXISTS local_asset_roots (
                    resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    path TEXT NOT NULL,
                    workdir TEXT NOT NULL DEFAULT '',
                    owner_id TEXT NOT NULL DEFAULT '',
                    state TEXT NOT NULL DEFAULT 'active' CHECK (state IN ('active', 'cleaned', 'orphaned')),
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (resource_type, resource_id, path)
                );

                CREATE TABLE IF NOT EXISTS alignment_sessions (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    executor_kind TEXT NOT NULL DEFAULT 'codex',
                    executor_mode TEXT NOT NULL DEFAULT 'preset',
                    command_cli TEXT NOT NULL DEFAULT '',
                    command_args_text TEXT NOT NULL DEFAULT '',
                    model TEXT NOT NULL DEFAULT '',
                    reasoning_effort TEXT NOT NULL DEFAULT '',
                    workdir TEXT NOT NULL,
                    bundle_path TEXT NOT NULL,
                    transcript_json TEXT NOT NULL DEFAULT '[]',
                    validation_json TEXT NOT NULL DEFAULT '{}',
                    alignment_stage TEXT NOT NULL DEFAULT 'clarifying',
                    working_agreement_json TEXT NOT NULL DEFAULT '{}',
                    executor_session_ref_json TEXT NOT NULL DEFAULT '{}',
                    linked_bundle_id TEXT NOT NULL DEFAULT '',
                    linked_loop_id TEXT NOT NULL DEFAULT '',
                    linked_run_id TEXT NOT NULL DEFAULT '',
                    active_child_pid INTEGER,
                    stop_requested INTEGER NOT NULL DEFAULT 0,
                    repair_attempts INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    finished_at TEXT,
                    error_message TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS alignment_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL REFERENCES alignment_sessions(id),
                    created_at TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_run_takeaway_projections_cutoff
                    ON run_takeaway_projections(run_id, source_event_id DESC);
                CREATE INDEX IF NOT EXISTS idx_bundle_asset_ownership_bundle
                    ON bundle_asset_ownership(bundle_id);
                CREATE INDEX IF NOT EXISTS idx_local_asset_roots_lookup
                    ON local_asset_roots(resource_type, resource_id, state);
                """
            )
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
        if version == 0 and cls._schema_has_current_v3_shape(connection):
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

    @staticmethod
    def _schema_has_current_v3_shape(connection: sqlite3.Connection) -> bool:
        required_columns = {
            "loop_definitions": {"id", "orchestration_id", "executor_kind", "workflow_json", "completion_mode"},
            "loop_runs": {"id", "orchestration_id", "executor_kind", "workflow_json", "task_verdict_json", "completion_mode"},
            "alignment_sessions": {"id", "alignment_stage", "working_agreement_json", "executor_session_ref_json", "linked_run_id"},
            "local_asset_roots": {"resource_type", "resource_id", "path", "state"},
            "bundle_asset_ownership": {"bundle_id", "asset_type", "asset_id"},
        }
        for table, columns in required_columns.items():
            existing = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}
            if not columns <= existing:
                return False
        return True
