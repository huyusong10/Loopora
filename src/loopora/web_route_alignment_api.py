from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

from loopora.service_types import LooporaError, LooporaWorkdirUnavailableError
from loopora.web_alignment_import_recovery import (
    alignment_bundle_preview_recovery_payload,
    alignment_bundle_sync_recovery_payload,
    alignment_import_recovery_payload,
    is_alignment_import_recovery_error,
)
from loopora.web_alignment_event_api import register_alignment_event_api_routes
from loopora.web_alignment_session_recovery import (
    alignment_session_creation_recovery_payload,
    is_alignment_session_creation_recovery_error,
)
from loopora.web_common_inputs import _coerce_bool
from loopora.web_revision_workdir import (
    bundle_revision_workdir_recovery_payload,
    is_revision_session_creation_recovery_error,
    revision_session_creation_recovery_payload,
    revision_source_workdir_context,
    run_revision_workdir_recovery_payload,
)
from loopora.web_route_context import WebRouteContext
from loopora.web_run_dispatch import web_run_start_failure_payload
from loopora.web_start_context import resource_workdir_context_href
from loopora.web_url_utils import with_query_params
from loopora.web_workdir_recovery import web_alignment_workdir_ready, web_alignment_workdir_recovery_payload


def register_alignment_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    _register_alignment_improvement_routes(app, ctx)
    _register_alignment_workdir_context_route(app, ctx)
    _register_alignment_session_routes(app, ctx)
    register_alignment_event_api_routes(app, ctx)
    _register_alignment_bundle_routes(app, ctx)


