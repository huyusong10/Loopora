from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import Response

from loopora.web_route_context import WebRouteContext


def register_auth_form_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/auth/token")
    async def submit_auth_token(request: Request) -> Response:
        return await ctx.submit_auth_token(request)
