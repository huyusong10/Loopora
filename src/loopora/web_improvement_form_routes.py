from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from loopora.agent_entry_run_projection import AGENT_NATIVE_WEB_RERUN_ERROR
from loopora.service import LooporaError
from loopora.service_types import LooporaConflictError, LooporaWorkdirUnavailableError
from loopora.web_request_context import _request_wants_json
from loopora.web_revision_workdir import (
    browser_revision_session_creation_recovery_payload,
    bundle_revision_workdir_recovery_payload,
    is_revision_session_creation_recovery_error,
    revision_session_creation_recovery_payload,
    revision_source_workdir_context,
    run_revision_workdir_recovery_payload,
)
from loopora.web_route_context import WebRouteContext
from loopora.web_run_dispatch import web_run_start_failure_payload
from loopora.web_start_context import request_workdir_context_href
from loopora.web_start_context import request_resource_workdir_context_href
from loopora.web_start_context import resource_workdir_context_href
from loopora.web_url_utils import with_query_params
from loopora.web_workdir_recovery import web_loop_start_workdir_recovery_payload


def register_improvement_form_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    _register_bundle_improvement_form_routes(app, ctx)
    _register_run_improvement_form_routes(app, ctx)


def _register_bundle_improvement_form_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/bundles/{bundle_id}/revise")
    async def create_bundle_improvement_from_form(request: Request, bundle_id: str):
        form = await request.form()
        message = str(form.get("message", "") or "")
        try:
            recovery = bundle_revision_workdir_recovery_payload(ctx.svc(), bundle_id)
            if recovery:
                return _bundle_recovery_response(ctx, request, bundle_id, recovery)
            session = ctx.svc().create_bundle_revision_session(
                bundle_id,
                message=message,
                start_immediately=True,
            )
        except (LooporaError, OSError, UnicodeError) as exc:
            return _bundle_revision_creation_error_response(ctx, request, bundle_id, exc)
        return RedirectResponse(
            url=resource_workdir_context_href(f"/loops/new/bundle?alignment_session_id={session['id']}", session),
            status_code=303,
        )


def _register_run_improvement_form_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/runs/{run_id}/revise")
    async def create_run_improvement_from_form(request: Request, run_id: str):
        form = await request.form()
        message = str(form.get("message", "") or "")
        try:
            recovery = run_revision_workdir_recovery_payload(ctx.svc(), run_id)
            if recovery:
                return _run_recovery_response(ctx, request, run_id, recovery)
            session = ctx.svc().create_run_revision_session(
                run_id,
                message=message,
                start_immediately=True,
            )
        except (LooporaError, OSError, UnicodeError) as exc:
            return _run_revision_creation_error_response(ctx, request, run_id, exc)
        return RedirectResponse(
            url=resource_workdir_context_href(f"/loops/new/bundle?alignment_session_id={session['id']}", session),
            status_code=303,
        )

    @app.post("/runs/{run_id}/rerun")
    async def rerun_from_run_detail(request: Request, run_id: str):
        loop_id = ""
        form = await request.form()
        follow_up_kind = str(form.get("follow_up_kind", "") or "").strip()
        try:
            run = ctx.svc().get_run(run_id)
            loop_id = str(run.get("loop_id") or "")
            agent_entry_start = ctx.svc().agent_entry_loop_start_projection(loop_id)
            if agent_entry_start:
                return _run_agent_entry_start_error_response(request, run_id, agent_entry_start)
            new_run = ctx.svc().rerun_from_run(
                run_id,
                follow_up_kind=follow_up_kind,
                background=True,
            )
        except LooporaWorkdirUnavailableError as exc:
            return _run_start_workdir_error_response(ctx, request, run_id, loop_id, exc)
        except LooporaError as exc:
            return _run_action_error_response(request, run_id, exc)
        return _rerun_response(request, new_run)

    _register_run_result_recording_form_routes(app, ctx)


def _register_run_result_recording_form_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/runs/{run_id}/accept")
    async def accept_run_from_run_detail(request: Request, run_id: str):
        try:
            run = ctx.svc().get_run(run_id)
            ctx.svc().accept_run_result(run_id)
        except LooporaError as exc:
            return _run_action_error_response(request, run_id, exc)
        return RedirectResponse(url=request_resource_workdir_context_href(request, f"/runs/{run_id}", run), status_code=303)

    @app.post("/runs/{run_id}/reopen-result")
    async def reopen_run_result_from_run_detail(request: Request, run_id: str):
        try:
            run = ctx.svc().get_run(run_id)
            ctx.svc().reopen_run_result_acceptance(run_id)
        except LooporaError as exc:
            return _run_action_error_response(request, run_id, exc)
        return RedirectResponse(url=request_resource_workdir_context_href(request, f"/runs/{run_id}", run), status_code=303)


def _run_action_error_response(request: Request, run_id: str, exc: LooporaError) -> Response:
    if _request_wants_json(request):
        return JSONResponse(
            {"error": str(exc)},
            status_code=int(getattr(exc, "status_code", 400) or 400),
        )
    return _redirect_to_run_with_action_error(request, run_id, str(exc))


