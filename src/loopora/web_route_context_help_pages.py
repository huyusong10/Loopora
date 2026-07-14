from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from urllib.parse import urlencode

from fastapi import Request
from fastapi.responses import HTMLResponse

from loopora import agent_adapter_command_prefix
from loopora.fit_guidance import fit_guidance_web_context
from loopora.markdown_tools import render_safe_markdown_html
from loopora.settings import app_home, load_recent_workdirs
from loopora.support_guidance import (
    public_support_payload,
    support_local_only_items,
    support_posting_guidance_text,
    support_public_paste_items,
    support_redaction_items,
    support_target_project_status_label,
)
from loopora.web_request_context import _preferred_request_locale
from loopora.web_start_context import request_workdir_context
from loopora.web_start_context import workdir_context_return_to
from loopora.web_url_utils import safe_local_return_path
from loopora.web_url_utils import with_query_params


def _agent_adapter_preference_scope() -> str:
    app_home_identity = str(app_home()).encode("utf-8")
    return f"app-home-sha256:{sha256(app_home_identity).hexdigest()}"


def _support_public_report_url(workdir: str, *, target_project_required: bool, language: str) -> str:
    if target_project_required or not workdir.strip():
        return ""
    return f"/api/diagnostics/public-issue-bundle?{urlencode({'workdir': workdir, 'language': language})}"


def _support_report_workdir_context(workdir: str) -> str:
    raw = str(workdir or "").strip()
    if not raw:
        return ""
    try:
        return raw if Path(raw).expanduser().is_absolute() else ""
    except (OSError, RuntimeError, ValueError):
        return ""


def _support_target_feedback(request: Request, *, support_workdir: str) -> str:
    feedback = str(request.query_params.get("support_target_feedback") or "").strip()
    if feedback in {"target_ready", "target_report_only", "target_required", "target_unavailable"}:
        return feedback
    explicit_workdir = str(
        request.query_params.get("workdir") or request.query_params.get("alignment_workdir") or ""
    ).strip()
    if explicit_workdir and not _support_report_workdir_context(explicit_workdir):
        return "target_unavailable"
    if str(support_workdir or "").strip() and not _support_report_workdir_context(support_workdir):
        return "target_unavailable"
    return ""


def _support_return_to(request: Request, *, workdir_context: str) -> str:
    return_to = safe_local_return_path(request.query_params.get("return_to", ""))
    if not return_to:
        return ""
    return workdir_context_return_to(return_to, workdir_context)


def _support_target_form_action(*, workdir_context: str, return_to: str) -> str:
    return with_query_params("/support", workdir=workdir_context or None, return_to=return_to or None)


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
        tutorial_workdir = request_workdir_context(request)
        return self.templates.TemplateResponse(
            request,
            "tutorial.html",
            {
                "request": request,
                "builtin_orchestrations": builtin_orchestrations,
                "tutorial_spec_practices": tutorial_spec_practices,
                "fit_guidance": fit_guidance_web_context(
                    cli_entry=agent_adapter_command_prefix.current_copyable_loopora_cli_entry(),
                    workdir=tutorial_workdir or None,
                ),
                "access_state": self.access_state,
            },
        )

    def _support_template_context(
        self,
        request: Request,
        *,
        support_panel_context: str,
        support_panel_open: bool = False,
    ) -> dict[str, object]:
        support_workdir = request_workdir_context(request)
        support_report_workdir = _support_report_workdir_context(support_workdir)
        support_return_to = _support_return_to(request, workdir_context=support_workdir)
        support_guidance = public_support_payload(
            workdir=support_report_workdir,
            web_host=str(self.access_state.get("bind_host") or ""),
            web_port=self.access_state.get("bind_port"),
        )
        target_project_required = bool(support_guidance.get("target_project_required"))
        return {
            "support_guidance": support_guidance,
            "support_posting_guidance_en": support_posting_guidance_text(support_guidance, language="en"),
            "support_posting_guidance_zh": support_posting_guidance_text(support_guidance, language="zh"),
            "support_public_paste_en": support_public_paste_items("en"),
            "support_public_paste_zh": support_public_paste_items("zh"),
            "support_local_only_en": support_local_only_items("en"),
            "support_local_only_zh": support_local_only_items("zh"),
            "support_redaction_en": support_redaction_items("en"),
            "support_redaction_zh": support_redaction_items("zh"),
            "support_target_status_en": support_target_project_status_label(
                str(support_guidance.get("target_project_status") or ""),
                language="en",
            ),
            "support_target_status_zh": support_target_project_status_label(
                str(support_guidance.get("target_project_status") or ""),
                language="zh",
            ),
            "support_panel_context": support_panel_context,
            "support_panel_open": support_panel_open,
            "support_public_report_url": _support_public_report_url(
                support_report_workdir,
                target_project_required=target_project_required,
                language=_preferred_request_locale(request),
            ),
            "support_target_feedback": _support_target_feedback(request, support_workdir=support_workdir),
            "support_return_to": support_return_to,
            "support_target_form_action": _support_target_form_action(
                workdir_context=support_workdir,
                return_to=support_return_to,
            ),
        }

    def render_tools(self, request: Request) -> HTMLResponse:
        return self.templates.TemplateResponse(
            request,
            "tools.html",
            {
                "request": request,
                "access_state": self.access_state,
                "agent_adapter_preference_scope": _agent_adapter_preference_scope(),
                "recent_workdirs": load_recent_workdirs(),
                **self._support_template_context(request, support_panel_context="tools"),
            },
        )

    def render_support(self, request: Request) -> HTMLResponse:
        return self.templates.TemplateResponse(
            request,
            "support.html",
            {
                "request": request,
                "access_state": self.access_state,
                "recent_workdirs": load_recent_workdirs(),
                **self._support_template_context(
                    request,
                    support_panel_context="support",
                    support_panel_open=True,
                ),
            },
        )
