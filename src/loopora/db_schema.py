from __future__ import annotations

import logging
import sqlite3

from loopora.db_shared import logger
from loopora.db_schema_v3 import CURRENT_SCHEMA_VERSION, V3_SCHEMA_SQL, schema_has_current_v3_shape
from loopora.diagnostics import log_event
from loopora.service_types import LooporaConflictError

FUTURE_SCHEMA_ERROR_PREFIX = "App database was created by a newer Loopora schema:"


def future_schema_error_message(database_version: int, *, supported_version: int = CURRENT_SCHEMA_VERSION) -> str:
    return (
        f"{FUTURE_SCHEMA_ERROR_PREFIX} database version {database_version} is newer than supported version "
        f"{supported_version}. Use a matching or newer Loopora version, or inspect App-state recovery before "
        "previewing an app-scope reset."
    )


class RepositorySchemaMixin:
    def _validate_read_only_db(self) -> None:
        connection = self._connect(configure_journal_mode=False)
        try:
            version = self._schema_user_version(connection)
            if version > CURRENT_SCHEMA_VERSION:
                self._raise_future_schema_error(version)
            if version == CURRENT_SCHEMA_VERSION or (version == 0 and schema_has_current_v3_shape(connection)):
                return
        finally:
            connection.close()
        raise LooporaConflictError(
            "Loopora v3 development reset required: existing local database schema "
            f"version {version} is not compatible. Run `loopora dev reset --scope app --workdir <project>` "
            "to preview the local App database reset, then rerun with `--yes` after reviewing planned deletions."
        )

    def _init_db(self) -> None:
        self._reject_future_schema_before_writes()
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
            cls._raise_future_schema_error(version)
        if version == CURRENT_SCHEMA_VERSION:
            return
        if version == 0 and schema_has_current_v3_shape(connection):
            cls._set_schema_user_version(connection, CURRENT_SCHEMA_VERSION)
            return
        raise LooporaConflictError(
            "Loopora v3 development reset required: existing local database schema "
            f"version {version} is not compatible. Run `loopora dev reset --scope app --workdir <project>` "
            "to preview the local App database reset, then rerun with `--yes` after reviewing planned deletions."
        )

    def _reject_future_schema_before_writes(self) -> None:
        connection = self._connect(configure_journal_mode=False)
        try:
            version = self._schema_user_version(connection)
        finally:
            connection.close()
        if version > CURRENT_SCHEMA_VERSION:
            self._raise_future_schema_error(version)

    @classmethod
    def _raise_future_schema_error(cls, version: int) -> None:
        log_event(
            logger,
            logging.INFO,
            "db.schema.future_version",
            "Database schema was created by a newer Loopora version",
            database_version=version,
            supported_version=CURRENT_SCHEMA_VERSION,
        )
        raise LooporaConflictError(future_schema_error_message(version))

    @staticmethod
    def _schema_user_version(connection: sqlite3.Connection) -> int:
        row = connection.execute("PRAGMA user_version").fetchone()
        return int(row[0] or 0)

    @staticmethod
    def _set_schema_user_version(connection: sqlite3.Connection, version: int) -> None:
        connection.execute(f"PRAGMA user_version = {int(version)}")
