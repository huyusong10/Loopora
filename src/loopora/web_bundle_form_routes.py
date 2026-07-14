from __future__ import annotations

from fastapi import FastAPI

from loopora.web_bundle_derive_form_routes import register_bundle_derive_form_routes
from loopora.web_bundle_edit_form_routes import register_bundle_edit_form_routes
from loopora.web_bundle_import_form_routes import register_bundle_import_form_routes
from loopora.web_bundle_run_routes import register_bundle_run_routes
from loopora.web_route_context import WebRouteContext


def register_bundle_form_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    register_bundle_import_form_routes(app, ctx)
    register_bundle_run_routes(app, ctx)
    register_bundle_edit_form_routes(app, ctx)
    register_bundle_derive_form_routes(app, ctx)
