from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from loopora.asset_errors import asset_mutation_error_message
from loopora.bundles import bundle_to_yaml
from loopora.service import LooporaError
from loopora.web_bundle_export_recovery import web_bundle_export_generation_recovery_payload
from loopora.web_bundle_import_recovery import (
    web_bundle_import_file_workdir_recovery,
    web_bundle_import_text_workdir_recovery,
)
from loopora.web_bundle_inputs import bundle_import_preview_review_token
from loopora.web_delete_preview_projection import web_delete_preview_payload
from loopora.web_editor_api_support import api_asset_mutation_error_response
from loopora.web_route_context import WebRouteContext
from loopora.web_start_context import request_resource_workdir_context_href
from loopora.web_url_utils import attachment_content_disposition


def register_bundle_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    _register_bundle_record_api_routes(app, ctx)
    _register_bundle_import_api_routes(app, ctx)
    _register_bundle_export_api_routes(app, ctx)


def _optional_api_identifier_value(value: object) -> object | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    return value


def _api_bundle_redirect_url(request: Request, bundle: Mapping[str, object]) -> str:
    return request_resource_workdir_context_href(request, f"/bundles/{bundle['id']}", bundle)


def _api_bundle_workdir_context(ctx: WebRouteContext, bundle_id: str) -> str:
    try:
        bundle = ctx.svc().get_bundle(bundle_id)
    except LooporaError:
        return ""
    return str(bundle.get("workdir") or "").strip()


def _register_bundle_record_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/api/bundles")
    async def api_list_bundles() -> JSONResponse:
        return JSONResponse(ctx.svc().list_bundle_exchange_items())

    @app.get("/api/bundles/{bundle_id}")
    async def api_get_bundle(bundle_id: str) -> JSONResponse:
        bundle = ctx.svc().get_bundle(bundle_id)
        return JSONResponse(bundle)

    @app.get("/api/bundles/{bundle_id}/delete-preview")
    async def api_preview_delete_bundle(bundle_id: str) -> JSONResponse:
        return JSONResponse(
            web_delete_preview_payload(
                ctx.svc().preview_bundle_delete(bundle_id),
                resource_kind="bundle",
                resource_id=bundle_id,
            )
        )

    @app.put("/api/bundles/{bundle_id}")
    async def api_update_bundle(bundle_id: str, request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        try:
            if "spec_markdown" in payload:
                bundle = ctx.svc().update_bundle(
                    bundle_id,
                    description=payload.get("description"),
                    collaboration_summary=payload.get("collaboration_summary"),
                    spec_markdown=payload.get("spec_markdown"),
                )
            else:
                bundle = ctx.svc().update_bundle_metadata(
                    bundle_id,
                    description=payload.get("description"),
                    collaboration_summary=payload.get("collaboration_summary"),
                )
        except (OSError, UnicodeError) as exc:
            return ctx.json_error(asset_mutation_error_message(exc, asset_label="plan file"))
        return JSONResponse({"bundle": bundle, "redirect_url": _api_bundle_redirect_url(request, bundle)})


def _register_bundle_import_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/api/bundles/import")
    async def api_import_bundle(request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        bundle_yaml, bundle_path, replace_bundle_id = _api_bundle_import_source(payload)
        if not bundle_yaml.strip() and not bundle_path:
            return ctx.json_error("bundle path or bundle YAML is required")
        recovery = _api_bundle_import_workdir_recovery(bundle_yaml, bundle_path, replace_bundle_id)
        if recovery is not None:
            return JSONResponse(recovery, status_code=400)
        return _api_import_bundle_response(ctx, request, bundle_yaml, bundle_path, replace_bundle_id)

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
        preview["preview_review_token"] = bundle_import_preview_review_token(payload)
        return JSONResponse(preview)

    @app.post("/api/bundles/derive")
    async def api_derive_bundle(request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        return _api_derive_bundle_response(ctx, payload)


def _api_derive_bundle_response(ctx: WebRouteContext, payload: Mapping[str, object]) -> JSONResponse:
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
    except (LooporaError, OSError, UnicodeError, ValueError) as exc:
        return api_asset_mutation_error_response(ctx, exc, asset_label="plan file", action="generated")
    return JSONResponse({"bundle": bundle})


def _api_bundle_import_source(payload: Mapping[str, object]) -> tuple[str, str, object | None]:
    return (
        str(payload.get("bundle_yaml", "")),
        str(payload.get("bundle_path", "")).strip(),
        _optional_api_identifier_value(payload.get("replace_bundle_id")),
    )


def _api_bundle_import_workdir_recovery(
    bundle_yaml: str,
    bundle_path: str,
    replace_bundle_id: object | None,
) -> dict[str, object] | None:
    action = "replace_bundle" if replace_bundle_id is not None else "import_bundle"
    if bundle_yaml.strip():
        return web_bundle_import_text_workdir_recovery(bundle_yaml, action=action)
    if bundle_path:
        return web_bundle_import_file_workdir_recovery(Path(bundle_path), action=action)
    return None


def _api_import_bundle(
    ctx: WebRouteContext,
    bundle_yaml: str,
    bundle_path: str,
    replace_bundle_id: object | None,
) -> dict:
    if bundle_yaml.strip():
        return ctx.svc().import_bundle_text(bundle_yaml, replace_bundle_id=replace_bundle_id)
    return ctx.svc().import_bundle_file(Path(bundle_path), replace_bundle_id=replace_bundle_id)


def _api_import_bundle_response(
    ctx: WebRouteContext,
    request: Request,
    bundle_yaml: str,
    bundle_path: str,
    replace_bundle_id: object | None,
) -> JSONResponse:
    try:
        bundle = _api_import_bundle(ctx, bundle_yaml, bundle_path, replace_bundle_id)
    except (OSError, UnicodeError) as exc:
        return ctx.json_error(asset_mutation_error_message(exc, asset_label="plan file", action="imported"))
    return JSONResponse({"bundle": bundle, "redirect_url": _api_bundle_redirect_url(request, bundle)}, status_code=201)


def _register_bundle_export_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/api/bundles/{bundle_id}/export")
    async def api_export_bundle(bundle_id: str) -> Response:
        try:
            bundle = ctx.svc().export_bundle(bundle_id)
            yaml_text = bundle_to_yaml(bundle)
        except (LooporaError, OSError, UnicodeError, ValueError) as exc:
            return JSONResponse(
                web_bundle_export_generation_recovery_payload(
                    bundle_id,
                    exc,
                    workdir_context=_api_bundle_workdir_context(ctx, bundle_id),
                ),
                status_code=ctx.error_status_code(exc),
            )

        return Response(
            content=yaml_text,
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
