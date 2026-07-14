from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from fastapi import Request
from fastapi.responses import HTMLResponse

from loopora.markdown_tools import render_safe_markdown_html
from loopora.service import LooporaError
from loopora.web_bundle_inputs import (
    _normalize_bundle_derive_form,
    _normalize_bundle_import_form,
)
from loopora.web_start_context import request_all_projects_scope_href
from loopora.web_start_context import request_workdir_context
from loopora.web_url_utils import with_query_params
from loopora.workdir_inputs import same_workdir_identity


class WebRouteBundlePagesMixin:
    def render_bundles(  # noqa: PLR0913 - catalog page renders independent import and derive form states.
        self,
        request: Request,
        *,
        import_values: Mapping[str, object] | None = None,
        import_error: str | None = None,
        import_recovery: Mapping[str, object] | None = None,
        derive_values: Mapping[str, object] | None = None,
        derive_error: str | None = None,
        derive_recovery: Mapping[str, object] | None = None,
    ) -> HTMLResponse:
        workdir_context = request_workdir_context(request)
        all_loops = self.svc().list_loops()
        loops = _bundle_derive_loops(all_loops, workdir_context=workdir_context)
        all_bundles = self._bundle_list_items(workdir_context="")
        bundles = _bundle_list_items_for_workdir(all_bundles, workdir_context=workdir_context)
        return self.templates.TemplateResponse(
            request,
            "bundles.html",
            {
                "request": request,
                "bundles": bundles,
                "loops": loops,
                "import_values": _normalize_bundle_import_form(import_values),
                "derive_values": _normalize_bundle_derive_form(derive_values),
                "import_error": import_error,
                "import_recovery": dict(import_recovery or {}),
                "derive_error": derive_error,
                "derive_recovery": dict(derive_recovery or {}),
                "all_bundle_count": len(all_bundles),
                "hidden_bundle_count": max(0, len(all_bundles) - len(bundles)),
                "all_loop_count": len(all_loops),
                "hidden_loop_count": max(0, len(all_loops) - len(loops)),
                "bundles_all_href": request_all_projects_scope_href(request, "/bundles"),
                "bundle_import_form_action": with_query_params(
                    "/bundles/import",
                    workdir=workdir_context or None,
                ),
                "bundle_derive_form_action": with_query_params(
                    "/bundles/derive",
                    workdir=workdir_context or None,
                ),
                "access_state": self.access_state,
            },
        )

    def _bundle_list_items(self, *, workdir_context: str = "") -> list[dict]:
        items = []
        for bundle in self.svc().list_bundle_exchange_items():
            item = dict(bundle)
            bundle_id = str(item.get("id") or "").strip()
            loop_id = str(item.get("loop_id") or "").strip()
            loop = item.get("loop") if isinstance(item.get("loop"), dict) else None
            bundle_workdir = _bundle_list_item_workdir(item, loop=loop)
            if workdir_context and not same_workdir_identity(bundle_workdir, workdir_context):
                continue
            item["detail_href"] = with_query_params(f"/bundles/{bundle_id}", workdir=bundle_workdir or None)
            item["export_href"] = with_query_params(
                f"/bundles/{bundle_id}/export",
                workdir=bundle_workdir or None,
            )
            item["loop_detail_href"] = (
                with_query_params(f"/loops/{loop_id}", workdir=bundle_workdir or None) if loop_id else ""
            )
            item["start_run_action"] = with_query_params(
                f"/bundles/{bundle_id}/runs",
                workdir=bundle_workdir or None,
            )
            item["agent_entry_start"] = {}
            item["can_start_web_run"] = bool(loop_id and loop)
            if loop_id and loop:
                try:
                    agent_entry_start = self.svc().agent_entry_loop_start_projection(loop_id)
                except LooporaError:
                    agent_entry_start = {}
                item["agent_entry_start"] = agent_entry_start
                item["can_start_web_run"] = not bool(agent_entry_start)
            items.append(item)
        return items

    def render_bundle_detail(  # noqa: PLR0913 - detail rerenders carry edit, action, and recovery feedback state.
        self,
        request: Request,
        bundle_id: str,
        *,
        values: Mapping[str, object] | None = None,
        form_error: str | None = None,
        action_error: str | None = None,
        action_recovery: Mapping[str, object] | None = None,
    ) -> HTMLResponse:
        bundle = self.svc().get_bundle(bundle_id)
        spec_path = Path(self.svc()._bundle_spec_path(bundle_id))
        spec_markdown = ""
        spec_read_error = None
        try:
            spec_markdown = spec_path.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError, UnicodeDecodeError) as exc:
            spec_read_error = _bundle_spec_read_error(exc)
            spec_markdown = _bundle_spec_markdown_from_loop_snapshot(self.svc(), bundle)
        bundle_yaml = self.svc().export_bundle_yaml(bundle_id)
        exported_bundle = self.svc().export_bundle(bundle_id)
        form_values = {
            "description": str(bundle.get("description", "")),
            "collaboration_summary": str(bundle.get("collaboration_summary", "")),
            "spec_markdown": spec_markdown,
        }
        if values:
            for key in form_values:
                if key in values:
                    form_values[key] = values[key]
        control_summary = self.svc()._bundle_control_summary(exported_bundle)
        governance_summary = self.svc()._bundle_governance_summary(exported_bundle)
        workflow_preview = self.svc()._bundle_workflow_preview(exported_bundle)
        traceability = control_summary.get("traceability") if isinstance(control_summary, dict) else {}
        traceability = traceability if isinstance(traceability, dict) else {}
        diagnostics = control_summary.get("diagnostics") if isinstance(control_summary, dict) else []
        traceability_items = [dict(item) for item in list(traceability.get("items") or []) if isinstance(item, dict)]
        diagnostic_warnings = [dict(item) for item in list(diagnostics or []) if isinstance(item, dict) and str(item.get("severity") or "").strip() != "info"]
        bundle_workdir = str(bundle.get("workdir") or "").strip()
        bundle_loop_id = str(bundle.get("loop_id") or "").strip()
        agent_entry_start = self.svc().agent_entry_loop_start_projection(bundle_loop_id) if bundle_loop_id else None
        bundle_surface_links = _bundle_owned_surface_links(bundle, workdir=bundle_workdir)
        bundle_replace_yaml_href = with_query_params(
            "/bundles#bundle-import-panel",
            replace_bundle_id=bundle_id,
            workdir=bundle_workdir or None,
        )
        return self.templates.TemplateResponse(
            request,
            "bundle_detail.html",
            {
                "request": request,
                "bundle": bundle,
                "form_values": form_values,
                "form_error": form_error or spec_read_error,
                "bundle_action_error": action_error or request.query_params.get("bundle_action_error") or None,
                "bundle_action_recovery": dict(action_recovery or {}),
                "bundle_yaml": bundle_yaml,
                "control_summary": control_summary,
                "bundle_governance_summary": governance_summary,
                "bundle_workflow_preview": workflow_preview,
                "bundle_traceability": traceability,
                "bundle_traceability_items": traceability_items,
                "bundle_diagnostic_warnings": diagnostic_warnings,
                "agent_entry_start": agent_entry_start,
                "bundle_orchestration_edit_href": bundle_surface_links["orchestration_edit_href"],
                "bundle_role_edit_hrefs": bundle_surface_links["role_edit_hrefs"],
                "bundle_replace_yaml_href": bundle_replace_yaml_href,
                "spec_rendered_html": render_safe_markdown_html(str(form_values.get("spec_markdown", ""))),
                "access_state": self.access_state,
            },
        )


