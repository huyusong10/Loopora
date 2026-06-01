from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from loopora.web_route_context import WebRouteContext


def register_system_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    _register_system_picker_api_routes(app, ctx)
    _register_system_reveal_api_route(app, ctx)


def _register_system_picker_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/api/system/pick-directory")
    async def api_pick_directory(request: Request) -> JSONResponse:
        guard = _guard_system_api_request(request, ctx)
        if guard is not None:
            return guard
        payload = await ctx.read_json_mapping(request)
        start_path = str(payload.get("start_path", "")).strip()
        selected = ctx.pick_directory_dialog(start_path or None)
        return JSONResponse({"path": selected or "", "cancelled": not selected})

    @app.post("/api/system/pick-spec-file")
    async def api_pick_spec_file(request: Request) -> JSONResponse:
        guard = _guard_system_api_request(request, ctx)
        if guard is not None:
            return guard
        payload = await ctx.read_json_mapping(request)
        start_path = str(payload.get("start_path", "")).strip()
        selected = ctx.pick_file_dialog(start_path or None)
        return JSONResponse({"path": selected or "", "cancelled": not selected})

    @app.post("/api/system/pick-bundle-file")
    async def api_pick_bundle_file(request: Request) -> JSONResponse:
        guard = _guard_system_api_request(request, ctx)
        if guard is not None:
            return guard
        payload = await ctx.read_json_mapping(request)
        start_path = str(payload.get("start_path", "")).strip()
        selected = ctx.pick_file_dialog(start_path or None)
        return JSONResponse({"path": selected or "", "cancelled": not selected})

    @app.post("/api/system/pick-spec-save-path")
    async def api_pick_spec_save_path(request: Request) -> JSONResponse:
        guard = _guard_system_api_request(request, ctx)
        if guard is not None:
            return guard
        payload = await ctx.read_json_mapping(request)
        start_path = str(payload.get("start_path", "")).strip()
        selected = ctx.pick_save_file_dialog(start_path or None, default_name="spec.md")
        return JSONResponse({"path": selected or "", "cancelled": not selected})


def _register_system_reveal_api_route(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/api/system/reveal-path")
    async def api_reveal_path(request: Request) -> JSONResponse:
        guard = _guard_system_api_request(request, ctx)
        if guard is not None:
            return guard
        payload = await ctx.read_json_mapping(request)
        target = str(payload.get("path") or "").strip()
        if not target:
            return ctx.json_error("path is required")
        return JSONResponse({"path": ctx.reveal_path_callback(target), "ok": True})


def _guard_system_api_request(request: Request, ctx: WebRouteContext) -> JSONResponse | None:
    if not _system_request_is_same_origin(request):
        return ctx.json_error("system API requests must come from the same origin", status_code=403)
    if not ctx.access_state["native_dialogs_enabled"]:
        return ctx.json_error("native dialogs are disabled in network mode; paste a server-side absolute path instead")
    return None


def _system_request_is_same_origin(request: Request) -> bool:
    references = [
        value.strip()
        for value in (
            request.headers.get("origin", ""),
            request.headers.get("referer", ""),
        )
        if value and value.strip()
    ]
    if not references:
        return True

    expected = _origin_tuple(
        scheme=request.url.scheme,
        hostname=request.url.hostname,
        port=request.url.port,
    )
    if expected is None:
        return False
    return all(_header_origin_tuple(value) == expected for value in references)


def _header_origin_tuple(value: str) -> tuple[str, str, int] | None:
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError:
        return None
    return _origin_tuple(scheme=parsed.scheme, hostname=parsed.hostname, port=port)


def _origin_tuple(*, scheme: str | None, hostname: str | None, port: int | None) -> tuple[str, str, int] | None:
    normalized_scheme = str(scheme or "").lower()
    normalized_host = str(hostname or "").lower()
    if not normalized_scheme or not normalized_host:
        return None
    if port is None:
        if normalized_scheme == "http":
            port = 80
        elif normalized_scheme == "https":
            port = 443
    return normalized_scheme, normalized_host, int(port or 0)
