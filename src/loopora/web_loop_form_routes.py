from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from loopora.service import LooporaError
from loopora.specs import SpecError
from loopora.web_loop_inputs import (
    _loop_payload_from_mapping,
    _normalize_loop_form,
)
from loopora.web_route_context import WebRouteContext


def register_loop_form_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/loops/new/manual")
    @app.post("/loops/new")
    async def create_loop_from_form(request: Request):
        form = await request.form()
        values = _normalize_loop_form(form)
        try:
            loop_kwargs, start_immediately = _loop_payload_from_mapping(form)
            loop = ctx.svc().create_loop(**loop_kwargs)
            if start_immediately:
                run = ctx.svc().start_run(loop["id"])
                ctx.svc().start_run_async(run["id"])
                return RedirectResponse(url=f"/runs/{run['id']}", status_code=303)
            return RedirectResponse(url=f"/loops/{loop['id']}", status_code=303)
        except (LooporaError, SpecError, FileExistsError, OSError, ValueError) as exc:
            return ctx.render_new_loop(request, page_mode="manual", values=values, form_error=str(exc))
