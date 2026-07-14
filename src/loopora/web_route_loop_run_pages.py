from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from loopora.web_route_context import WebRouteContext


def register_loop_run_page_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/loops/{loop_id}", response_class=HTMLResponse)
    async def loop_detail(request: Request, loop_id: str) -> HTMLResponse:
        return ctx.render_loop_detail(request, loop_id)

    @app.get("/runs/{run_id}", response_class=HTMLResponse)
    async def run_detail(request: Request, run_id: str) -> HTMLResponse:
        return ctx.render_run_detail(request, run_id)

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
