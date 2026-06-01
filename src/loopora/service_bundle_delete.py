from __future__ import annotations

from pathlib import Path

from loopora.diagnostics import get_logger
from loopora.service_bundle_graph_preflight import BundleGraphLinks, bundle_graph_links, preflight_bundle_graph_delete
from loopora.service_cleanup_diagnostics import best_effort_rmtree, cleanup_diagnostic_payload, log_cleanup_diagnostic
from loopora.service_types import LooporaError

logger = get_logger("loopora.service_bundle_assets")


class ServiceBundleDeleteMixin:
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
