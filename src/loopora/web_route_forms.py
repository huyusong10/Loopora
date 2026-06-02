from __future__ import annotations

from fastapi import FastAPI

from loopora.web_bundle_form_routes import register_bundle_form_routes
from loopora.web_improvement_form_routes import register_improvement_form_routes
from loopora.web_loop_form_routes import register_loop_form_routes
from loopora.web_orchestration_form_routes import register_orchestration_form_routes
from loopora.web_role_form_routes import register_role_form_routes
from loopora.web_route_context import WebRouteContext


def register_form_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    register_improvement_form_routes(app, ctx)
    register_loop_form_routes(app, ctx)
    register_orchestration_form_routes(app, ctx)
    register_role_form_routes(app, ctx)
    register_bundle_form_routes(app, ctx)
