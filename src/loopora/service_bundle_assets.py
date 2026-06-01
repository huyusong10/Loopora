from __future__ import annotations

from pathlib import Path

from loopora.bundles import BundleError, load_bundle_file, load_bundle_text
from loopora.service_bundle_delete import ServiceBundleDeleteMixin
from loopora.service_bundle_export import BundleDeriveRequest, ServiceBundleExportMixin
from loopora.service_bundle_import import BundleImportRollbackState, BundleImportTarget, ServiceBundleImportMixin
from loopora.service_bundle_links import ServiceBundleLinksMixin
from loopora.service_bundle_loop_snapshot import ServiceBundleLoopSnapshotMixin
from loopora.service_bundle_projection import ServiceBundleProjectionMixin
from loopora.settings import app_home
from loopora.specs import compile_markdown_spec, SpecError
from loopora.service_types import LooporaError, LooporaNotFoundError
from loopora.service_local_asset_diagnostics import build_local_asset_diagnostics

__all__ = [
    "BundleDeriveRequest",
    "BundleImportRollbackState",
    "BundleImportTarget",
    "ServiceBundleAssetMixin",
]


class ServiceBundleAssetMixin(
    ServiceBundleDeleteMixin,
    ServiceBundleExportMixin,
    ServiceBundleProjectionMixin,
    ServiceBundleImportMixin,
    ServiceBundleLinksMixin,
    ServiceBundleLoopSnapshotMixin,
):
    def _bundle_dir(self, bundle_id: str) -> Path:
        return app_home() / "bundles" / bundle_id

    def _bundle_spec_path(self, bundle_id: str) -> Path:
        return self._bundle_dir(bundle_id) / "spec.md"

    def _bundle_yaml_path(self, bundle_id: str) -> Path:
        return self._bundle_dir(bundle_id) / "bundle.yml"

    def list_bundles(self) -> list[dict]:
        return [self._hydrate_bundle_links(bundle) for bundle in self.repository.list_bundles()]

    def list_bundle_exchange_items(self) -> list[dict]:
        """Return imported plan files without derived governance-card projections."""
        return self.list_bundles()

    def local_asset_diagnostics(self) -> dict:
        return build_local_asset_diagnostics(self)

    def list_bundle_governance_cards(self) -> list[dict]:
        # Compatibility alias for older callers. The default Web/API surface no
        # longer promotes bundle governance cards as a catalog product.
        return self.list_bundle_exchange_items()

    def get_bundle(self, bundle_id: str) -> dict:
        bundle = self.repository.get_bundle(bundle_id)
        if not bundle:
            raise LooporaNotFoundError(f"unknown bundle: {bundle_id}")
        return self._hydrate_bundle_links(bundle)

    def import_bundle_file(self, path: Path, *, replace_bundle_id: str | None = None) -> dict:
        try:
            bundle = load_bundle_file(path)
        except (BundleError, OSError) as exc:
            raise LooporaError(str(exc)) from exc
        return self._import_normalized_bundle(
            bundle,
            replace_bundle_id=replace_bundle_id,
            imported_from_path=str(path.expanduser().resolve()),
        )

    def import_bundle_text(
        self,
        raw_text: str,
        *,
        replace_bundle_id: str | None = None,
        imported_from_path: str = "",
    ) -> dict:
        try:
            bundle = load_bundle_text(raw_text)
        except BundleError as exc:
            raise LooporaError(str(exc)) from exc
        return self._import_normalized_bundle(
            bundle,
            replace_bundle_id=replace_bundle_id,
            imported_from_path=imported_from_path,
        )

    def preview_bundle_file(self, path: Path) -> dict:
        resolved_path = path.expanduser().resolve()
        try:
            bundle = load_bundle_file(resolved_path)
        except (BundleError, OSError) as exc:
            raise LooporaError(str(exc)) from exc
        return self._bundle_preview_payload(bundle, source_path=str(resolved_path))

    def preview_bundle_text(self, raw_text: str) -> dict:
        try:
            bundle = load_bundle_text(raw_text)
        except BundleError as exc:
            raise LooporaError(str(exc)) from exc
        return self._bundle_preview_payload(bundle)

    def update_bundle(
        self,
        bundle_id: str,
        *,
        description: str | None = None,
        collaboration_summary: str | None = None,
        spec_markdown: str | None = None,
        bump_revision: bool = True,  # noqa: ARG002 - retained for compatibility; revisions are not tracked.
    ) -> dict:
        bundle = self.get_bundle(bundle_id)
        normalized_markdown = None
        if spec_markdown is not None:
            normalized_markdown = str(spec_markdown or "").strip()
            if not normalized_markdown:
                raise LooporaError("bundle spec markdown is required")
            try:
                compile_markdown_spec(normalized_markdown)
            except SpecError as exc:
                raise LooporaError(str(exc)) from exc

        snapshot = None
        if str(bundle.get("loop_id", "") or "").strip():
            snapshot = self._build_bundle_loop_snapshot(
                bundle_id,
                spec_markdown=normalized_markdown,
            )
        elif normalized_markdown is not None:
            spec_path = self._bundle_spec_path(bundle_id)
            spec_path.parent.mkdir(parents=True, exist_ok=True)
            spec_path.write_text(normalized_markdown + "\n", encoding="utf-8")

        payload = {
            "name": bundle["name"],
            "description": str(bundle.get("description", "")) if description is None else str(description or "").strip(),
            "collaboration_summary": (
                str(bundle.get("collaboration_summary", ""))
                if collaboration_summary is None
                else str(collaboration_summary or "").strip()
            ),
            "workdir": bundle.get("workdir", ""),
            "loop_id": bundle.get("loop_id", ""),
            "orchestration_id": bundle.get("orchestration_id", ""),
            "role_definition_ids": bundle.get("role_definition_ids", []),
            "source_bundle_id": "",
            "revision": int(bundle.get("revision", 1) or 1),
            "imported_from_path": bundle.get("imported_from_path", ""),
        }
        if snapshot is not None:
            self._apply_bundle_loop_snapshot(snapshot)
        saved = self.repository.update_bundle(bundle_id, payload)
        if not saved:
            raise LooporaError(f"failed to update bundle: {bundle_id}")
        self._sync_bundle_yaml(bundle_id)
        return self.get_bundle(bundle_id)

    def update_bundle_metadata(
        self,
        bundle_id: str,
        *,
        description: str | None = None,
        collaboration_summary: str | None = None,
    ) -> dict:
        return self.update_bundle(
            bundle_id,
            description=description,
            collaboration_summary=collaboration_summary,
        )

    def update_bundle_spec_markdown(self, bundle_id: str, markdown_text: str) -> dict:
        return self.update_bundle(bundle_id, spec_markdown=markdown_text)
