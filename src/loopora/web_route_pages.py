from __future__ import annotations

from fastapi import FastAPI

from loopora.web_bundle_export_page_routes import register_bundle_export_page_routes
from loopora.web_home_create_page_routes import register_home_create_page_routes
from loopora.web_library_page_routes import register_library_page_routes
from loopora.web_route_context import WebRouteContext
from loopora.web_route_loop_run_pages import register_loop_run_page_routes
from loopora.web_support_page_routes import register_support_page_routes


def register_page_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    register_home_create_page_routes(app, ctx)
    register_library_page_routes(app, ctx)
    register_bundle_export_page_routes(app, ctx)
    register_support_page_routes(app, ctx)
    register_loop_run_page_routes(app, ctx)
