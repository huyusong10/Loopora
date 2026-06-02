from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse

from loopora.service_types import LooporaConflictError
from loopora.web_route_context import WebRouteContext


def register_improvement_form_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/bundles/{bundle_id}/revise")
    async def create_bundle_improvement_from_form(request: Request, bundle_id: str):
        form = await request.form()
        message = str(form.get("message", "") or "")
        session = ctx.svc().create_bundle_revision_session(
            bundle_id,
            message=message,
            start_immediately=True,
        )
        return RedirectResponse(url=f"/loops/new/bundle?alignment_session_id={session['id']}", status_code=303)

    @app.post("/runs/{run_id}/revise")
    async def create_run_improvement_from_form(request: Request, run_id: str):
        form = await request.form()
        message = str(form.get("message", "") or "")
        session = ctx.svc().create_run_revision_session(
            run_id,
            message=message,
            start_immediately=True,
        )
        return RedirectResponse(url=f"/loops/new/bundle?alignment_session_id={session['id']}", status_code=303)

    @app.post("/runs/{run_id}/rerun")
    async def rerun_from_run_detail(run_id: str):
        run = ctx.svc().get_run(run_id)
        if run.get("status") not in {"succeeded", "failed", "stopped"}:
            raise LooporaConflictError(f"cannot rerun from active run in status {run.get('status')}")
        agent_entry_start = ctx.svc().agent_entry_loop_start_projection(run["loop_id"])
        if agent_entry_start:
            return JSONResponse(
                {
                    "error": "agent-first Loop runs must be restarted from /loopora-run in the host Agent",
                    "agent_entry_start": agent_entry_start,
                },
                status_code=409,
            )
        new_run = ctx.svc().rerun(run["loop_id"], background=True)
        return RedirectResponse(url=f"/runs/{new_run['id']}", status_code=303)

    @app.post("/runs/{run_id}/accept")
    async def accept_run_from_run_detail(run_id: str):
        ctx.svc().accept_run_result(run_id)
        return RedirectResponse(url=f"/runs/{run_id}", status_code=303)
