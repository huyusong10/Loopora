from __future__ import annotations

import logging
import sqlite3

from loopora.db_shared import logger
from loopora.db_schema_v3 import CURRENT_SCHEMA_VERSION, V3_SCHEMA_SQL, schema_has_current_v3_shape
from loopora.diagnostics import log_event
from loopora.service_types import LooporaConflictError


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
