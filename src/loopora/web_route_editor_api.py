from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from loopora.service import LooporaError
from loopora.web_role_inputs import (
    _role_definition_payload_from_mapping,
)
from loopora.web_route_context import WebRouteContext
from loopora.web_spec_api import register_spec_api_routes
from loopora.web_strategy_inputs import _orchestration_payload_from_mapping
from loopora.web_route_context_loop_pages import attachment_content_disposition

from urllib.parse import urlsplit


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


def _optional_api_identifier_value(value: object) -> object | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    return value


def register_editor_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    _register_bundle_record_api_routes(app, ctx)
    _register_bundle_import_api_routes(app, ctx)
    _register_bundle_preview_api_routes(app, ctx)
    _register_bundle_derive_api_routes(app, ctx)
    _register_bundle_export_api_routes(app, ctx)
    _register_orchestration_api_routes(app, ctx)
    _register_role_definition_api_routes(app, ctx)
    register_spec_api_routes(app, ctx)
    register_system_api_routes(app, ctx)


def _register_bundle_record_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/api/bundles")
    async def api_list_bundles() -> JSONResponse:
        return JSONResponse(ctx.svc().list_bundle_exchange_items())

    @app.get("/api/bundles/{bundle_id}")
    async def api_get_bundle(bundle_id: str) -> JSONResponse:
        bundle = ctx.svc().get_bundle(bundle_id)
        return JSONResponse(bundle)

    @app.put("/api/bundles/{bundle_id}")
    async def api_update_bundle(bundle_id: str, request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        bundle = ctx.svc().update_bundle(
            bundle_id,
            description=payload.get("description"),
            collaboration_summary=payload.get("collaboration_summary"),
            spec_markdown=payload.get("spec_markdown"),
        )
        return JSONResponse({"bundle": bundle, "redirect_url": f"/bundles/{bundle['id']}"})


def _import_bundle_or_error(importer):
    try:
        return importer()
    except OSError as exc:
        raise LooporaError("plan file could not be imported") from exc


def _register_bundle_import_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/api/bundles/import")
    async def api_import_bundle(request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        bundle_yaml = str(payload.get("bundle_yaml", ""))
        bundle_path = str(payload.get("bundle_path", "")).strip()
        replace_bundle_id = _optional_api_identifier_value(payload.get("replace_bundle_id"))
        if bundle_yaml.strip():
            bundle = _import_bundle_or_error(lambda: ctx.svc().import_bundle_text(bundle_yaml, replace_bundle_id=replace_bundle_id))
        elif bundle_path:
            bundle = _import_bundle_or_error(lambda: ctx.svc().import_bundle_file(Path(bundle_path), replace_bundle_id=replace_bundle_id))
        else:
            return ctx.json_error("bundle path or bundle YAML is required")
        return JSONResponse({"bundle": bundle, "redirect_url": f"/bundles/{bundle['id']}"}, status_code=201)


def _register_bundle_preview_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/api/bundles/preview")
    async def api_preview_bundle(request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        bundle_yaml = str(payload.get("bundle_yaml", ""))
        bundle_path = str(payload.get("bundle_path", "")).strip()
        try:
            if bundle_yaml.strip():
                preview = ctx.svc().preview_bundle_text(bundle_yaml)
            elif bundle_path:
                preview = ctx.svc().preview_bundle_file(Path(bundle_path))
            else:
                return JSONResponse({"ok": False, "error": "bundle path or bundle YAML is required"})
        except LooporaError as exc:
            return JSONResponse({"ok": False, "error": str(exc)})
        return JSONResponse(preview)


def _register_bundle_derive_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/api/bundles/derive")
    async def api_derive_bundle(request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        loop_id = str(payload.get("loop_id", "")).strip()
        if not loop_id:
            return ctx.json_error("loop id is required")
        try:
            bundle = ctx.svc().derive_bundle_from_loop(
                loop_id,
                name=str(payload.get("name", "")).strip() or None,
                description=str(payload.get("description", "")),
                collaboration_summary=str(payload.get("collaboration_summary", "")),
            )
        except OSError as exc:
            raise LooporaError("plan file could not be generated") from exc
        return JSONResponse({"bundle": bundle})


def _register_bundle_export_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/api/bundles/{bundle_id}/export")
    async def api_export_bundle(bundle_id: str) -> Response:
        bundle = ctx.svc().export_bundle(bundle_id)
        from loopora.bundles import bundle_to_yaml

        return Response(
            content=bundle_to_yaml(bundle),
            media_type="application/yaml; charset=utf-8",
            headers={
                "Content-Disposition": attachment_content_disposition(
                    f"{bundle['metadata']['name'] or bundle_id}.yml",
                    default=f"{bundle_id}.yml",
                )
            },
        )

    @app.delete("/api/bundles/{bundle_id}")
    async def api_delete_bundle(bundle_id: str) -> JSONResponse:
        return JSONResponse(ctx.svc().delete_bundle(bundle_id))


def _register_orchestration_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/api/orchestrations")
    async def api_list_orchestrations() -> JSONResponse:
        return JSONResponse(ctx.svc().list_orchestrations())

    @app.get("/api/orchestrations/{orchestration_id}")
    async def api_get_orchestration(orchestration_id: str) -> JSONResponse:
        return JSONResponse(ctx.svc().get_orchestration(orchestration_id))

    @app.post("/api/orchestrations")
    async def api_create_orchestration(request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        orchestration = ctx.svc().create_orchestration(**_orchestration_payload_from_mapping(payload))
        return JSONResponse(
            {"orchestration": orchestration, "redirect_url": f"/orchestrations/{orchestration['id']}/edit"},
            status_code=201,
        )

    @app.put("/api/orchestrations/{orchestration_id}")
    async def api_update_orchestration(orchestration_id: str, request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        orchestration = ctx.svc().update_orchestration(orchestration_id, **_orchestration_payload_from_mapping(payload))
        return JSONResponse({"orchestration": orchestration, "redirect_url": f"/orchestrations/{orchestration['id']}/edit"})

    @app.delete("/api/orchestrations/{orchestration_id}")
    async def api_delete_orchestration(orchestration_id: str) -> JSONResponse:
        return JSONResponse(ctx.svc().delete_orchestration(orchestration_id))


def _register_role_definition_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/api/role-definitions")
    async def api_list_role_definitions() -> JSONResponse:
        return JSONResponse(ctx.svc().list_role_definitions())

    @app.get("/api/role-definitions/{role_definition_id}")
    async def api_get_role_definition(role_definition_id: str) -> JSONResponse:
        return JSONResponse(ctx.svc().get_role_definition(role_definition_id))

    @app.post("/api/role-definitions")
    async def api_create_role_definition(request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        role_definition = ctx.svc().create_role_definition(**_role_definition_payload_from_mapping(payload))
        return JSONResponse(
            {"role_definition": role_definition, "redirect_url": f"/roles/{role_definition['id']}/edit"},
            status_code=201,
        )

    @app.put("/api/role-definitions/{role_definition_id}")
    async def api_update_role_definition(role_definition_id: str, request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        role_definition = ctx.svc().update_role_definition(role_definition_id, **_role_definition_payload_from_mapping(payload))
        return JSONResponse({"role_definition": role_definition, "redirect_url": f"/roles/{role_definition['id']}/edit"})

    @app.delete("/api/role-definitions/{role_definition_id}")
    async def api_delete_role_definition(role_definition_id: str) -> JSONResponse:
        return JSONResponse(ctx.svc().delete_role_definition(role_definition_id))