def _bundle_revision_creation_error_response(
    ctx: WebRouteContext,
    request: Request,
    bundle_id: str,
    exc: BaseException,
) -> Response:
    if is_revision_session_creation_recovery_error(exc):
        if not _request_wants_json(request):
            return _bundle_recovery_response(
                ctx,
                request,
                bundle_id,
                browser_revision_session_creation_recovery_payload(
                    "bundle",
                    bundle_id,
                    exc,
                    retry_url=request_workdir_context_href(request, f"/bundles/{bundle_id}/revise"),
                    workdir_context=revision_source_workdir_context(ctx.svc(), "bundle", bundle_id),
                ),
            )
        return _bundle_recovery_response(
            ctx,
            request,
            bundle_id,
            revision_session_creation_recovery_payload(
                "bundle",
                bundle_id,
                exc,
                workdir_context=revision_source_workdir_context(ctx.svc(), "bundle", bundle_id),
            ),
        )
    return _redirect_to_bundle_with_action_error(request, bundle_id, str(exc))


def _run_revision_creation_error_response(
    ctx: WebRouteContext,
    request: Request,
    run_id: str,
    exc: BaseException,
) -> Response:
    if is_revision_session_creation_recovery_error(exc):
        if not _request_wants_json(request):
            return _run_recovery_response(
                ctx,
                request,
                run_id,
                browser_revision_session_creation_recovery_payload(
                    "run",
                    run_id,
                    exc,
                    retry_url=request_workdir_context_href(request, f"/runs/{run_id}/revise"),
                    workdir_context=revision_source_workdir_context(ctx.svc(), "run", run_id),
                ),
            )
        return _run_recovery_response(
            ctx,
            request,
            run_id,
            revision_session_creation_recovery_payload(
                "run",
                run_id,
                exc,
                workdir_context=revision_source_workdir_context(ctx.svc(), "run", run_id),
            ),
        )
    if isinstance(exc, LooporaError):
        return _run_action_error_response(request, run_id, exc)
    return _redirect_to_run_with_action_error(request, run_id, str(exc))


def _rerun_response(request: Request, run: dict) -> Response:
    run_start_error = str(run.get("run_start_error") or "").strip()
    if run_start_error:
        redirect_url = with_query_params(
            request_resource_workdir_context_href(request, f"/runs/{run['id']}", run),
            run_action_error=run_start_error,
        )
        if _request_wants_json(request):
            return JSONResponse(
                web_run_start_failure_payload(run, redirect_url=redirect_url, action="rerun"),
                status_code=503,
            )
        return RedirectResponse(url=redirect_url, status_code=303)
    return RedirectResponse(url=request_resource_workdir_context_href(request, f"/runs/{run['id']}", run), status_code=303)


def _run_agent_entry_start_error_response(request: Request, run_id: str, agent_entry_start: dict) -> Response:
    error = AGENT_NATIVE_WEB_RERUN_ERROR
    if _request_wants_json(request):
        return JSONResponse(
            {
                "error": error,
                "agent_entry_start": agent_entry_start,
            },
            status_code=LooporaConflictError.status_code,
        )
    return _redirect_to_run_with_action_error(request, run_id, error)


def _bundle_recovery_response(
    ctx: WebRouteContext,
    request: Request,
    bundle_id: str,
    recovery: dict[str, object],
) -> Response:
    if _request_wants_json(request):
        return JSONResponse(recovery, status_code=400)
    return ctx.render_bundle_detail(
        request,
        bundle_id,
        action_error=_recovery_error_text(recovery),
        action_recovery=recovery,
    )


def _run_recovery_response(
    ctx: WebRouteContext,
    request: Request,
    run_id: str,
    recovery: dict[str, object],
) -> Response:
    if _request_wants_json(request):
        return JSONResponse(recovery, status_code=400)
    return ctx.render_run_detail(
        request,
        run_id,
        run_action_error=_recovery_error_text(recovery),
        run_action_recovery=recovery,
    )


def _run_start_workdir_error_response(
    ctx: WebRouteContext,
    request: Request,
    run_id: str,
    loop_id: str,
    exc: LooporaWorkdirUnavailableError,
) -> Response:
    recovery = web_loop_start_workdir_recovery_payload(loop_id, exc.workdir, action="rerun")
    return _run_recovery_response(ctx, request, run_id, recovery)


def _recovery_error_text(recovery: dict[str, object]) -> str:
    return str(recovery.get("error") or recovery.get("summary") or "")


def _redirect_to_run_with_action_error(request: Request, run_id: str, error: str) -> RedirectResponse:
    return RedirectResponse(
        url=with_query_params(request_workdir_context_href(request, f"/runs/{run_id}"), run_action_error=error),
        status_code=303,
    )


def _redirect_to_bundle_with_action_error(request: Request, bundle_id: str, error: str) -> RedirectResponse:
    return RedirectResponse(
        url=with_query_params(
            request_workdir_context_href(request, f"/bundles/{bundle_id}"),
            bundle_action_error=error,
        ),
        status_code=303,
    )
