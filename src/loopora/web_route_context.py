from __future__ import annotations

from loopora.web_route_context_base import WebRouteContextBase
from loopora.web_route_context_loop_pages import WebRouteLoopPagesMixin

from collections.abc import Mapping

from pathlib import Path

from fastapi import Request

from fastapi.responses import HTMLResponse

from loopora.markdown_tools import render_safe_markdown_html

from loopora.web_inputs import (
    _normalize_bundle_derive_form,
    _normalize_bundle_import_form,
)


from urllib.parse import urlencode


from loopora.providers import list_executor_profiles

from loopora.web_role_inputs import (
    _archetype_options,
    _builtin_role_templates,
    _decorate_role_definition_overview,
    _normalize_role_definition_form,
    _role_definition_form_values_from_record,
)

from loopora.web_request_context import _preferred_request_locale

from loopora.web_route_context_loop_pages import safe_local_return_path


class WebRouteRolePagesMixin:
    def render_role_definitions(self, request: Request) -> HTMLResponse:
        role_definitions = [_decorate_role_definition_overview(role_definition) for role_definition in self.svc().list_role_definitions()]
        builtin_role_templates = [item for item in role_definitions if item["source"] == "builtin"]
        custom_role_definitions = [item for item in role_definitions if item["source"] == "custom"]
        return self.templates.TemplateResponse(
            request,
            "role_definitions.html",
            {
                "request": request,
                "role_definitions": role_definitions,
                "builtin_role_templates": builtin_role_templates,
                "custom_role_definitions": custom_role_definitions,
                "access_state": self.access_state,
            },
        )

    def render_new_role_definition(
        self,
        request: Request,
        *,
        values: Mapping[str, object] | None = None,
        form_error: str | None = None,
        role_definition: Mapping[str, object] | None = None,
    ) -> HTMLResponse:
        locale = _preferred_request_locale(request)
        return_to = safe_local_return_path(request.query_params.get("return_to", ""))
        incoming_values = values
        current_role_definition = dict(role_definition) if role_definition else None
        if values is None and current_role_definition is not None:
            values = _role_definition_form_values_from_record(current_role_definition, locale=locale)
        is_builtin_template = bool(current_role_definition and current_role_definition.get("source") == "builtin")
        is_editing_custom = bool(current_role_definition and current_role_definition.get("source") == "custom")
        role_template_locked = current_role_definition is not None
        if is_editing_custom:
            page_copy = {
                "title_zh": "修改这条角色定义，让后续编排都能复用新的版本。",
                "title_en": "Refine this role definition so future orchestrations can reuse it.",
                "body_zh": "这里改的是已经保存的角色定义。保存后，新的编排会继续引用它；已有编排里的角色快照不会被回写。",
                "body_en": "You are editing a saved role definition. Future orchestrations keep reusing it, while existing orchestrations keep their frozen role snapshots.",
                "submit_zh": "保存修改",
                "submit_en": "Save changes",
                "action": f"/roles/{current_role_definition['id']}/edit",
            }
        elif is_builtin_template:
            page_copy = {
                "title_zh": "从内置模板出发，打磨成你团队自己的角色版本。",
                "title_en": "Start from the built-in template, then tailor it into your team’s own role.",
                "body_zh": "这里保留的是模板的核心角色身份，你可以修改名字、执行工具、模型和提示词；保存时会派生出一条新的自定义角色定义。",
                "body_en": "The core role identity stays fixed here. Adjust the name, executor, model, and prompt, then save a new custom role definition derived from this template.",
                "submit_zh": "保存为新角色",
                "submit_en": "Save as new role",
                "action": "/roles/new",
            }
        else:
            page_copy = {
                "title_zh": "先把角色定义好，后面的编排就能直接拿来用。",
                "title_en": "Define the role once, then let orchestrations reuse it directly.",
                "body_zh": "角色定义保存的是角色名、角色模板、权限边界、默认执行工具、模型和提示词模板。编排里选中后，会把这些字段带进去作为角色快照。",
                "body_en": "A role definition stores the role name, role template, permission boundary, default executor, model, and prompt template. When an orchestration selects it, those values are copied in as a role snapshot.",
                "submit_zh": "保存角色",
                "submit_en": "Save role",
                "action": "/roles/new",
            }
        if return_to:
            page_copy["action"] = f"{page_copy['action']}?{urlencode({'return_to': return_to})}"
        form_values = _normalize_role_definition_form(values, locale=locale)
        archetype_options = _archetype_options()
        selected_archetype_option = next(
            (option for option in archetype_options if option["id"] == str(form_values.get("archetype", "builder"))),
            archetype_options[0],
        )
        builtin_prompt_sync_enabled = not is_editing_custom and (incoming_values is None or "prompt_markdown" not in incoming_values)
        return self.templates.TemplateResponse(
            request,
            "new_role_definition.html",
            {
                "request": request,
                "form_values": form_values,
                "form_error": form_error,
                "page_copy": page_copy,
                "current_role_definition": current_role_definition,
                "archetype_options": archetype_options,
                "selected_archetype_option": selected_archetype_option,
                "page_locale": locale,
                "role_template_locked": role_template_locked,
                "role_template_lock_reason": "builtin" if is_builtin_template else ("existing" if is_editing_custom else "new"),
                "executor_profiles": list_executor_profiles(),
                "builtin_role_templates": _builtin_role_templates(locale=locale),
                "builtin_prompt_sync_enabled": builtin_prompt_sync_enabled,
                "initial_prompt_preview_html": render_safe_markdown_html(
                    str(form_values.get("prompt_markdown", "")),
                    strip_front_matter=True,
                ),
                "access_state": self.access_state,
            },
        )


