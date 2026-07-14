from __future__ import annotations

from collections.abc import Mapping

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from loopora.action_readiness_projection import project_next_action_readiness_contract
from loopora.agent_entry_run_projection import AGENT_NATIVE_WEB_START_ERROR
from loopora.asset_errors import asset_mutation_error_message
from loopora.service_types import LooporaConflictError, LooporaError, LooporaWorkdirUnavailableError
from loopora.spec_recovery_commands import effective_spec_init_strategy_context
from loopora.web_overviews import _format_timeline_event
from loopora.web_loop_inputs import (
    _loop_payload_from_mapping,
    _loop_strategy_preset_from_mapping,
    _loop_strategy_source_from_mapping,
    validate_loop_payload_compose_options,
)
from loopora.web_route_context import WebRouteContext
from loopora.web_delete_preview_projection import web_delete_preview_payload
from loopora.web_run_dispatch import is_background_worker_start_error, start_run_async_error, web_run_start_failure_payload
from loopora.web_run_artifact_api import register_file_api_routes, register_run_artifact_api_routes
from loopora.web_run_event_api import register_run_event_api_routes
from loopora.web_start_context import resource_workdir_context_href
from loopora.web_workdir_recovery import (
    web_alignment_workdir_ready,
    web_loop_create_spec_ready,
    web_loop_create_spec_recovery_payload,
    web_loop_create_workdir_recovery_payload,
    web_loop_start_workdir_recovery_payload,
)


def register_run_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    _register_loop_api_routes(app, ctx)
    _register_run_observation_api_routes(app, ctx)
    register_run_event_api_routes(app, ctx)
    register_run_artifact_api_routes(app, ctx)
    register_file_api_routes(app, ctx)


