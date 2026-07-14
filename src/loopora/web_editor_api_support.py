from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from loopora.web_asset_validation_recovery import web_asset_mutation_error_payload
from loopora.web_route_context import WebRouteContext
from loopora.web_start_context import request_workdir_context, workdir_context_href


def api_asset_mutation_error_response(
    ctx: WebRouteContext,
    exc: BaseException,
    *,
    asset_label: str,
    action: str = "saved",
) -> JSONResponse:
    return JSONResponse(
        web_asset_mutation_error_payload(exc, asset_label=asset_label, action=action),
        status_code=ctx.error_status_code(exc),
    )


def api_asset_redirect_url(request: Request, path: str) -> str:
    return workdir_context_href(path, request_workdir_context(request))
