from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shutil

from loopora.diagnostics import get_logger
from loopora.service_bundle_graph_preflight import bundle_graph_links
from loopora.service_cleanup_diagnostics import best_effort_rmtree
from loopora.utils import make_id

logger = get_logger("loopora.service_bundle_import")


@dataclass(frozen=True)
class BundleImportTarget:
    target_bundle_id: str
    existing: dict | None
    old_local_paths: list[Path]
    bundle_dir: Path
    backup_dir: Path | None
    prompt_ref_namespace: str
    imported_from_path: str


@dataclass
class BundleImportRollbackState:
    target: BundleImportTarget
    created_role_ids: list[str] = field(default_factory=list)
    orchestration_id: str = ""
    loop_id: str = ""
    saved: object | None = None
    committed: bool = False


class ServiceBundleImportCleanupMixin:
    def _rollback_failed_bundle_import(self, state: BundleImportRollbackState) -> None:
        if state.committed:
            return
        target = state.target
        if state.saved is not None:
            if target.existing:
                self.repository.update_bundle(
                    target.target_bundle_id,
                    self._bundle_payload_from_record(target.existing),
                )
            else:
                self.repository.delete_bundle(target.target_bundle_id)
        self._cleanup_created_bundle_assets(
            owner_id=target.target_bundle_id,
            loop_id=state.loop_id,
            orchestration_id=state.orchestration_id,
            role_definition_ids=state.created_role_ids,
        )
        self._restore_bundle_dir_after_failed_import(
            bundle_dir=target.bundle_dir,
            backup_dir=target.backup_dir,
            had_existing=bool(target.existing),
        )

    def _cleanup_bundle_import_backup_dir(self, target: BundleImportTarget) -> None:
        if not target.backup_dir or not target.backup_dir.exists():
            return
        best_effort_rmtree(
            target.backup_dir,
            logger,
            operation="bundle_backup_cleanup",
            owner_id=target.target_bundle_id,
        )

    def _delete_replaced_bundle_artifact_paths(self, target_bundle_id: str, old_local_paths: list[Path]) -> None:
        for path in old_local_paths:
            best_effort_rmtree(
                path,
                logger,
                operation="bundle_replaced_artifact_delete",
                owner_id=target_bundle_id,
            )
            self._mark_local_asset_cleanup_by_path(
                path,
                operation="bundle_replaced_artifact_delete",
                owner_id=target_bundle_id,
            )

    def _assert_bundle_links_replaceable(self, bundle: dict) -> None:
        self._preflight_existing_bundle_graph(bundle)

    def _preflight_existing_bundle_graph(self, bundle: dict) -> list[Path]:
        return self._preflight_bundle_graph_delete(bundle, links=bundle_graph_links(bundle))

    def _backup_bundle_dir(self, bundle_dir: Path) -> Path | None:
        if not bundle_dir.exists():
            return None
        backup_dir = bundle_dir.with_name(f"{bundle_dir.name}.{make_id('backup')}")
        shutil.copytree(bundle_dir, backup_dir)
        return backup_dir

    def _restore_bundle_dir_after_failed_import(
        self,
        *,
        bundle_dir: Path,
        backup_dir: Path | None,
        had_existing: bool,
    ) -> None:
        if had_existing:
            if backup_dir is None:
                return
            best_effort_rmtree(
                bundle_dir,
                logger,
                operation="bundle_failed_import_restore",
                owner_id=bundle_dir.name,
            )
            try:
                shutil.copytree(backup_dir, bundle_dir)
            except OSError as exc:
                self._record_bundle_cleanup_failure(
                    operation="bundle_failed_import_restore",
                    resource_type="path",
                    resource_id=bundle_dir,
                    owner_id=bundle_dir.name,
                    error=exc,
                )
            return
        best_effort_rmtree(
            bundle_dir,
            logger,
            operation="bundle_failed_import_cleanup",
            owner_id=bundle_dir.name,
        )
        self._mark_local_asset_cleanup_by_path(
            bundle_dir,
            operation="bundle_failed_import_cleanup",
            owner_id=bundle_dir.name,
        )

    def _bundle_payload_from_record(self, bundle: dict) -> dict:
        role_definition_ids = [
            str(item).strip()
            for item in (bundle.get("role_definition_ids") or bundle.get("role_definition_ids_json") or [])
            if str(item).strip()
        ]
        return {
            "name": bundle["name"],
            "description": bundle.get("description", ""),
            "collaboration_summary": bundle.get("collaboration_summary", ""),
            "workdir": bundle.get("workdir", ""),
            "loop_id": bundle.get("loop_id", ""),
            "orchestration_id": bundle.get("orchestration_id", ""),
            "role_definition_ids": role_definition_ids,
            "source_bundle_id": bundle.get("source_bundle_id", ""),
            "revision": int(bundle.get("revision", 1) or 1),
            "imported_from_path": bundle.get("imported_from_path", ""),
        }

    def _cleanup_created_bundle_assets(
        self,
        *,
        owner_id: str,
        loop_id: str,
        orchestration_id: str,
        role_definition_ids: list[str],
    ) -> None:
        if loop_id:
            try:
                self.delete_loop(loop_id, allow_bundle_owned=True)
            except Exception as exc:  # noqa: BLE001 - rollback cleanup must preserve the original import failure.
                self._record_bundle_cleanup_failure(
                    operation="bundle_import_rollback",
                    resource_type="loop",
                    resource_id=loop_id,
                    owner_id=owner_id,
                    error=exc,
                )
        if orchestration_id:
            try:
                self.delete_orchestration(orchestration_id, allow_bundle_owned=True)
            except Exception as exc:  # noqa: BLE001 - rollback cleanup must preserve the original import failure.
                self._record_bundle_cleanup_failure(
                    operation="bundle_import_rollback",
                    resource_type="orchestration",
                    resource_id=orchestration_id,
                    owner_id=owner_id,
                    error=exc,
                )
        for role_definition_id in role_definition_ids:
            try:
                self.delete_role_definition(role_definition_id, allow_bundle_owned=True)
            except Exception as exc:  # noqa: BLE001 - rollback cleanup must preserve the original import failure.
                self._record_bundle_cleanup_failure(
                    operation="bundle_import_rollback",
                    resource_type="role_definition",
                    resource_id=role_definition_id,
                    owner_id=owner_id,
                    error=exc,
                )
                continue
