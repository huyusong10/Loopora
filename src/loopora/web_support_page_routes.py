from __future__ import annotations

from urllib.parse import parse_qs, urlencode

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from loopora.settings import remember_recent_workdir
from loopora.web_route_context import WebRouteContext
from loopora.web_start_context import request_workdir_context
from loopora.web_start_context import safe_workdir_context
from loopora.web_start_context import workdir_context_href
from loopora.web_start_context import workdir_context_return_to
from loopora.web_url_utils import safe_local_return_path
from loopora.web_url_utils import with_query_params
from loopora.workdir_inputs import workdir_path_state


def register_support_page_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/same-agent", response_class=HTMLResponse)
    @app.get("/tools", response_class=HTMLResponse)
    async def tools_page(request: Request) -> HTMLResponse:
        return ctx.render_tools(request)

    @app.get("/support", response_class=HTMLResponse)
    async def support_page(request: Request) -> HTMLResponse:
        return ctx.render_support(request)

    @app.post("/support")
    async def support_target_page(request: Request) -> RedirectResponse:
        form = parse_qs((await request.body()).decode("utf-8", errors="replace"), keep_blank_values=True)
        workdir = str((form.get("workdir") or [""])[0] or "").strip()
        if not workdir:
            return RedirectResponse(
                url=f"/support?{urlencode({'support_target_feedback': 'target_required'})}#support-target-form",
                status_code=303,
            )
        if not safe_workdir_context(workdir):
            return RedirectResponse(
                url=f"/support?{urlencode({'support_target_feedback': 'target_unavailable'})}#support-target-form",
                status_code=303,
            )
        target_state = workdir_path_state(workdir)
        target_workdir = str(target_state.get("workdir") or "").strip()
        if not target_workdir:
            return RedirectResponse(
                url=f"/support?{urlencode({'support_target_feedback': 'target_unavailable'})}#support-target-form",
                status_code=303,
            )
        if target_state.get("status") == "ready":
            remember_recent_workdir(target_workdir)
            feedback = "target_ready"
        else:
            feedback = "target_report_only"
        return_to = _support_target_return_to(request, workdir_context=target_workdir)
        return RedirectResponse(
            url=_support_target_redirect_url(
                workdir=target_workdir,
                feedback=feedback,
                return_to=return_to,
            ),
            status_code=303,
        )

    @app.get("/fit-guide", response_class=HTMLResponse)
    @app.get("/tutorial", response_class=HTMLResponse)
    async def tutorial_page(request: Request) -> HTMLResponse:
        return ctx.render_tutorial(request)

    @app.get("/runs", response_class=HTMLResponse)
    async def runs_page(request: Request) -> RedirectResponse:
        return RedirectResponse(
            url=workdir_context_href("/#activity", request_workdir_context(request)),
            status_code=303,
        )


def _support_target_return_to(request: Request, *, workdir_context: str) -> str:
    return_to = safe_local_return_path(request.query_params.get("return_to", ""))
    if not return_to:
        return ""
    return workdir_context_return_to(return_to, workdir_context)


def _support_target_redirect_url(*, workdir: str, feedback: str, return_to: str = "") -> str:
    return with_query_params(
        "/support",
        workdir=workdir or None,
        support_target_feedback=feedback,
        return_to=return_to or None,
    )