def _register_loop_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/api/loops")
    async def api_create_loop(request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        return _api_create_loop_response(ctx, payload)

    @app.get("/api/loops")
    async def api_list_loops() -> JSONResponse:
        return JSONResponse(ctx.svc().list_loops())

    @app.get("/api/runtime/activity")
    async def api_runtime_activity() -> JSONResponse:
        return JSONResponse(ctx.svc().get_runtime_activity())

    @app.get("/api/loops/{loop_id}")
    async def api_get_loop(loop_id: str) -> JSONResponse:
        return JSONResponse(ctx.svc().get_loop(loop_id))

    @app.get("/api/loops/{loop_id}/delete-preview")
    async def api_preview_delete_loop(loop_id: str) -> JSONResponse:
        return JSONResponse(
            web_delete_preview_payload(
                ctx.svc().preview_loop_delete(loop_id),
                resource_kind="loop",
                resource_id=loop_id,
            )
        )

    @app.delete("/api/loops/{loop_id}")
    async def api_delete_loop(loop_id: str) -> JSONResponse:
        return JSONResponse(ctx.svc().delete_loop(loop_id))

    @app.post("/api/loops/{loop_id}/runs")
    async def api_start_run(loop_id: str) -> JSONResponse:
        return _api_start_run_response(ctx, loop_id)


def _api_create_loop_response(ctx: WebRouteContext, payload: Mapping[str, object]) -> JSONResponse:
    recovery_response = _api_loop_create_recovery_response(payload)
    if recovery_response is not None:
        return recovery_response
    try:
        loop_kwargs, start_immediately = _loop_payload_from_mapping(payload)
        loop = ctx.svc().create_loop(**loop_kwargs)
    except LooporaWorkdirUnavailableError as exc:
        return JSONResponse(web_loop_create_workdir_recovery_payload(exc.workdir), status_code=400)
    except (LooporaError, FileExistsError, OSError, UnicodeError, ValueError) as exc:
        return JSONResponse({"error": asset_mutation_error_message(exc, asset_label="Loop", action="created")}, status_code=400)
    if start_immediately:
        return _api_created_loop_start_response(ctx, loop)
    return JSONResponse({"loop": loop, "redirect_url": resource_workdir_context_href(f"/loops/{loop['id']}", loop)}, status_code=201)


def _api_loop_create_recovery_response(payload: Mapping[str, object]) -> JSONResponse | None:
    try:
        validate_loop_payload_compose_options(payload)
    except LooporaError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    workdir_text = str(payload.get("workdir", "")).strip()
    if not web_alignment_workdir_ready(workdir_text):
        return JSONResponse(web_loop_create_workdir_recovery_payload(workdir_text), status_code=400)
    spec_path_text = str(payload.get("spec_path", "")).strip()
    if not web_loop_create_spec_ready(spec_path_text):
        return JSONResponse(
            web_loop_create_spec_recovery_payload(
                spec_path_text,
                orchestration_id=payload.get("orchestration_id", ""),
                strategy_preset=_loop_strategy_preset_from_mapping(payload),
                strategy_context=effective_spec_init_strategy_context(
                    orchestration_id=payload.get("orchestration_id", ""),
                    strategy_preset=_loop_strategy_preset_from_mapping(payload),
                    strategy_source=_loop_strategy_source_from_mapping(payload),
                ),
            ),
            status_code=400,
        )
    return None


def _api_created_loop_start_response(ctx: WebRouteContext, loop: Mapping[str, object]) -> JSONResponse:
    loop_id = str(loop["id"])
    try:
        run = ctx.svc().start_run(loop_id)
    except LooporaWorkdirUnavailableError as exc:
        return JSONResponse(web_loop_start_workdir_recovery_payload(loop_id, exc.workdir), status_code=400)
    dispatch_error = _api_run_dispatch_error_response(ctx, run, loop=loop)
    if dispatch_error is not None:
        return dispatch_error
    return JSONResponse({"loop": loop, "run": run, "redirect_url": resource_workdir_context_href(f"/runs/{run['id']}", run, loop)}, status_code=201)


def _api_start_run_response(ctx: WebRouteContext, loop_id: str) -> JSONResponse:
    agent_entry_start = ctx.svc().agent_entry_loop_start_projection(loop_id)
    if agent_entry_start:
        return JSONResponse(
            {
                "error": AGENT_NATIVE_WEB_START_ERROR,
                "agent_entry_start": agent_entry_start,
            },
            status_code=409,
        )
    try:
        run = ctx.svc().start_next_run(loop_id)
    except LooporaWorkdirUnavailableError as exc:
        return JSONResponse(web_loop_start_workdir_recovery_payload(loop_id, exc.workdir), status_code=400)
    dispatch_error = _api_run_dispatch_error_response(ctx, run)
    if dispatch_error is not None:
        return dispatch_error
    return JSONResponse(run, status_code=201)


def _api_run_dispatch_error_response(
    ctx: WebRouteContext,
    run: Mapping[str, object],
    *,
    loop: Mapping[str, object] | None = None,
) -> JSONResponse | None:
    dispatch_error = start_run_async_error(ctx.svc(), run)
    if dispatch_error is None:
        return None
    payload: dict[str, object] = {"error": str(dispatch_error)}
    if is_background_worker_start_error(dispatch_error):
        payload = web_run_start_failure_payload(ctx.svc().get_run(str(run["id"])), loop=loop)
        return JSONResponse(payload, status_code=503)
    return JSONResponse(payload, status_code=getattr(dispatch_error, "status_code", 400))


def _register_run_observation_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/api/runs/{run_id}")
    async def api_get_run(run_id: str) -> JSONResponse:
        run = ctx.svc().get_run(run_id)
        projection = ctx.svc().app_services.projection.web_run_detail(run)
        return JSONResponse(
            {
                **run,
                "web_projection": projection,
                "continuation": ctx.svc().run_continuation_state(run_id),
                "continuation_outcome": ctx.svc().run_continuation_outcome(run_id),
            }
        )

    @app.get("/api/runs/{run_id}/observation-snapshot")
    async def api_run_observation_snapshot(run_id: str) -> JSONResponse:
        snapshot = ctx.svc().run_observation_snapshot(run_id)
        return JSONResponse(
            {
                **snapshot,
                "timeline_events": [_format_timeline_event(event) for event in snapshot["timeline_events"]],
            }
        )

    @app.post("/api/runs/{run_id}/stop")
    async def api_stop_run(run_id: str) -> JSONResponse:
        try:
            return JSONResponse(ctx.svc().stop_run(run_id))
        except LooporaConflictError as exc:
            return JSONResponse(_api_stop_run_refresh_recovery_payload(ctx.svc().get_run(run_id), str(exc)), status_code=409)


def _api_stop_run_refresh_recovery_payload(run: Mapping[str, object], error: str) -> dict[str, object]:
    run_id = str(run.get("id") or "")
    run_status = str(run.get("status") or "")
    redirect_url = resource_workdir_context_href(f"/runs/{run_id}", run) if run_id else "/"
    next_action = {
        "kind": "refresh_run_detail",
        "target": "web_run_detail",
        "run_id": run_id,
        "redirect_url": redirect_url,
    }
    return project_next_action_readiness_contract(
        {
            "error": error,
            "run_action_recovery": "refresh_run_detail",
            "run": {
                "id": run_id,
                "status": run_status,
                "loop_id": str(run.get("loop_id") or ""),
            },
            "redirect_url": redirect_url,
            "next_actions": [next_action],
        }
    )
