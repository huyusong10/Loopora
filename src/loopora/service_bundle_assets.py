from __future__ import annotations

from pathlib import Path

from loopora.bundles import BundleError, load_bundle_file, load_bundle_text
from loopora.bundle_io import resolve_bundle_file_path
from loopora.service_bundle_import import BundleImportRollbackState, BundleImportTarget, ServiceBundleImportMixin
from loopora.service_bundle_loop_snapshot import ServiceBundleLoopSnapshotMixin
from loopora.settings import app_home
from loopora.specs import compile_markdown_spec, SpecError
from loopora.service_types import LooporaError, LooporaNotFoundError
from loopora.service_local_asset_diagnostics import build_local_asset_diagnostics


from loopora.diagnostics import get_logger

from loopora.service_bundle_graph_preflight import BundleGraphLinks, bundle_graph_links, preflight_bundle_graph_delete

from loopora.service_cleanup_diagnostics import best_effort_rmtree, cleanup_diagnostic_payload, log_cleanup_diagnostic


from dataclasses import dataclass


from loopora.bundles import bundle_to_yaml, normalize_bundle

from loopora.projections import LoopfileExportProjectionInput, build_loopfile_export_projection


from loopora.strategy_source import normalize_strategy_source, strategy_source_from_record



from loopora.markdown_tools import render_safe_markdown_html

from loopora.residual_risk_support import residual_risk_is_unmanaged

from loopora.service_bundle_control_summary import build_bundle_control_summary

from loopora.service_bundle_control_trace_mining import preview_list_items


from loopora.utils import structured_bool_is_true

class ServiceBundleProjectionMixin:
    def get_bundle_revision_summary(self, bundle_id: str) -> dict:
        self.get_bundle(bundle_id)
        return self._bundle_revision_summary()

    def get_bundle_governance_summary(self, bundle_id: str) -> dict:
        return self._bundle_governance_summary(self.export_bundle(bundle_id))

    def _bundle_preview_payload(
        self,
        bundle: dict,
        *,
        source_path: str = "",
        validation: dict | None = None,
    ) -> dict:
        normalized_yaml = bundle_to_yaml(bundle)
        control_summary = self._bundle_control_summary(bundle)
        return {
            "ok": True,
            "yaml": normalized_yaml,
            "source_path": source_path,
            "bundle": bundle,
            "metadata": bundle["metadata"],
            "spec_rendered_html": render_safe_markdown_html(bundle["spec"]["markdown"]),
            "roles": bundle["role_definitions"],
            "workflow_preview": self._bundle_workflow_preview(bundle),
            "control_summary": control_summary,
            "traceability": control_summary.get("traceability", {}),
            "diagnostics": list(control_summary.get("diagnostics") or []),
            "validation": validation or {"ok": True, "error": "", "source_path": source_path},
        }

    @staticmethod
    def _bundle_workflow_preview(bundle: dict) -> dict:
        role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
        preview_roles = []
        for role in bundle["workflow"]["roles"]:
            role_definition = role_by_key.get(role["role_definition_key"], {})
            preview_roles.append(
                {
                    **role,
                    "name": role_definition.get("name", role["id"]),
                    "archetype": role_definition.get("archetype", "custom"),
                    "description": role_definition.get("description", ""),
                    "posture_notes": role_definition.get("posture_notes", ""),
                }
            )
        return {
            **bundle["workflow"],
            "roles": preview_roles,
            "steps": list(bundle["workflow"]["steps"]),
        }

    @staticmethod
    def _bundle_control_summary(bundle: dict) -> dict:
        return build_bundle_control_summary(bundle)

    def _bundle_governance_summary(self, bundle: dict) -> dict:
        try:
            compiled_spec = compile_markdown_spec(str(bundle.get("spec", {}).get("markdown") or ""))
        except SpecError:
            compiled_spec = {"raw_sections": {}, "checks": []}
        raw_sections = compiled_spec.get("raw_sections") if isinstance(compiled_spec, dict) else {}
        if not isinstance(raw_sections, dict):
            raw_sections = {}
        control_summary = self._bundle_control_summary(bundle)
        coverage = dict(control_summary.get("coverage") or {})
        gatekeeper = dict(control_summary.get("gatekeeper") or {})
        gatekeeper_enabled = structured_bool_is_true(gatekeeper.get("enabled"))
        success_surface = list(control_summary.get("success_surface") or [])[:3]
        if not success_surface:
            success_surface = preview_list_items(str(raw_sections.get("Success Surface") or ""), limit=3)
        failure_modes = list(control_summary.get("fake_done_risks") or [])[:3]
        if not failure_modes:
            failure_modes = preview_list_items(str(raw_sections.get("Fake Done") or ""), limit=3)
        evidence_preferences = list(control_summary.get("evidence_preferences") or [])[:3]
        if not evidence_preferences:
            evidence_preferences = preview_list_items(str(raw_sections.get("Evidence Preferences") or ""), limit=3)
        if not evidence_preferences:
            evidence_preferences = list(control_summary.get("evidence") or [])[:3]
        residual_risk_policy = list(control_summary.get("residual_risk_policy") or [])[:3]
        raw_residual_risk = str(raw_sections.get("Residual Risk") or "").strip()
        if not residual_risk_policy and raw_residual_risk and not residual_risk_is_unmanaged(raw_residual_risk):
            residual_risk_policy = preview_list_items(raw_residual_risk, limit=3)
        return {
            "success_surface": success_surface,
            "failure_modes": failure_modes,
            "evidence_style": evidence_preferences,
            "loop_fit_reasons": list(control_summary.get("loop_fit_reasons") or [])[:3],
            "residual_risk_policy": residual_risk_policy,
            "execution_strategy": list(control_summary.get("execution_strategy") or [])[:3],
            "local_governance": list(control_summary.get("local_governance") or [])[:3],
            "role_postures": list(control_summary.get("role_postures") or [])[:3],
            "judgment_tradeoffs": list(control_summary.get("judgment_tradeoffs") or [])[:3],
            "coverage_summary": str(coverage.get("summary") or "").strip(),
            "coverage_targets": list(coverage.get("targets") or [])[:6],
            "workflow_shape": str((control_summary.get("workflow") or {}).get("summary") or "").strip(),
            "workflow_step_count": int((control_summary.get("workflow") or {}).get("step_count") or 0),
            "parallel_groups": list((control_summary.get("workflow") or {}).get("parallel_groups") or []),
            "gatekeeper": {
                "enabled": gatekeeper_enabled,
                "roles": list(gatekeeper.get("roles") or []),
                "finish_steps": list(gatekeeper.get("finish_steps") or []),
                "strictness": "evidence_refs_required" if gatekeeper_enabled else "not_configured",
            },
        }

    @staticmethod
    def _empty_bundle_governance_summary() -> dict:
        return {
            "success_surface": [],
            "failure_modes": [],
            "evidence_style": [],
            "loop_fit_reasons": [],
            "residual_risk_policy": [],
            "execution_strategy": [],
            "local_governance": [],
            "role_postures": [],
            "judgment_tradeoffs": [],
            "coverage_summary": "",
            "coverage_targets": [],
            "workflow_shape": "",
            "workflow_step_count": 0,
            "parallel_groups": [],
            "gatekeeper": {
                "enabled": False,
                "roles": [],
                "finish_steps": [],
                "strictness": "unavailable",
            },
        }

    @staticmethod
    def _bundle_revision_summary() -> dict:
        return {
            "revision": 1,
            "source_bundle_id": "",
            "source_bundle": None,
            "lineage_state": "not_tracked",
            "can_compare": False,
            "surface_deltas": [],
        }

