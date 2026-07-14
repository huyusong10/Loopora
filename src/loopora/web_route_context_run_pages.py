from __future__ import annotations

from collections.abc import Mapping

from fastapi import Request
from fastapi.responses import HTMLResponse

from loopora.markdown_tools import render_safe_markdown_html
from loopora.run_result_recording import RUN_RESULT_LIFECYCLE_FAILURE_BLOCKED_REASON
from loopora.run_result_recording import run_result_is_lifecycle_failure
from loopora.run_worker_start import BACKGROUND_WORKER_START_ERROR
from loopora.web_overviews import (
    _build_run_summary_snapshot,
    _decorate_run_overview,
    _overview_strategy_source,
    _strategy_role_executor_summary,
)
from loopora.web_request_context import _preferred_request_locale
from loopora.web_run_dispatch import web_run_start_failure_payload
from loopora.web_task_verdict_overviews import terminal_task_verdict_needs_evidence
from loopora.web_url_utils import with_query_params


class WebRouteRunPagesMixin:
    def render_loop_detail(
        self,
        request: Request,
        loop_id: str,
        *,
        run_start_error: str | None = None,
        run_start_recovery: Mapping[str, object] | None = None,
    ) -> HTMLResponse:
        loop = self.svc().get_loop(loop_id)
        runs = [_decorate_run_overview(run) for run in loop["runs"]]
        latest_run = runs[0] if runs else None
        agent_entry_start = self.svc().agent_entry_loop_start_projection(loop_id)
        latest_run_acceptance_state = (
            self.svc().run_result_acceptance_state(str(latest_run.get("id") or "")) if latest_run else {}
        )
        latest_run_result_recordable = latest_run_acceptance_state.get("recordable", True)
        latest_run_recording_blocked_reason = str(
            latest_run_acceptance_state.get("recording_blocked_reason") or ""
        ).strip()
        latest_run_needs_evidence = terminal_task_verdict_needs_evidence(
            latest_run.get("status") if latest_run else "",
            latest_run.get("task_verdict_status") if latest_run else "",
        )
        latest_run_needs_recovery = bool(
            latest_run
            and latest_run.get("status") in {"succeeded", "failed", "stopped"}
            and not latest_run_acceptance_state.get("accepted")
            and latest_run_result_recordable is False
            and latest_run_recording_blocked_reason == RUN_RESULT_LIFECYCLE_FAILURE_BLOCKED_REASON
        )
        return self.templates.TemplateResponse(
            request,
            "loop_detail.html",
            {
                "request": request,
                "loop": {
                    **loop,
                    "runs": runs,
                    "role_executor_summary": _strategy_role_executor_summary(
                        _overview_strategy_source(loop),
                        fallback_executor_kind=loop.get("executor_kind", "codex"),
                    ),
                    "spec_rendered_html": render_safe_markdown_html(loop.get("spec_markdown", "")),
                },
                "latest_run": latest_run,
                "summary_snapshot": _build_run_summary_snapshot(latest_run) if latest_run else None,
                "latest_run_acceptance_state": latest_run_acceptance_state,
                "latest_run_needs_evidence": latest_run_needs_evidence
                and not latest_run_acceptance_state.get("accepted")
                and not latest_run_needs_recovery,
                "latest_run_needs_recovery": latest_run_needs_recovery,
                "agent_entry_start": agent_entry_start,
                "run_start_error": run_start_error or request.query_params.get("run_start_error") or None,
                "run_start_recovery": dict(run_start_recovery or {}),
                "page_locale": _preferred_request_locale(request),
                "access_state": self.access_state,
            },
        )

    def render_run_detail(
        self,
        request: Request,
        run_id: str,
        *,
        run_action_error: str | None = None,
        run_action_recovery: Mapping[str, object] | None = None,
    ) -> HTMLResponse:
        locale = _preferred_request_locale(request)
        run = self.svc().get_run(run_id)
        web_projection = self.svc().app_services.projection.web_run_detail(run)
        export_bundle_url = with_query_params(
            "/bundles/derive/export",
            loop_id=run["loop_id"],
            workdir=str(run.get("workdir") or "").strip() or None,
        )
        agent_entry_start = self.svc().agent_entry_loop_start_projection(run["loop_id"])
        resolved_run_action_error = run_action_error or request.query_params.get("run_action_error") or None
        resolved_run_action_recovery = dict(run_action_recovery or {})
        if not resolved_run_action_recovery:
            resolved_run_action_recovery = _run_action_recovery_from_query(run, resolved_run_action_error)
        return self.templates.TemplateResponse(
            request,
            "run_detail.html",
            {
                "request": request,
                "run": run,
                "web_projection": web_projection,
                "export_bundle_url": export_bundle_url,
                "page_locale": locale,
                "progress_stages": web_projection["progress_stages"],
                "agent_entry_start": agent_entry_start,
                "acceptance_state": self.svc().run_result_acceptance_state(run_id),
                "continuation_state": self.svc().run_continuation_state(run_id),
                "continuation_outcome": self.svc().run_continuation_outcome(run_id),
                "run_result_lifecycle_failure_blocked_reason": RUN_RESULT_LIFECYCLE_FAILURE_BLOCKED_REASON,
                "run_action_error": resolved_run_action_error,
                "run_action_recovery": resolved_run_action_recovery,
                "access_state": self.access_state,
            },
        )


def _run_action_recovery_from_query(run: Mapping[str, object], error: str | None) -> dict[str, object]:
    if error != BACKGROUND_WORKER_START_ERROR or not run_result_is_lifecycle_failure(run):
        return {}
    return web_run_start_failure_payload(run, action="start_run", include_error=True)