def _bundle_spec_read_error(exc: BaseException) -> str:
    if isinstance(exc, FileNotFoundError):
        return "bundle spec file does not exist"
    return "bundle spec file could not be read"


def _bundle_spec_markdown_from_loop_snapshot(service: object, bundle: Mapping[str, object]) -> str:
    loop_id = str(bundle.get("loop_id") or "").strip()
    if not loop_id or not hasattr(service, "get_loop"):
        return ""
    try:
        loop = service.get_loop(loop_id)
    except LooporaError:
        return ""
    return str(loop.get("spec_markdown") or "")


def _bundle_list_item_workdir(item: Mapping[str, object], *, loop: Mapping[str, object] | None) -> str:
    bundle_workdir = str(item.get("workdir") or "").strip()
    if bundle_workdir:
        return bundle_workdir
    return str((loop or {}).get("workdir") or "").strip()


def _bundle_derive_loops(loops: list[dict], *, workdir_context: str) -> list[dict]:
    if not workdir_context:
        return loops
    return [loop for loop in loops if same_workdir_identity(loop.get("workdir"), workdir_context)]


def _bundle_list_items_for_workdir(items: list[dict], *, workdir_context: str) -> list[dict]:
    if not workdir_context:
        return items
    filtered_items: list[dict] = []
    for item in items:
        loop = item.get("loop") if isinstance(item.get("loop"), Mapping) else None
        if same_workdir_identity(_bundle_list_item_workdir(item, loop=loop), workdir_context):
            filtered_items.append(item)
    return filtered_items


def _bundle_owned_surface_links(bundle: Mapping[str, object], *, workdir: str) -> dict[str, object]:
    bundle_id = str(bundle.get("id") or "").strip()
    return_to = with_query_params(f"/bundles/{bundle_id}", workdir=workdir or None)
    orchestration = bundle.get("orchestration") if isinstance(bundle.get("orchestration"), Mapping) else {}
    orchestration_id = str(orchestration.get("id") or "").strip()
    role_edit_hrefs: dict[str, str] = {}
    for role_definition in list(bundle.get("role_definitions") or []):
        if not isinstance(role_definition, Mapping):
            continue
        role_definition_id = str(role_definition.get("id") or "").strip()
        if role_definition_id:
            role_edit_hrefs[role_definition_id] = with_query_params(
                f"/roles/{role_definition_id}/edit",
                workdir=workdir or None,
                return_to=return_to,
            )

    return {
        "orchestration_edit_href": with_query_params(
            f"/orchestrations/{orchestration_id}/edit",
            workdir=workdir or None,
            return_to=return_to,
        )
        if orchestration_id
        else "",
        "role_edit_hrefs": role_edit_hrefs,
    }
