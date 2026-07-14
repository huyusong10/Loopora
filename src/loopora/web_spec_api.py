from __future__ import annotations

from fastapi import FastAPI

from loopora.web_markdown_prompt_api_routes import register_markdown_prompt_api_routes
from loopora.web_route_context import WebRouteContext
from loopora.web_spec_document_api_routes import register_spec_document_api_routes
from loopora.web_spec_template_api_routes import register_spec_template_api_routes


def register_spec_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    register_spec_document_api_routes(app, ctx)
    register_markdown_prompt_api_routes(app, ctx)
    register_spec_template_api_routes(app, ctx)
