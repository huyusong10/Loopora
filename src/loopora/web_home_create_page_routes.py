from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from loopora.web_home_attention import home_loop_sections
from loopora.web_page_query_redirects import clean_create_query_redirect
from loopora.web_page_query_redirects import new_loop_bundle_redirect
from loopora.web_page_query_redirects import new_loop_redirect
from loopora.web_route_context import WebRouteContext
from loopora.web_start_context import request_all_projects_scope_href
from loopora.web_start_context import request_workdir_context
from loopora.web_url_utils import with_query_params


def register_home_create_page_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        service = ctx.svc()
        workdir_context = request_workdir_context(request)
        loop_sections = home_loop_sections(service, workdir_context=workdir_context)
        all_loop_sections = home_loop_sections(service) if workdir_context else loop_sections
        scoped_activity_count = len(loop_sections["active_loops"]) + len(loop_sections["recent_loops"])
        all_activity_count = len(all_loop_sections["active_loops"]) + len(all_loop_sections["recent_loops"])
        return ctx.templates.TemplateResponse(
            request,
            "index.html",
            {
                "request": request,
                **loop_sections,
                "all_loop_count": len(all_loop_sections["loops"]),
                "hidden_loop_count": max(0, len(all_loop_sections["loops"]) - len(loop_sections["loops"])),
                "all_activity_count": all_activity_count,
                "hidden_activity_count": max(0, all_activity_count - scoped_activity_count),
                "home_all_href": request_all_projects_scope_href(request, "/"),
                "home_web_conversation_href": with_query_params(
                    "/loops/new/bundle",
                    alignment_workdir=workdir_context or None,
                ),
                "access_state": ctx.access_state,
            },
        )

    @app.get("/loops/new", response_class=HTMLResponse)
    async def new_loop(request: Request) -> HTMLResponse:
        if redirect := new_loop_redirect(request):
            return redirect
        return ctx.render_new_loop(
            request,
            page_mode="choice",
        )

    @app.get("/loops/new/bundle", response_class=HTMLResponse)
    async def new_loop_bundle(request: Request) -> HTMLResponse:
        if redirect := new_loop_bundle_redirect(request):
            return redirect
        return ctx.render_new_loop(
            request,
            page_mode="bundle",
        )

    @app.get("/loops/new/manual", response_class=HTMLResponse)
    async def new_loop_manual(request: Request) -> HTMLResponse:
        if redirect := clean_create_query_redirect(request):
            return redirect
        return ctx.render_new_loop(
            request,
            page_mode="manual",
            values=request.query_params,
            import_values=request.query_params or None,
        )
