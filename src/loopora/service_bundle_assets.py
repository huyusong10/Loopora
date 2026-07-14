from __future__ import annotations

from pathlib import Path

from loopora.bundles import BundleError, load_bundle_file, load_bundle_text
from loopora.bundle_io import resolve_bundle_file_path
from loopora.service_bundle_delete import ServiceBundleDeleteMixin
from loopora.service_bundle_export import BundleDeriveRequest, ServiceBundleExportMixin
from loopora.service_bundle_export import PLAN_FILE_SAVE_ERROR
from loopora.service_bundle_import import BundleImportRollbackState, BundleImportTarget, ServiceBundleImportMixin
from loopora.service_bundle_links import ServiceBundleLinksMixin
from loopora.service_bundle_loop_snapshot import ServiceBundleLoopSnapshotMixin
from loopora.service_bundle_projection import ServiceBundleProjectionMixin
from loopora.service_asset_common import record_bundle_asset_update_rollback_failure
from loopora.settings import app_home
from loopora.specs import compile_markdown_spec, save_spec_file, SpecError
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
            resolved_path = resolve_bundle_file_path(path)
            bundle = load_bundle_file(resolved_path)
        except (BundleError, OSError) as exc:
            raise LooporaError(str(exc)) from exc
        return self._import_normalized_bundle(
            bundle,
            replace_bundle_id=replace_bundle_id,
            imported_from_path=str(resolved_path),
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
        try:
            resolved_path = resolve_bundle_file_path(path)
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
        normalized_markdown = self._normalized_bundle_spec_markdown(spec_markdown)
        mutation_plan = self._bundle_update_mutation_plan(
            bundle_id,
            bundle,
            normalized_markdown,
        )
        payload = self._bundle_update_payload(
            bundle,
            description=description,
            collaboration_summary=collaboration_summary,
        )
        self._apply_bundle_update_with_rollback(
            bundle_id,
            bundle,
            payload,
            mutation_plan,
        )
        return self.get_bundle(bundle_id)

    def _normalized_bundle_spec_markdown(self, spec_markdown: str | None) -> str | None:
        if spec_markdown is None:
            return None
        normalized_markdown = str(spec_markdown or "").strip()
        if not normalized_markdown:
            raise LooporaError("bundle spec markdown is required")
        try:
            compile_markdown_spec(normalized_markdown)
        except SpecError as exc:
            raise LooporaError(str(exc)) from exc
        return normalized_markdown

    def _bundle_update_mutation_plan(
        self,
        bundle_id: str,
        bundle: dict,
        normalized_markdown: str | None,
    ) -> dict:
        loop_id = str(bundle.get("loop_id", "") or "").strip()
        if loop_id:
            snapshot = self._build_bundle_loop_snapshot(
                bundle_id,
                spec_markdown=normalized_markdown,
            )
            return {
                "loop_snapshot": snapshot,
                "loop_rollback": self._bundle_loop_snapshot_rollback_state(snapshot) if snapshot else None,
                "sidecar_rollback": None,
            }
        if normalized_markdown is not None:
            spec_path = self._bundle_spec_path(bundle_id)
            try:
                previous_text = spec_path.read_text(encoding="utf-8")
                existed = True
            except FileNotFoundError:
                previous_text = ""
                existed = False
            except (OSError, UnicodeDecodeError) as exc:
                raise LooporaError(PLAN_FILE_SAVE_ERROR) from exc
            return {
                "loop_snapshot": None,
                "loop_rollback": None,
                "sidecar_rollback": {
                    "path": spec_path,
                    "content": normalized_markdown + "\n",
                    "previous_text": previous_text,
                    "existed": existed,
                },
            }
        return {"loop_snapshot": None, "loop_rollback": None, "sidecar_rollback": None}

    def _apply_bundle_update_with_rollback(
        self,
        bundle_id: str,
        bundle: dict,
        payload: dict,
        mutation_plan: dict,
    ) -> None:
        bundle_saved = False
        snapshot_mutation_started = False
        sidecar_saved = False
        try:
            sidecar_saved = self._apply_bundle_sidecar_update(mutation_plan)
            snapshot_mutation_started = mutation_plan.get("loop_snapshot") is not None
            self._apply_bundle_loop_update(mutation_plan)
            saved = self.repository.update_bundle(bundle_id, payload)
            if not saved:
                raise LooporaError(f"failed to update bundle: {bundle_id}")
            bundle_saved = True
            self._sync_bundle_yaml(bundle_id)
        except OSError as exc:
            self._rollback_bundle_update_failure(
                bundle,
                mutation_plan,
                bundle_saved=bundle_saved,
                sidecar_saved=sidecar_saved,
                snapshot_mutation_started=snapshot_mutation_started,
            )
            raise LooporaError(PLAN_FILE_SAVE_ERROR) from exc
        except Exception:
            self._rollback_bundle_update_failure(
                bundle,
                mutation_plan,
                bundle_saved=bundle_saved,
                sidecar_saved=sidecar_saved,
                snapshot_mutation_started=snapshot_mutation_started,
            )
            raise

    def _apply_bundle_sidecar_update(self, mutation_plan: dict) -> bool:
        sidecar_rollback = mutation_plan.get("sidecar_rollback")
        if sidecar_rollback is None:
            return False
        save_spec_file(Path(sidecar_rollback["path"]), str(sidecar_rollback["content"]))
        return True

    def _apply_bundle_loop_update(self, mutation_plan: dict) -> None:
        snapshot = mutation_plan.get("loop_snapshot")
        if snapshot is None:
            return
        self._apply_bundle_loop_snapshot(snapshot)

    def _rollback_bundle_update_failure(
        self,
        bundle: dict,
        mutation_plan: dict,
        *,
        bundle_saved: bool,
        sidecar_saved: bool,
        snapshot_mutation_started: bool,
    ) -> None:
        if bundle_saved:
            self._restore_bundle_record_after_update_failure(bundle)
        sidecar_rollback = mutation_plan.get("sidecar_rollback")
        if sidecar_saved and sidecar_rollback is not None:
            self._restore_bundle_spec_sidecar_after_update_failure(sidecar_rollback, bundle)
        loop_rollback = mutation_plan.get("loop_rollback")
        if snapshot_mutation_started and loop_rollback is not None:
            self._restore_bundle_loop_snapshot_after_update_failure(loop_rollback, bundle)

    def update_bundle_metadata(
        self,
        bundle_id: str,
        *,
        description: str | None = None,
        collaboration_summary: str | None = None,
    ) -> dict:
        bundle = self.get_bundle(bundle_id)
        payload = self._bundle_update_payload(
            bundle,
            description=description,
            collaboration_summary=collaboration_summary,
        )
        self._apply_bundle_update_with_rollback(
            bundle_id,
            bundle,
            payload,
            mutation_plan={"loop_snapshot": None, "loop_rollback": None, "sidecar_rollback": None},
        )
        return self.get_bundle(bundle_id)

    def update_bundle_spec_markdown(self, bundle_id: str, markdown_text: str) -> dict:
        return self.update_bundle(bundle_id, spec_markdown=markdown_text)

    def _restore_bundle_record_after_update_failure(self, bundle: dict) -> None:
        try:
            self.repository.update_bundle(bundle["id"], self._bundle_payload_from_record(bundle))
        except Exception as exc:  # noqa: BLE001 - rollback diagnostics must preserve the original update error.
            record_bundle_asset_update_rollback_failure(self, bundle, exc)

    def _restore_bundle_loop_snapshot_after_update_failure(self, rollback_state: dict, bundle: dict) -> None:
        try:
            self._restore_bundle_loop_snapshot(rollback_state)
        except Exception as exc:  # noqa: BLE001 - rollback diagnostics must preserve the original update error.
            record_bundle_asset_update_rollback_failure(self, bundle, exc)

    def _restore_bundle_spec_sidecar_after_update_failure(self, rollback_state: dict, bundle: dict) -> None:
        try:
            path = Path(rollback_state["path"])
            if rollback_state.get("existed"):
                save_spec_file(path, str(rollback_state.get("previous_text", "")))
            else:
                path.unlink(missing_ok=True)
        except Exception as exc:  # noqa: BLE001 - rollback diagnostics must preserve the original update error.
            record_bundle_asset_update_rollback_failure(self, bundle, exc)

    @staticmethod
    def _bundle_update_payload(
        bundle: dict,
        *,
        description: str | None,
        collaboration_summary: str | None,
    ) -> dict:
        return {
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
