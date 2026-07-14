from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from loopora.web_page_query_redirects import clean_bundles_query_redirect
from loopora.web_route_context import WebRouteContext


def register_library_page_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/orchestrations", response_class=HTMLResponse)
    async def orchestrations_page(request: Request) -> HTMLResponse:
        return ctx.render_orchestrations(request)

    @app.get("/bundles", response_class=HTMLResponse)
    async def bundles_page(request: Request):
        if redirect := clean_bundles_query_redirect(request):
            return redirect
        return ctx.render_bundles(request, import_values=request.query_params or None)

    @app.get("/bundles/{bundle_id}", response_class=HTMLResponse)
    async def bundle_detail_page(request: Request, bundle_id: str) -> HTMLResponse:
        return ctx.render_bundle_detail(request, bundle_id)

    @app.get("/roles", response_class=HTMLResponse)
    async def role_definitions_page(request: Request) -> HTMLResponse:
        return ctx.render_role_definitions(request)

    @app.get("/orchestrations/new", response_class=HTMLResponse)
    async def new_orchestration(request: Request) -> HTMLResponse:
        preset = str(request.query_params.get("workflow_preset", "")).strip()
        values = request.query_params if preset else None
        return ctx.render_new_orchestration(request, values=values)

    @app.get("/orchestrations/{orchestration_id}/edit", response_class=HTMLResponse)
    async def edit_orchestration(request: Request, orchestration_id: str) -> HTMLResponse:
        return ctx.render_new_orchestration(request, orchestration=ctx.svc().get_orchestration(orchestration_id))

    @app.get("/roles/new", response_class=HTMLResponse)
    async def new_role_definition(request: Request) -> HTMLResponse:
        return ctx.render_new_role_definition(request, values=request.query_params or None)

    @app.get("/roles/{role_definition_id}/edit", response_class=HTMLResponse)
    async def edit_role_definition(request: Request, role_definition_id: str) -> HTMLResponse:
        return ctx.render_new_role_definition(request, role_definition=ctx.svc().get_role_definition(role_definition_id))