def _register_alignment_improvement_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/api/bundles/{bundle_id}/revise")
    async def api_create_bundle_improvement_session(bundle_id: str, request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        recovery = bundle_revision_workdir_recovery_payload(ctx.svc(), bundle_id)
        if recovery:
            return JSONResponse(recovery, status_code=400)
        try:
            session = ctx.svc().create_bundle_revision_session(bundle_id, **_alignment_executor_payload(payload))
        except (LooporaError, OSError, UnicodeError) as exc:
            return _api_revision_creation_error_response(ctx, "bundle", bundle_id, exc)
        return JSONResponse(
            {
                "session": session,
                "redirect_url": resource_workdir_context_href(
                    f"/loops/new/bundle?alignment_session_id={session['id']}",
                    session,
                ),
            },
            status_code=201,
        )

    @app.post("/api/runs/{run_id}/revise")
    async def api_create_run_improvement_session(run_id: str, request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        recovery = run_revision_workdir_recovery_payload(ctx.svc(), run_id)
        if recovery:
            return JSONResponse(recovery, status_code=400)
        try:
            session = ctx.svc().create_run_revision_session(run_id, **_alignment_executor_payload(payload))
        except (LooporaError, OSError, UnicodeError) as exc:
            return _api_revision_creation_error_response(ctx, "run", run_id, exc)
        return JSONResponse(
            {
                "session": session,
                "redirect_url": resource_workdir_context_href(
                    f"/loops/new/bundle?alignment_session_id={session['id']}",
                    session,
                ),
            },
            status_code=201,
        )


def _api_revision_creation_error_response(
    ctx: WebRouteContext,
    source_kind: str,
    source_id: str,
    exc: BaseException,
) -> JSONResponse:
    if is_revision_session_creation_recovery_error(exc):
        return JSONResponse(
            revision_session_creation_recovery_payload(
                source_kind,
                source_id,
                exc,
                workdir_context=revision_source_workdir_context(ctx.svc(), source_kind, source_id),
            ),
            status_code=ctx.error_status_code(exc),
        )
    return ctx.json_error(str(exc), status_code=ctx.error_status_code(exc))


def _register_alignment_workdir_context_route(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/api/alignments/workdir-context")
    async def api_alignment_workdir_context(request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        workdir_text = str(payload.get("workdir", "")).strip()
        if not web_alignment_workdir_ready(workdir_text):
            return JSONResponse(web_alignment_workdir_recovery_payload(workdir_text, action="workdir_context"), status_code=400)
        workdir = Path(workdir_text)
        try:
            return JSONResponse(ctx.svc().get_alignment_workdir_context(workdir))
        except LooporaWorkdirUnavailableError as exc:
            return JSONResponse(web_alignment_workdir_recovery_payload(exc.workdir, action="workdir_context"), status_code=400)


def _register_alignment_session_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    _register_alignment_session_creation_route(app, ctx)
    _register_alignment_session_record_routes(app, ctx)


def _register_alignment_session_creation_route(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/api/alignments/sessions")
    async def api_create_alignment_session(request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        message = str(payload.get("message", "") or payload.get("user_message", "") or "").strip()
        if not message:
            return ctx.json_error("message is required")
        workdir_text = str(payload.get("workdir", "")).strip()
        if not web_alignment_workdir_ready(workdir_text):
            return JSONResponse(web_alignment_workdir_recovery_payload(workdir_text, action="create_alignment_session"), status_code=400)
        workdir = Path(workdir_text)
        source_option_id = str(payload.get("source_option_id", "")).strip()
        try:
            session = ctx.svc().create_alignment_session(
                workdir=workdir,
                message=message,
                executor_kind=str(payload.get("executor_kind", "codex")).strip() or "codex",
                executor_mode=str(payload.get("executor_mode", "preset")).strip() or "preset",
                command_cli=str(payload.get("command_cli", "")).strip(),
                command_args_text=str(payload.get("command_args_text", "")),
                model=str(payload.get("model", "")).strip(),
                reasoning_effort=str(payload.get("reasoning_effort", "")).strip(),
                source_option_id=source_option_id,
                start_immediately=_coerce_bool(payload.get("start_immediately", True)),
            )
        except LooporaWorkdirUnavailableError as exc:
            return JSONResponse(web_alignment_workdir_recovery_payload(exc.workdir, action="create_alignment_session"), status_code=400)
        except (LooporaError, OSError, UnicodeError) as exc:
            return _api_alignment_session_creation_error_response(ctx, workdir_text, source_option_id, exc)
        return JSONResponse({"session": session}, status_code=201)


def _register_alignment_session_record_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/api/alignments/sessions")
    async def api_list_alignment_sessions(limit: Annotated[int, Query(ge=1, le=100)] = 30) -> JSONResponse:
        return JSONResponse({"sessions": ctx.svc().list_alignment_sessions(limit=limit)})

    @app.get("/api/alignments/sessions/{session_id}")
    async def api_get_alignment_session(session_id: str) -> JSONResponse:
        return JSONResponse({"session": ctx.svc().get_alignment_session(session_id)})

    @app.delete("/api/alignments/sessions/{session_id}")
    async def api_delete_alignment_session(session_id: str) -> JSONResponse:
        return JSONResponse({"deleted": ctx.svc().delete_alignment_session(session_id)})

    @app.post("/api/alignments/sessions/{session_id}/messages")
    async def api_append_alignment_message(session_id: str, request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        session = ctx.svc().append_alignment_message(session_id, str(payload.get("message", "")))
        return JSONResponse({"session": session})

    @app.post("/api/alignments/sessions/{session_id}/retry-generation")
    async def api_retry_alignment_generation(session_id: str, request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        executor_fields = {
            key: payload[key]
            for key in (
                "executor_kind",
                "executor_mode",
                "command_cli",
                "command_args_text",
                "model",
                "reasoning_effort",
            )
            if key in payload
        }
        session = ctx.svc().retry_alignment_generation(session_id, **executor_fields)
        return JSONResponse({"session": session})

    @app.post("/api/alignments/sessions/{session_id}/cancel")
    async def api_cancel_alignment_session(session_id: str) -> JSONResponse:
        return JSONResponse({"session": ctx.svc().cancel_alignment_session(session_id)})


def _api_alignment_session_creation_error_response(
    ctx: WebRouteContext,
    workdir: str,
    source_option_id: str,
    exc: BaseException,
) -> JSONResponse:
    if is_alignment_session_creation_recovery_error(exc):
        return JSONResponse(
            alignment_session_creation_recovery_payload(
                workdir=workdir,
                source_option_id=source_option_id,
                exc=exc,
            ),
            status_code=ctx.error_status_code(exc),
        )
    return ctx.json_error(str(exc), status_code=ctx.error_status_code(exc))


def _register_alignment_bundle_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/api/alignments/sessions/{session_id}/bundle")
    async def api_alignment_bundle(session_id: str) -> JSONResponse:
        result = ctx.svc().get_alignment_bundle(session_id)
        if result.get("ok") is False:
            return JSONResponse(
                alignment_bundle_preview_recovery_payload(
                    session_id,
                    result,
                    workdir_context=_alignment_session_workdir_context(ctx, session_id),
                )
            )
        return JSONResponse(result)

    @app.post("/api/alignments/sessions/{session_id}/bundle/sync")
    async def api_sync_alignment_bundle(session_id: str) -> JSONResponse:
        result = ctx.svc().sync_alignment_bundle_from_file(session_id)
        if result.get("ok") is False:
            return JSONResponse(
                alignment_bundle_sync_recovery_payload(
                    session_id,
                    result,
                    workdir_context=_alignment_session_workdir_context(ctx, session_id),
                )
            )
        return JSONResponse(result)

    @app.post("/api/alignments/sessions/{session_id}/import")
    async def api_import_alignment_bundle(session_id: str, request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        start_immediately = _coerce_bool(payload.get("start_immediately", True))
        try:
            result = ctx.svc().import_alignment_bundle(session_id, start_immediately=start_immediately)
        except (LooporaError, OSError, UnicodeError) as exc:
            if is_alignment_import_recovery_error(exc):
                return JSONResponse(
                    alignment_import_recovery_payload(
                        session_id,
                        exc,
                        workdir_context=_alignment_session_workdir_context(ctx, session_id),
                    ),
                    status_code=ctx.error_status_code(exc),
                )
            raise
        if result.get("run_start_error") and result.get("run"):
            run = ctx.svc().get_run(str(result["run"]["id"]))
            redirect_url = with_query_params(
                resource_workdir_context_href(
                    str(result.get("redirect_url") or f"/runs/{result['run']['id']}"),
                    run,
                ),
                run_action_error=str(result["run_start_error"]),
            )
            result.update(
                web_run_start_failure_payload(
                    run,
                    loop=result.get("loop") if isinstance(result.get("loop"), Mapping) else None,
                    redirect_url=redirect_url,
                    include_error=False,
                )
            )
        else:
            result = _alignment_import_result_with_resource_redirect(result)
        return JSONResponse(result, status_code=201)


def _alignment_executor_payload(payload: Mapping[str, object]) -> dict[str, object]:
    return {
        "message": str(payload.get("message", "") or ""),
        "executor_kind": str(payload.get("executor_kind", "codex")).strip() or "codex",
        "executor_mode": str(payload.get("executor_mode", "preset")).strip() or "preset",
        "command_cli": str(payload.get("command_cli", "")).strip(),
        "command_args_text": str(payload.get("command_args_text", "")),
        "model": str(payload.get("model", "")).strip(),
        "reasoning_effort": str(payload.get("reasoning_effort", "")).strip(),
        "start_immediately": _coerce_bool(payload.get("start_immediately", True)),
    }


def _alignment_import_result_with_resource_redirect(result: dict) -> dict:
    redirect_url = str(result.get("redirect_url") or "").strip()
    if not redirect_url:
        return result
    result = dict(result)
    result["redirect_url"] = resource_workdir_context_href(
        redirect_url,
        result.get("run") if isinstance(result.get("run"), Mapping) else None,
        result.get("loop") if isinstance(result.get("loop"), Mapping) else None,
        result.get("bundle") if isinstance(result.get("bundle"), Mapping) else None,
        result.get("session") if isinstance(result.get("session"), Mapping) else None,
    )
    return result


def _alignment_session_workdir_context(ctx: WebRouteContext, session_id: str) -> str:
    try:
        session = ctx.svc().get_alignment_session(session_id)
    except LooporaError:
        return ""
    return str(session.get("workdir") or "").strip()
