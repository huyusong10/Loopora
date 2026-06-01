from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from loopora.web_overviews import _format_timeline_event
from loopora.web_loop_inputs import _loop_payload_from_mapping
from loopora.web_route_context import WebRouteContext
from loopora.web_run_artifact_api import register_file_api_routes, register_run_artifact_api_routes
from loopora.web_run_event_api import register_run_event_api_routes


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
        loop_kwargs, start_immediately = _loop_payload_from_mapping(payload)
        loop = ctx.svc().create_loop(**loop_kwargs)
        if start_immediately:
            run = ctx.svc().start_run(loop["id"])
            ctx.svc().start_run_async(run["id"])
            return JSONResponse({"loop": loop, "run": run, "redirect_url": f"/runs/{run['id']}"}, status_code=201)
        return JSONResponse({"loop": loop, "redirect_url": f"/loops/{loop['id']}"}, status_code=201)

    @app.get("/api/loops")
    async def api_list_loops() -> JSONResponse:
        return JSONResponse(ctx.svc().list_loops())

    @app.get("/api/runtime/activity")
    async def api_runtime_activity() -> JSONResponse:
        return JSONResponse(ctx.svc().get_runtime_activity())

    @app.get("/api/loops/{loop_id}")
    async def api_get_loop(loop_id: str) -> JSONResponse:
        return JSONResponse(ctx.svc().get_loop(loop_id))

    @app.delete("/api/loops/{loop_id}")
    async def api_delete_loop(loop_id: str) -> JSONResponse:
        return JSONResponse(ctx.svc().delete_loop(loop_id))

    @app.post("/api/loops/{loop_id}/runs")
    async def api_start_run(loop_id: str) -> JSONResponse:
        agent_entry_start = ctx.svc().agent_entry_loop_start_projection(loop_id)
        if agent_entry_start:
            return JSONResponse(
                {
                    "error": "agent-first Loop runs must be started or continued with /loopora-run in the host Agent",
                    "agent_entry_start": agent_entry_start,
                },
                status_code=409,
            )
        run = ctx.svc().start_run(loop_id)
        ctx.svc().start_run_async(run["id"])
        return JSONResponse(run, status_code=201)


def _register_run_observation_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/api/runs/{run_id}")
    async def api_get_run(run_id: str) -> JSONResponse:
        run = ctx.svc().get_run(run_id)
        projection = ctx.svc().app_services.projection.web_run_detail(run)
        return JSONResponse({**run, "web_projection": projection})

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
        return JSONResponse(ctx.svc().stop_run(run_id))
