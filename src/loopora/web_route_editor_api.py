from __future__ import annotations

from fastapi import FastAPI

from loopora.web_asset_catalog_api_routes import register_asset_catalog_api_routes
from loopora.web_bundle_api_routes import register_bundle_api_routes
from loopora.web_route_context import WebRouteContext
from loopora.web_spec_api import register_spec_api_routes
from loopora.web_system_api import register_system_api_routes


def register_editor_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    register_bundle_api_routes(app, ctx)
    register_asset_catalog_api_routes(app, ctx)
    register_spec_api_routes(app, ctx)
    register_system_api_routes(app, ctx)
