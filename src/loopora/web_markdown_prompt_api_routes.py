from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response

from loopora.markdown_tools import render_safe_markdown_html
from loopora.strategy_source import (
    StrategySourceError,
    builtin_strategy_prompt_markdown,
    validate_strategy_prompt_markdown,
)
from loopora.web_common_inputs import _coerce_bool
from loopora.web_route_context import WebRouteContext
from loopora.web_url_utils import attachment_content_disposition


def register_markdown_prompt_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/api/markdown/render")
    async def api_render_markdown(request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        markdown_text = str(payload.get("markdown", ""))
        strip_front_matter = _coerce_bool(payload.get("strip_front_matter", False))
        return JSONResponse(
            {
                "ok": True,
                "rendered_html": render_safe_markdown_html(markdown_text, strip_front_matter=strip_front_matter),
            }
        )

    @app.post("/api/prompts/validate")
    async def api_validate_prompt(request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        markdown_text = str(payload.get("markdown", ""))
        expected_archetype = str(payload.get("archetype", "")).strip() or None
        try:
            metadata, body = validate_strategy_prompt_markdown(markdown_text, expected_archetype=expected_archetype)
        except StrategySourceError as exc:
            return JSONResponse({"ok": False, "error": str(exc)})
        return JSONResponse({"ok": True, "metadata": metadata, "body": body})

    @app.get("/api/prompts/templates/{prompt_ref}")
    async def api_prompt_template(prompt_ref: str, locale: Annotated[str | None, Query()] = None) -> Response:
        try:
            markdown_text = builtin_strategy_prompt_markdown(prompt_ref, locale=locale)
        except StrategySourceError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return Response(
            content=markdown_text,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": attachment_content_disposition(prompt_ref, default="prompt.md")},
        )