class ServiceBundleLinksMixin:
    def _hydrate_bundle_links(self, bundle: dict) -> dict:
        hydrated = dict(bundle)
        loop_id = str(hydrated.get("loop_id", "") or "").strip()
        orchestration_id = str(hydrated.get("orchestration_id", "") or "").strip()
        role_definition_ids = [str(item).strip() for item in hydrated.get("role_definition_ids_json", []) if str(item).strip()]
        hydrated["role_definition_ids"] = role_definition_ids
        hydrated["managed_dir"] = str(self._bundle_dir(hydrated["id"]))
        hydrated["bundle_yaml_path"] = str(self._bundle_yaml_path(hydrated["id"]))
        if loop_id:
            try:
                hydrated["loop"] = self.get_loop(loop_id)
            except LooporaError:
                hydrated["loop"] = None
        else:
            hydrated["loop"] = None
        if orchestration_id:
            try:
                hydrated["orchestration"] = self.get_orchestration(orchestration_id)
            except LooporaError:
                hydrated["orchestration"] = None
        else:
            hydrated["orchestration"] = None
        role_definitions = []
        for role_definition_id in role_definition_ids:
            try:
                role_definitions.append(self.get_role_definition(role_definition_id))
            except LooporaError:
                continue
        hydrated["role_definitions"] = role_definitions
        return hydrated

    def _bundle_record_for_loop_id(self, loop_id: str) -> dict | None:
        normalized = str(loop_id or "").strip()
        if not normalized:
            return None
        for bundle in self.repository.list_bundles():
            if str(bundle.get("loop_id", "") or "").strip() == normalized:
                return bundle
        return None

    def _bundle_record_for_orchestration_id(self, orchestration_id: str) -> dict | None:
        normalized = str(orchestration_id or "").strip()
        if not normalized:
            return None
        for bundle in self.repository.list_bundles():
            if str(bundle.get("orchestration_id", "") or "").strip() == normalized:
                return bundle
        return None

    def _bundle_record_for_role_definition_id(self, role_definition_id: str) -> dict | None:
        normalized = str(role_definition_id or "").strip()
        if not normalized:
            return None
        for bundle in self.repository.list_bundles():
            role_ids = [
                str(item).strip()
                for item in (bundle.get("role_definition_ids") or bundle.get("role_definition_ids_json") or [])
                if str(item).strip()
            ]
            if normalized in role_ids:
                return bundle
        return None

    def _touch_bundle_for_orchestration(self, orchestration_id: str) -> dict | None:
        bundle = self._bundle_record_for_orchestration_id(orchestration_id)
        if not bundle:
            return None
        return self.update_bundle(bundle["id"])

    def _touch_bundle_for_role_definition(self, role_definition_id: str) -> dict | None:
        bundle = self._bundle_record_for_role_definition_id(role_definition_id)
        if not bundle:
            return None
        return self.update_bundle(bundle["id"])

