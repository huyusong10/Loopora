from __future__ import annotations

import json
import logging

from loopora.db_bundle_graph_records import RepositoryBundleGraphRecordsMixin
from loopora.db_shared import logger
from loopora.diagnostics import log_event
from loopora.utils import utc_now


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
