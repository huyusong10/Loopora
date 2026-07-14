from __future__ import annotations

from collections.abc import Mapping

from fastapi import Request
from fastapi.responses import HTMLResponse

from loopora.markdown_tools import render_safe_markdown_html
from loopora.service import LooporaError
from loopora.specs import render_spec_template_for_strategy_source
from loopora.strategy_source import (
    StrategySourceError,
    available_strategy_prompt_templates,
    build_preset_strategy_source,
    resolve_strategy_prompt_files,
    strategy_source_preset_copy,
    strategy_source_preset_names,
)
from loopora.web_asset_validation_recovery import web_asset_field_error_ids
from loopora.web_asset_validation_recovery import web_asset_field_error_views
from loopora.web_request_context import _preferred_request_locale
from loopora.web_strategy_inputs import (
    _normalize_orchestration_form,
    _orchestration_form_values_from_record,
    _strategy_source_for_spec_template,
)
from loopora.web_start_context import request_workdir_context
from loopora.web_start_context import workdir_context_return_to
from loopora.web_url_utils import safe_local_return_path
from loopora.web_url_utils import with_query_params


class WebRouteOrchestrationPagesMixin:
    def render_orchestrations(self, request: Request) -> HTMLResponse:
        workdir_context = request_workdir_context(request)
        return_to = workdir_context_return_to(
            safe_local_return_path(request.query_params.get("return_to", "")),
            workdir_context,
        )

        def orchestration_href(orchestration_id: str) -> str:
            return with_query_params(
                f"/orchestrations/{orchestration_id}/edit",
                workdir=workdir_context or None,
                return_to=return_to or None,
            )

        orchestrations = [
            {
                **item,
                "editor_href": orchestration_href(str(item.get("id", ""))),
            }
            for item in self.svc().list_orchestrations()
        ]
        custom_orchestrations = [item for item in orchestrations if item.get("source") == "custom"]
        builtin_orchestrations = [item for item in orchestrations if item.get("source") == "builtin"]
        return self.templates.TemplateResponse(
            request,
            "orchestrations.html",
            {
                "request": request,
                "orchestrations": orchestrations,
                "custom_orchestrations": custom_orchestrations,
                "builtin_orchestrations": builtin_orchestrations,
                "create_orchestration_href": with_query_params(
                    "/orchestrations/new",
                    workdir=workdir_context or None,
                    return_to=return_to or None,
                ),
                "access_state": self.access_state,
            },
        )

    def render_new_orchestration(
        self,
        request: Request,
        *,
        values: Mapping[str, object] | None = None,
        form_error: str | None = None,
        form_field_errors: list[Mapping[str, object]] | None = None,
        orchestration: Mapping[str, object] | None = None,
    ) -> HTMLResponse:
        page_locale = _preferred_request_locale(request)
        workdir_context = request_workdir_context(request)
        return_to = workdir_context_return_to(
            safe_local_return_path(request.query_params.get("return_to", "")),
            workdir_context,
        )
        current_orchestration = dict(orchestration) if orchestration else None
        if values is None and current_orchestration is not None:
            values = _orchestration_form_values_from_record(current_orchestration)
        is_builtin_template = bool(current_orchestration and current_orchestration.get("source") == "builtin")
        is_editing_custom = bool(current_orchestration and current_orchestration.get("source") == "custom")
        if is_builtin_template and current_orchestration is not None:
            form_values = _normalize_orchestration_form(_orchestration_form_values_from_record(current_orchestration))
        else:
            form_values = _normalize_orchestration_form(values)
        if is_editing_custom:
            page_copy = {
                "title_zh": "修改编排，让后续 Loop 继续沿着新的流程走。",
                "title_en": "Refine this orchestration before future loops use the new flow.",
                "body_zh": "这里改的是已经保存的流程编排。你可以调整角色定义的引用关系、步骤顺序和收束规则；角色提示词和执行方式请回到“角色定义”页修改。",
                "body_en": "You are editing a saved orchestration. Adjust role-definition snapshots, step order, and completion rules here; return to Role Definitions to change prompts or execution settings.",
                "submit_zh": "保存修改",
                "submit_en": "Save changes",
                "action": f"/orchestrations/{current_orchestration['id']}/edit",
            }
        elif is_builtin_template:
            page_copy = {
                "title_zh": "查看默认编排，先理解 Loopora 推荐的 Loop 结构。",
                "title_en": "Inspect the built-in orchestration to understand Loopora's recommended loop shape.",
                "body_zh": "默认编排是固定的，只用于查看和直接复用，不能在这里修改。若要做自己的版本，请新建一条自定义编排，再按需要调整角色快照、步骤顺序和收束规则。",
                "body_en": "Built-in orchestrations are fixed. You can inspect and reuse them directly here, but not modify them. To make your own version, create a custom orchestration and then adjust role snapshots, step order, and completion rules there.",
                "submit_zh": "新建自定义编排",
                "submit_en": "Create custom orchestration",
                "action": "/orchestrations/new",
            }
        else:
            page_copy = {
                "title_zh": "先把步骤编排搭起来，再让 Loop 去执行。",
                "title_en": "Shape the step workbench first, then let loops execute it.",
                "body_zh": "这里默认从空白编排开始。你可以在步骤工具条里载入起手模板、按角色定义添加步骤、重排步骤和检查 Loop 实例图；角色提示词与执行配置继续在“角色定义”页维护。",
                "body_en": "This editor starts blank by default. Use the step toolbar to load a starter template, add steps from role definitions, reorder steps, and inspect the loop map. Prompts and execution settings still live in Role Definitions.",
                "submit_zh": "保存编排",
                "submit_en": "Save orchestration",
                "action": "/orchestrations/new",
            }
        page_copy["action"] = with_query_params(
            page_copy["action"],
            workdir=workdir_context or None,
            return_to=return_to or None,
        )
        orchestration_api_path = f"/api/orchestrations/{current_orchestration['id']}" if is_editing_custom and current_orchestration else "/api/orchestrations"
        orchestration_api_action = with_query_params(
            orchestration_api_path,
            workdir=workdir_context or None,
        )
        orchestration_api_method = "PUT" if is_editing_custom else "POST"
        try:
            spec_template_strategy_source = _strategy_source_for_spec_template(form_values)
        except (LooporaError, StrategySourceError, ValueError):
            spec_template_strategy_source = None
        generated_spec_template = render_spec_template_for_strategy_source(
            locale=page_locale,
            strategy_source=spec_template_strategy_source,
        )
        spec_practice_markdown = ""
        spec_practice_summary = ""
        spec_practice_markdown_zh = ""
        spec_practice_markdown_en = ""
        spec_practice_summary_zh = ""
        spec_practice_summary_en = ""
        if current_orchestration and current_orchestration.get("source") == "builtin":
            spec_practice_markdown_zh = str(current_orchestration.get("spec_practice_markdown_zh", ""))
            spec_practice_markdown_en = str(current_orchestration.get("spec_practice_markdown_en", ""))
            spec_practice_summary_zh = str(current_orchestration.get("spec_practice_summary_zh", ""))
            spec_practice_summary_en = str(current_orchestration.get("spec_practice_summary_en", ""))
            spec_practice_markdown = spec_practice_markdown_zh if page_locale == "zh" else spec_practice_markdown_en
            spec_practice_summary = spec_practice_summary_zh if page_locale == "zh" else spec_practice_summary_en
        workflow_preset_option_names = list(strategy_source_preset_names())
        selected_workflow_preset = str(form_values.get("workflow_preset", "")).strip()
        if (
            selected_workflow_preset
            and selected_workflow_preset not in workflow_preset_option_names
            and selected_workflow_preset in strategy_source_preset_names(include_hidden=True)
        ):
            workflow_preset_option_names.append(selected_workflow_preset)
        workflow_preset_option_values = [strategy_source_preset_copy(preset_name) for preset_name in workflow_preset_option_names]
        field_errors = web_asset_field_error_views(
            form_field_errors,
            field_labels=_orchestration_field_labels(page_locale),
            id_prefix="orchestration-field-recovery",
        )
        return self.templates.TemplateResponse(
            request,
            "new_orchestration.html",
            {
                "request": request,
                "form_values": form_values,
                "form_error": form_error,
                "form_field_errors": field_errors,
                "form_field_error_fields": {str(item.get("field", "")) for item in field_errors},
                "form_field_error_ids": web_asset_field_error_ids(field_errors),
                "workflow_preset_options": [
                    {
                        "id": preset_name,
                        **copy,
                    }
                    for preset_name, copy in zip(workflow_preset_option_names, workflow_preset_option_values, strict=False)
                ],
                "workflow_preset_bundles": {
                    preset_name: {
                        "copy": copy,
                        "workflow": build_preset_strategy_source(preset_name),
                        "prompt_files": resolve_strategy_prompt_files(build_preset_strategy_source(preset_name)),
                    }
                    for preset_name, copy in zip(workflow_preset_option_names, workflow_preset_option_values, strict=False)
                },
                "prompt_templates": available_strategy_prompt_templates(),
                "role_definitions": self.svc().list_role_definitions(),
                "page_copy": page_copy,
                "orchestration_api_action": orchestration_api_action,
                "orchestration_api_method": orchestration_api_method,
                "return_to": return_to,
                "current_orchestration": current_orchestration,
                "orchestrations_href": with_query_params(
                    "/orchestrations",
                    workdir=workdir_context or None,
                    return_to=return_to or None,
                ),
                "cancel_href": return_to
                or with_query_params(
                    "/orchestrations",
                    workdir=workdir_context or None,
                ),
                "role_definitions_href": with_query_params(
                    "/roles",
                    workdir=workdir_context or None,
                    return_to=return_to or None,
                ),
                "generated_spec_template_rendered_html": render_safe_markdown_html(generated_spec_template),
                "spec_practice_summary": spec_practice_summary,
                "spec_practice_markdown": spec_practice_markdown,
                "spec_practice_summary_zh": spec_practice_summary_zh,
                "spec_practice_summary_en": spec_practice_summary_en,
                "spec_practice_markdown_zh": spec_practice_markdown_zh,
                "spec_practice_markdown_en": spec_practice_markdown_en,
                "spec_practice_rendered_html": render_safe_markdown_html(spec_practice_markdown) if spec_practice_markdown else "",
                "spec_practice_rendered_html_zh": render_safe_markdown_html(spec_practice_markdown_zh) if spec_practice_markdown_zh else "",
                "spec_practice_rendered_html_en": render_safe_markdown_html(spec_practice_markdown_en) if spec_practice_markdown_en else "",
                "orchestration_locked": is_builtin_template,
                "orchestration_create_from_preset_href": (
                    with_query_params(
                        "/orchestrations/new",
                        workflow_preset=form_values.get("workflow_preset", "quality_gate"),
                        workdir=workdir_context or None,
                        return_to=return_to or None,
                    )
                    if is_builtin_template
                    else ""
                ),
                "access_state": self.access_state,
            },
        )


def _orchestration_field_labels(locale: str) -> dict[str, str]:
    if locale == "zh":
        return {
            "name": "名称",
            "strategy_json": "流程结构",
            "workflow_json": "流程结构",
            "prompt_files_json": "提示词文件",
            "workflow_preset": "起手模板",
        }
    return {
        "name": "Name",
        "strategy_json": "Flow structure",
        "workflow_json": "Flow structure",
        "prompt_files_json": "Prompt files",
        "workflow_preset": "Starter",
    }