@dataclass(frozen=True)
class BundleDeriveRequest:
    loop_id: str
    bundle_id: str = ""
    name: str | None = None
    description: str = ""
    collaboration_summary: str = ""
    source_bundle_id: str = ""
    revision: int = 1

def _derive_bundle_request_from_args(
    request: BundleDeriveRequest | str,
    raw_request: dict[str, object],
) -> BundleDeriveRequest:
    if isinstance(request, BundleDeriveRequest):
        if raw_request:
            raise TypeError("bundle derive request object cannot be combined with keyword fields")
        return request

    fields = dict(raw_request)
    derive_request = BundleDeriveRequest(
        loop_id=request,
        bundle_id=fields.pop("bundle_id", ""),
        name=fields.pop("name", None),
        description=fields.pop("description", ""),
        collaboration_summary=fields.pop("collaboration_summary", ""),
        source_bundle_id=fields.pop("source_bundle_id", ""),
        revision=fields.pop("revision", 1),
    )
    if fields:
        unexpected_fields = ", ".join(sorted(fields))
        raise TypeError(f"unexpected bundle derive request fields: {unexpected_fields}")
    return derive_request

class ServiceBundleExportMixin:
    def export_bundle(self, bundle_id: str) -> dict:
        bundle = self.get_bundle(bundle_id)
        return self.derive_bundle_from_loop(
            bundle["loop_id"],
            bundle_id=bundle["id"],
            name=bundle["name"],
            description=str(bundle.get("description", "")),
            collaboration_summary=str(bundle.get("collaboration_summary", "")),
        )

    def export_bundle_yaml(self, bundle_id: str) -> str:
        return bundle_to_yaml(self.export_bundle(bundle_id))

    def derive_bundle_from_loop(self, request: BundleDeriveRequest | str, **raw_request: object) -> dict:
        request = _derive_bundle_request_from_args(request, raw_request)
        loop_id = request.loop_id
        loop = self.get_loop(loop_id)
        strategy_source = normalize_strategy_source(strategy_source_from_record(loop) or {})
        prompt_files = dict(loop.get("prompt_files") or {})
        role_definition_by_id = {}
        for role in strategy_source.get("roles", []):
            role_definition_id = str(role.get("role_definition_id", "") or "").strip()
            if not role_definition_id or role_definition_id in role_definition_by_id:
                continue
            try:
                role_definition_by_id[role_definition_id] = self.get_role_definition(role_definition_id)
            except LooporaError:
                role_definition_by_id[role_definition_id] = None
        try:
            return normalize_bundle(
                build_loopfile_export_projection(
                    LoopfileExportProjectionInput(
                        loop=loop,
                        loop_id=loop_id,
                        strategy_source=strategy_source,
                        prompt_files=prompt_files,
                        role_definition_by_id=role_definition_by_id,
                        bundle_id=request.bundle_id,
                        name=request.name,
                        description=request.description,
                        collaboration_summary=request.collaboration_summary,
                    )
                )
            )
        except (BundleError, ValueError) as exc:
            raise LooporaError(str(exc)) from exc

    def write_bundle_file(self, bundle_id: str, path: Path) -> Path:
        target = path.expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.export_bundle_yaml(bundle_id), encoding="utf-8")
        return target

    def _sync_bundle_yaml(self, bundle_id: str) -> None:
        self._bundle_yaml_path(bundle_id).parent.mkdir(parents=True, exist_ok=True)
        self._bundle_yaml_path(bundle_id).write_text(self.export_bundle_yaml(bundle_id), encoding="utf-8")

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