class WebRouteHelpPagesMixin:
    def render_tutorial(self, request: Request) -> HTMLResponse:
        orchestrations = self.svc().list_orchestrations()
        builtin_orchestrations = [dict(item) for item in orchestrations if item.get("source") == "builtin"]
        tutorial_order = {
            "quality_gate": 0,
            "evidence_first": 1,
            "benchmark_gate": 2,
        }
        builtin_orchestrations.sort(key=lambda item: tutorial_order.get(str(item.get("preset", "")), 99))
        tutorial_spec_practices: dict[str, dict[str, str]] = {}

        def tutorial_teaser(summary: str, *, locale: str) -> str:
            text = str(summary or "").strip()
            if locale == "zh" and text.startswith("场景："):
                return text.removeprefix("场景：").strip()
            if locale == "en" and text.lower().startswith("scenario:"):
                _, _, remainder = text.partition(":")
                return remainder.strip()
            return text

        for orchestration in builtin_orchestrations:
            summary_zh = str(orchestration.get("spec_practice_summary_zh", "")).strip()
            summary_en = str(orchestration.get("spec_practice_summary_en", "")).strip()
            markdown_zh = str(orchestration.get("spec_practice_markdown_zh", "")).strip()
            markdown_en = str(orchestration.get("spec_practice_markdown_en", "")).strip()
            orchestration["tutorial_teaser_zh"] = tutorial_teaser(summary_zh, locale="zh")
            orchestration["tutorial_teaser_en"] = tutorial_teaser(summary_en, locale="en")
            tutorial_spec_practices[str(orchestration.get("id", ""))] = {
                "name": str(orchestration.get("name", "")).strip(),
                "summary_zh": summary_zh,
                "summary_en": summary_en,
                "rendered_html_zh": render_safe_markdown_html(markdown_zh) if markdown_zh else "",
                "rendered_html_en": render_safe_markdown_html(markdown_en) if markdown_en else "",
            }
        return self.templates.TemplateResponse(
            request,
            "tutorial.html",
            {
                "request": request,
                "builtin_orchestrations": builtin_orchestrations,
                "tutorial_spec_practices": tutorial_spec_practices,
                "access_state": self.access_state,
            },
        )

    def render_tools(self, request: Request) -> HTMLResponse:
        return self.templates.TemplateResponse(
            request,
            "tools.html",
            {
                "request": request,
                "access_state": self.access_state,
            },
        )


class WebRouteBundlePagesMixin:
    def render_bundles(
        self,
        request: Request,
        *,
        import_values: Mapping[str, object] | None = None,
        import_error: str | None = None,
        derive_values: Mapping[str, object] | None = None,
        derive_error: str | None = None,
    ) -> HTMLResponse:
        loops = self.svc().list_loops()
        bundles = self.svc().list_bundle_exchange_items()
        scoped_workdir = str(request.query_params.get("workdir") or "").strip()
        if scoped_workdir:
            requested_workdir = Path(scoped_workdir).expanduser()
            if not requested_workdir.is_absolute():
                loops = []
                bundles = []
            else:
                requested_workdir = requested_workdir.resolve()
                loops = [loop for loop in loops if Path(str(loop.get("workdir") or "")).expanduser().resolve() == requested_workdir]
                visible_loop_ids = {str(loop.get("id") or "") for loop in loops}
                bundles = [bundle for bundle in bundles if str(bundle.get("loop_id") or "") in visible_loop_ids]
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
                "derive_error": derive_error,
                "access_state": self.access_state,
            },
        )

    def render_bundle_detail(
        self,
        request: Request,
        bundle_id: str,
        *,
        values: Mapping[str, object] | None = None,
        form_error: str | None = None,
    ) -> HTMLResponse:
        bundle = self.svc().get_bundle(bundle_id)
        spec_path = Path(self.svc()._bundle_spec_path(bundle_id))
        spec_markdown = ""
        spec_read_error = None
        if spec_path.exists():
            try:
                spec_markdown = spec_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                spec_read_error = f"bundle spec file could not be read: {exc}"
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
        traceability = control_summary.get("traceability") if isinstance(control_summary, dict) else {}
        traceability = traceability if isinstance(traceability, dict) else {}
        diagnostics = control_summary.get("diagnostics") if isinstance(control_summary, dict) else []
        traceability_items = [dict(item) for item in list(traceability.get("items") or []) if isinstance(item, dict)]
        diagnostic_warnings = [dict(item) for item in list(diagnostics or []) if isinstance(item, dict) and str(item.get("severity") or "").strip() != "info"]
        return self.templates.TemplateResponse(
            request,
            "bundle_detail.html",
            {
                "request": request,
                "bundle": bundle,
                "form_values": form_values,
                "form_error": form_error or spec_read_error,
                "bundle_yaml": bundle_yaml,
                "control_summary": control_summary,
                "bundle_traceability": traceability,
                "bundle_traceability_items": traceability_items,
                "bundle_diagnostic_warnings": diagnostic_warnings,
                "spec_rendered_html": render_safe_markdown_html(str(form_values.get("spec_markdown", ""))),
                "access_state": self.access_state,
            },
        )


class WebRouteContext(
    WebRouteBundlePagesMixin,
    WebRouteLoopPagesMixin,
    WebRouteRolePagesMixin,
    WebRouteHelpPagesMixin,
    WebRouteContextBase,
):
    """Aggregate page/rendering context for web route registration."""
