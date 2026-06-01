from __future__ import annotations

from loopora.bundles import bundle_to_yaml
from loopora.markdown_tools import render_safe_markdown_html
from loopora.residual_risk_support import residual_risk_is_unmanaged
from loopora.service_bundle_control_summary import build_bundle_control_summary
from loopora.service_bundle_control_trace_preview import preview_list_items
from loopora.specs import SpecError, compile_markdown_spec
from loopora.structured_booleans import structured_bool_is_true


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
