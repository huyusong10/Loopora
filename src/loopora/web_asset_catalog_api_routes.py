from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from loopora.service import LooporaError
from loopora.strategy_source import StrategySourceError
from loopora.web_delete_preview_projection import web_delete_preview_payload
from loopora.web_editor_api_support import api_asset_mutation_error_response, api_asset_redirect_url
from loopora.web_role_inputs import _role_definition_payload_from_mapping
from loopora.web_route_context import WebRouteContext
from loopora.web_strategy_inputs import _orchestration_payload_from_mapping


def register_asset_catalog_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    _register_orchestration_api_routes(app, ctx)
    _register_role_definition_api_routes(app, ctx)


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
        try:
            orchestration = ctx.svc().create_orchestration(**_orchestration_payload_from_mapping(payload))
        except (LooporaError, StrategySourceError, OSError, UnicodeError, ValueError) as exc:
            return api_asset_mutation_error_response(ctx, exc, asset_label="orchestration")
        return JSONResponse(
            {
                "orchestration": orchestration,
                "redirect_url": api_asset_redirect_url(request, f"/orchestrations/{orchestration['id']}/edit"),
            },
            status_code=201,
        )

    @app.put("/api/orchestrations/{orchestration_id}")
    async def api_update_orchestration(orchestration_id: str, request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        try:
            orchestration = ctx.svc().update_orchestration(orchestration_id, **_orchestration_payload_from_mapping(payload))
        except (LooporaError, StrategySourceError, OSError, UnicodeError, ValueError) as exc:
            return api_asset_mutation_error_response(ctx, exc, asset_label="orchestration")
        return JSONResponse(
            {
                "orchestration": orchestration,
                "redirect_url": api_asset_redirect_url(request, f"/orchestrations/{orchestration['id']}/edit"),
            }
        )

    _register_orchestration_delete_api_routes(app, ctx)


def _register_orchestration_delete_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/api/orchestrations/{orchestration_id}/delete-preview")
    async def api_preview_delete_orchestration(orchestration_id: str) -> JSONResponse:
        try:
            return JSONResponse(
                web_delete_preview_payload(
                    ctx.svc().preview_orchestration_delete(orchestration_id),
                    resource_kind="orchestration",
                    resource_id=orchestration_id,
                )
            )
        except (LooporaError, OSError, UnicodeError, ValueError) as exc:
            return api_asset_mutation_error_response(ctx, exc, asset_label="orchestration", action="previewed")

    @app.delete("/api/orchestrations/{orchestration_id}")
    async def api_delete_orchestration(orchestration_id: str) -> JSONResponse:
        try:
            return JSONResponse(ctx.svc().delete_orchestration(orchestration_id))
        except (LooporaError, OSError, UnicodeError, ValueError) as exc:
            return api_asset_mutation_error_response(ctx, exc, asset_label="orchestration", action="deleted")


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
        try:
            role_definition = ctx.svc().create_role_definition(**_role_definition_payload_from_mapping(payload))
        except (LooporaError, OSError, UnicodeError, ValueError) as exc:
            return api_asset_mutation_error_response(ctx, exc, asset_label="role definition")
        return JSONResponse(
            {
                "role_definition": role_definition,
                "redirect_url": api_asset_redirect_url(request, f"/roles/{role_definition['id']}/edit"),
            },
            status_code=201,
        )

    @app.put("/api/role-definitions/{role_definition_id}")
    async def api_update_role_definition(role_definition_id: str, request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        try:
            role_definition = ctx.svc().update_role_definition(role_definition_id, **_role_definition_payload_from_mapping(payload))
        except (LooporaError, OSError, UnicodeError, ValueError) as exc:
            return api_asset_mutation_error_response(ctx, exc, asset_label="role definition")
        return JSONResponse(
            {
                "role_definition": role_definition,
                "redirect_url": api_asset_redirect_url(request, f"/roles/{role_definition['id']}/edit"),
            }
        )

    _register_role_definition_delete_api_routes(app, ctx)


def _register_role_definition_delete_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/api/role-definitions/{role_definition_id}/delete-preview")
    async def api_preview_delete_role_definition(role_definition_id: str) -> JSONResponse:
        try:
            return JSONResponse(
                web_delete_preview_payload(
                    ctx.svc().preview_role_definition_delete(role_definition_id),
                    resource_kind="role_definition",
                    resource_id=role_definition_id,
                )
            )
        except (LooporaError, OSError, UnicodeError, ValueError) as exc:
            return api_asset_mutation_error_response(ctx, exc, asset_label="role definition", action="previewed")

    @app.delete("/api/role-definitions/{role_definition_id}")
    async def api_delete_role_definition(role_definition_id: str) -> JSONResponse:
        try:
            return JSONResponse(ctx.svc().delete_role_definition(role_definition_id))
        except (LooporaError, OSError, UnicodeError, ValueError) as exc:
            return api_asset_mutation_error_response(ctx, exc, asset_label="role definition", action="deleted")
