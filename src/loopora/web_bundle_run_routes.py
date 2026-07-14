from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response

from loopora.agent_entry_run_projection import AGENT_NATIVE_PLAN_FILE_WEB_START_ERROR
from loopora.service import LooporaError
from loopora.service_types import LooporaWorkdirUnavailableError
from loopora.web_run_dispatch import (
    is_background_worker_start_error,
    redirect_to_loop_start_error,
    redirect_to_run_action_error,
    start_run_async_error,
)
from loopora.web_route_context import WebRouteContext
from loopora.web_start_context import (
    request_resource_workdir_context_href,
    request_workdir_context,
    request_workdir_context_href,
    resource_workdir_context,
)
from loopora.web_workdir_recovery import browser_recovery_submit_payload, web_loop_start_workdir_recovery_payload


def register_bundle_run_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/bundles/{bundle_id}/runs")
    async def start_bundle_run_from_form(request: Request, bundle_id: str):
        return _start_bundle_run_from_form_response(ctx, request, bundle_id)


def bundle_import_run_dispatch_response(
    ctx: WebRouteContext,
    request: Request,
    loop_id: str,
    run: dict,
) -> RedirectResponse | None:
    dispatch_error = start_run_async_error(ctx.svc(), run)
    if dispatch_error is None:
        return None
    if is_background_worker_start_error(dispatch_error):
        return redirect_to_run_action_error(
            str(run["id"]),
            str(dispatch_error),
            workdir_context=resource_workdir_context(run, fallback=request_workdir_context(request)),
        )
    return redirect_to_loop_start_error(
        loop_id,
        str(dispatch_error),
        workdir_context=resource_workdir_context(run, fallback=request_workdir_context(request)),
    )


def _start_bundle_run_from_form_response(ctx: WebRouteContext, request: Request, bundle_id: str) -> Response:
    bundle = ctx.svc().get_bundle(bundle_id)
    loop_id = str(bundle.get("loop_id", "") or "").strip()
    loop = bundle.get("loop") if isinstance(bundle.get("loop"), dict) else None
    if not loop_id or not loop:
        return ctx.render_bundle_detail(request, bundle_id, action_error="plan file has no runnable Loop")
    agent_entry_start = ctx.svc().agent_entry_loop_start_projection(loop_id)
    if agent_entry_start:
        return ctx.render_bundle_detail(
            request,
            bundle_id,
            action_error=AGENT_NATIVE_PLAN_FILE_WEB_START_ERROR,
        )
    try:
        run = ctx.svc().start_run(loop_id)
    except LooporaWorkdirUnavailableError as exc:
        recovery = browser_recovery_submit_payload(
            web_loop_start_workdir_recovery_payload(loop_id, exc.workdir),
            form_id="bundle-start-run-form-fields",
            form_action=request_workdir_context_href(request, f"/bundles/{bundle_id}/runs"),
            action_kinds=("retry_web_run_start",),
        )
        return ctx.render_bundle_detail(
            request,
            bundle_id,
            action_error=str(recovery.get("error") or recovery.get("summary") or ""),
            action_recovery=recovery,
        )
    except LooporaError as exc:
        return ctx.render_bundle_detail(request, bundle_id, action_error=str(exc))
    return _started_bundle_run_form_response(ctx, request, bundle_id, run)


def _started_bundle_run_form_response(
    ctx: WebRouteContext,
    request: Request,
    bundle_id: str,
    run: dict,
) -> Response:
    dispatch_error = start_run_async_error(ctx.svc(), run)
    if dispatch_error is None:
        return RedirectResponse(url=request_resource_workdir_context_href(request, f"/runs/{run['id']}", run), status_code=303)
    if is_background_worker_start_error(dispatch_error):
        return redirect_to_run_action_error(
            str(run["id"]),
            str(dispatch_error),
            workdir_context=resource_workdir_context(run, fallback=request_workdir_context(request)),
        )
    return ctx.render_bundle_detail(request, bundle_id, action_error=str(dispatch_error))
