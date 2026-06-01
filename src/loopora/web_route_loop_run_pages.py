from __future__ import annotations

from urllib.parse import urlencode

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from loopora.markdown_tools import render_safe_markdown_html
from loopora.web_overviews import (
    _build_run_summary_snapshot,
    _decorate_run_overview,
    _overview_strategy_source,
    _strategy_role_executor_summary,
)
from loopora.web_route_context import WebRouteContext
from loopora.web_request_context import _preferred_request_locale


def register_loop_run_page_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/loops/{loop_id}", response_class=HTMLResponse)
    async def loop_detail(request: Request, loop_id: str) -> HTMLResponse:
        loop = ctx.svc().get_loop(loop_id)
        runs = [_decorate_run_overview(run) for run in loop["runs"]]
        latest_run = runs[0] if runs else None
        agent_entry_start = ctx.svc().agent_entry_loop_start_projection(loop_id)
        return ctx.templates.TemplateResponse(
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
                "agent_entry_start": agent_entry_start,
                "access_state": ctx.access_state,
            },
        )

    @app.get("/runs/{run_id}", response_class=HTMLResponse)
    async def run_detail(request: Request, run_id: str) -> HTMLResponse:
        locale = _preferred_request_locale(request)
        run = ctx.svc().get_run(run_id)
        web_projection = ctx.svc().app_services.projection.web_run_detail(run)
        export_bundle_url = f"/bundles/derive/export?{urlencode({'loop_id': run['loop_id']})}"
        agent_entry_start = ctx.svc().agent_entry_loop_start_projection(run["loop_id"])
        return ctx.templates.TemplateResponse(
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
                "acceptance_state": ctx.svc().run_result_acceptance_state(run_id),
                "access_state": ctx.access_state,
            },
        )

    @app.get("/runs/{run_id}/console", response_class=HTMLResponse)
    async def run_console(request: Request, run_id: str) -> HTMLResponse:
        run = ctx.svc().get_run(run_id)
        seed_events = ctx.svc().stream_events(run_id, limit=5000)
        latest_event_id = seed_events[-1]["id"] if seed_events else 0
        return ctx.templates.TemplateResponse(
            request,
            "run_console.html",
            {
                "request": request,
                "run": run,
                "console_events": seed_events[-360:],
                "latest_event_id": latest_event_id,
                "access_state": ctx.access_state,
            },
        )
