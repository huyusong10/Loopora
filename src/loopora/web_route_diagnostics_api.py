from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from loopora.diagnose_doctor import DEFAULT_WEB_HOST, DEFAULT_WEB_PORT, build_doctor_report
from loopora.web_route_context import WebRouteContext


def register_diagnostics_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/api/diagnostics/doctor")
    async def api_doctor(workdir: str = "") -> JSONResponse:
        root = _diagnostic_workdir(workdir)
        host = str(ctx.access_state.get("bind_host") or DEFAULT_WEB_HOST)
        port = _diagnostic_web_port(ctx.access_state.get("bind_port"))
        return JSONResponse(build_doctor_report(workdir=root, web_host=host, web_port=port))

    @app.get("/api/diagnostics/local-assets")
    async def api_local_asset_diagnostics() -> JSONResponse:
        return JSONResponse(ctx.svc().local_asset_diagnostics())


def _diagnostic_workdir(value: str) -> Path:
    raw = str(value or "").strip()
    return Path(raw).expanduser().resolve() if raw else Path.cwd().resolve()


def _diagnostic_web_port(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return DEFAULT_WEB_PORT
