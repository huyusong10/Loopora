from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

from loopora.web_alignment_event_api import register_alignment_event_api_routes
from loopora.web_common_inputs import _coerce_bool
from loopora.web_route_context import WebRouteContext


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
        session = ctx.svc().create_bundle_revision_session(bundle_id, **_alignment_executor_payload(payload))
        return JSONResponse(
            {"session": session, "redirect_url": f"/loops/new/bundle?alignment_session_id={session['id']}"},
            status_code=201,
        )

    @app.post("/api/runs/{run_id}/revise")
    async def api_create_run_improvement_session(run_id: str, request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        session = ctx.svc().create_run_revision_session(run_id, **_alignment_executor_payload(payload))
        return JSONResponse(
            {"session": session, "redirect_url": f"/loops/new/bundle?alignment_session_id={session['id']}"},
            status_code=201,
        )


def _register_alignment_workdir_context_route(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/api/alignments/workdir-context")
    async def api_alignment_workdir_context(request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        workdir_text = str(payload.get("workdir", "")).strip()
        if not workdir_text:
            return ctx.json_error("workdir is required")
        return JSONResponse(ctx.svc().get_alignment_workdir_context(Path(workdir_text)))


def _register_alignment_session_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/api/alignments/sessions")
    async def api_create_alignment_session(request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        message = str(payload.get("message", "") or payload.get("user_message", "") or "")
        workdir_text = str(payload.get("workdir", "")).strip()
        if not workdir_text:
            return ctx.json_error("workdir is required")
        session = ctx.svc().create_alignment_session(
            workdir=Path(workdir_text),
            message=message,
            executor_kind=str(payload.get("executor_kind", "codex")).strip() or "codex",
            executor_mode=str(payload.get("executor_mode", "preset")).strip() or "preset",
            command_cli=str(payload.get("command_cli", "")).strip(),
            command_args_text=str(payload.get("command_args_text", "")),
            model=str(payload.get("model", "")).strip(),
            reasoning_effort=str(payload.get("reasoning_effort", "")).strip(),
            source_option_id=str(payload.get("source_option_id", "")).strip(),
            start_immediately=_coerce_bool(payload.get("start_immediately", True)),
        )
        return JSONResponse({"session": session}, status_code=201)

    @app.get("/api/alignments/sessions")
    async def api_list_alignment_sessions(limit: int = Query(default=30, ge=1, le=100)) -> JSONResponse:
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

    @app.post("/api/alignments/sessions/{session_id}/cancel")
    async def api_cancel_alignment_session(session_id: str) -> JSONResponse:
        return JSONResponse({"session": ctx.svc().cancel_alignment_session(session_id)})


def _register_alignment_bundle_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/api/alignments/sessions/{session_id}/bundle")
    async def api_alignment_bundle(session_id: str) -> JSONResponse:
        return JSONResponse(ctx.svc().get_alignment_bundle(session_id))

    @app.post("/api/alignments/sessions/{session_id}/bundle/sync")
    async def api_sync_alignment_bundle(session_id: str) -> JSONResponse:
        return JSONResponse(ctx.svc().sync_alignment_bundle_from_file(session_id))

    @app.post("/api/alignments/sessions/{session_id}/import")
    async def api_import_alignment_bundle(session_id: str, request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        start_immediately = _coerce_bool(payload.get("start_immediately", True))
        result = ctx.svc().import_alignment_bundle(session_id, start_immediately=start_immediately)
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
