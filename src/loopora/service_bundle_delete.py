from __future__ import annotations

from pathlib import Path

from loopora.diagnostics import get_logger
from loopora.service_bundle_graph_preflight import BundleGraphLinks, bundle_graph_links, preflight_bundle_graph_delete
from loopora.service_cleanup_diagnostics import best_effort_rmtree, cleanup_diagnostic_payload, log_cleanup_diagnostic
from loopora.service_types import ACTIVE_RUN_STATUSES, LooporaError

logger = get_logger("loopora.service_bundle_assets")


class ServiceBundleDeleteMixin:
    def preview_bundle_delete(self, bundle_id: str) -> dict:
        bundle = self.get_bundle(bundle_id)
        links = bundle_graph_links(bundle)
        runs = self.repository.list_runs_for_loop(links.loop_id, limit=5000) if links.loop_id else []
        active_run_ids = [
            str(run.get("id") or "").strip()
            for run in runs
            if isinstance(run, dict)
            and str(run.get("status") or "").strip() in ACTIVE_RUN_STATUSES
            and str(run.get("id") or "").strip()
        ]
        preflight_error = ""
        try:
            self._preflight_bundle_graph_delete(bundle, links=links)
        except LooporaError as exc:
            preflight_error = str(exc)
        blockers = []
        if active_run_ids:
            blockers.append({"kind": "active_runs", "run_ids": active_run_ids})
        if preflight_error and (not active_run_ids or "active loop runs" not in preflight_error):
            blockers.append({"kind": "preflight", "message": preflight_error})
        run_ids = [
            str(run.get("id") or "").strip()
            for run in runs
            if isinstance(run, dict) and str(run.get("id") or "").strip()
        ]
        return {
            "status": "dry_run",
            "dry_run": True,
            "delete_allowed": not preflight_error and not active_run_ids,
            "id": bundle["id"],
            "name": bundle.get("name", ""),
            "workdir": bundle.get("workdir", ""),
            "would_delete": {
                "bundle": bundle["id"],
                "linked_loop": links.loop_id,
                "linked_orchestration": links.orchestration_id,
                "linked_role_definition_count": len(links.role_definition_ids),
                "linked_role_definition_ids": links.role_definition_ids,
                "linked_run_count": len(run_ids),
                "linked_run_ids": run_ids,
            },
            "blocked_by_active_runs": active_run_ids,
            "blockers": blockers,
            "does_not_delete": [
                "original_exported_yaml_file",
                "source_project_workdir",
                "non_bundle_owned_assets",
                "external_provider_history",
            ],
        }

    def delete_bundle(self, bundle_id: str) -> dict:
        bundle = self.get_bundle(bundle_id)
        cleanup_warnings: list[dict] = []
        self._delete_bundle_links(bundle, cleanup_warnings=cleanup_warnings)
        result = {"id": bundle_id, "deleted": True}
        if cleanup_warnings:
            result["local_cleanup"] = "partial_failed"
            result["cleanup_warnings"] = cleanup_warnings
        return result

    def _delete_bundle_links(
        self,
        bundle: dict,
        *,
        delete_managed_dir: bool = True,
        cleanup_warnings: list[dict] | None = None,
    ) -> None:
        links = bundle_graph_links(bundle)
        local_paths = self._preflight_bundle_graph_delete(bundle, links=links)
        deleted = self.repository.delete_bundle_graph(bundle["id"])
        if not deleted:
            raise LooporaError(f"failed to delete bundle: {bundle['id']}")
        self._delete_bundle_link_artifact_paths(bundle["id"], local_paths, cleanup_warnings=cleanup_warnings)
        self._delete_bundle_managed_dir(bundle["id"], delete_managed_dir=delete_managed_dir, cleanup_warnings=cleanup_warnings)

    def _delete_bundle_link_artifact_paths(
        self,
        bundle_id: str,
        local_paths: list[Path],
        *,
        cleanup_warnings: list[dict] | None = None,
    ) -> None:
        for path in local_paths:
            best_effort_rmtree(
                path,
                logger,
                operation="bundle_link_artifact_delete",
                owner_id=bundle_id,
                on_failure=self._cleanup_warning_collector(cleanup_warnings),
            )
            self._mark_local_asset_cleanup_by_path(
                path,
                operation="bundle_link_artifact_delete",
                owner_id=bundle_id,
            )

    def _delete_bundle_managed_dir(
        self,
        bundle_id: str,
        *,
        delete_managed_dir: bool,
        cleanup_warnings: list[dict] | None = None,
    ) -> None:
        if not delete_managed_dir:
            return
        bundle_dir = self._bundle_dir(bundle_id)
        if bundle_dir.exists():
            best_effort_rmtree(
                bundle_dir,
                logger,
                operation="bundle_managed_dir_delete",
                owner_id=bundle_id,
                on_failure=self._cleanup_warning_collector(cleanup_warnings),
            )
        self._mark_local_asset_cleanup_by_path(
            bundle_dir,
            operation="bundle_managed_dir_delete",
            owner_id=bundle_id,
        )

    @staticmethod
    def _cleanup_warning_collector(cleanup_warnings: list[dict] | None):
        if cleanup_warnings is None:
            return None

        def collect(payload: dict) -> None:
            cleanup_warnings.append(
                {
                    "operation": str(payload.get("operation") or ""),
                    "resource_type": str(payload.get("resource_type") or ""),
                    "resource_id": str(payload.get("resource_id") or ""),
                    "owner_id": str(payload.get("owner_id") or ""),
                    "error_type": str(payload.get("error_type") or ""),
                    "error": str(payload.get("error") or payload.get("error_message") or ""),
                }
            )

        return collect

    def _preflight_bundle_graph_delete(
        self,
        bundle: dict,
        *,
        links: BundleGraphLinks,
    ) -> list[Path]:
        return preflight_bundle_graph_delete(self.repository, bundle, links)

    @staticmethod
    def _record_bundle_cleanup_failure(
        *,
        operation: str,
        resource_type: str,
        resource_id: object,
        owner_id: object,
        error: BaseException,
    ) -> None:
        payload = cleanup_diagnostic_payload(
            operation=operation,
            resource_type=resource_type,
            resource_id=resource_id,
            owner_id=owner_id,
            error=error,
        )
        log_cleanup_diagnostic(logger, **payload)
