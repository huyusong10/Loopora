from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from starlette.exceptions import HTTPException

from loopora.diagnostics import log_event
from loopora.service_types import LooporaError
from loopora.specs import SpecError
from loopora.strategy_source import StrategySourceError
from loopora.system_dialogs import SystemDialogError
from loopora.web_request_context import _request_wants_json
from loopora.web_route_context import WebRouteContext


def register_error_handlers(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_error_handler(request: Request, exc: HTTPException) -> Response:
        detail = exc.detail if isinstance(exc.detail, str) else "request failed"
        return _domain_error_response(request, ctx, detail, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(request: Request, _exc: RequestValidationError) -> Response:
        return _domain_error_response(request, ctx, "request validation failed", status_code=400)

    @app.exception_handler(LooporaError)
    async def loopora_error_handler(request: Request, exc: LooporaError) -> Response:
        log_event(
            ctx.logger,
            logging.WARNING,
            "web.request.domain_error",
            "Request failed with a Loopora domain error",
            method=request.method,
            request_path=request.url.path,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        return _domain_error_response(request, ctx, str(exc), status_code=getattr(exc, "status_code", 400))

    @app.exception_handler(SpecError)
    async def spec_error_handler(request: Request, exc: SpecError) -> Response:
        log_event(
            ctx.logger,
            logging.WARNING,
            "web.request.domain_error",
            "Request failed with a spec validation error",
            method=request.method,
            request_path=request.url.path,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        return _domain_error_response(request, ctx, str(exc), status_code=400)

    @app.exception_handler(StrategySourceError)
    async def strategy_source_error_handler(request: Request, exc: StrategySourceError) -> Response:
        log_event(
            ctx.logger,
            logging.WARNING,
            "web.request.domain_error",
            "Request failed with a strategy source validation error",
            method=request.method,
            request_path=request.url.path,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        return _domain_error_response(request, ctx, str(exc), status_code=400)

    @app.exception_handler(SystemDialogError)
    async def system_dialog_error_handler(request: Request, exc: SystemDialogError) -> Response:
        log_event(
            ctx.logger,
            logging.WARNING,
            "web.request.domain_error",
            "Request failed while opening a system dialog",
            method=request.method,
            request_path=request.url.path,
            error_type=type(exc).__name__,
            error_message=str(exc),
            error_detail=str(getattr(exc, "detail", "") or ""),
        )
        if not _request_wants_json(request):
            return _domain_error_page(status_code=400)
        return JSONResponse(
            {"error": str(exc), "error_code": str(getattr(exc, "code", "") or "system_dialog_failed")},
            status_code=400,
        )


def _domain_error_response(request: Request, ctx: WebRouteContext, message: str, *, status_code: int) -> Response:
    if _request_wants_json(request):
        return ctx.json_error(message, status_code=status_code)
    return _domain_error_page(status_code=status_code)


def _domain_error_page(*, status_code: int) -> HTMLResponse:
    return HTMLResponse(
        "<!doctype html><html lang='en'><head><meta charset='utf-8'><title>Request failed</title></head>"
        "<body><main data-testid='web-error-page'><h1>Loopora could not complete this request</h1>"
        f"<p data-testid='web-error-status'>Status {status_code}</p>"
        "<p><a href='/' data-testid='web-error-home-link'>Return to Loopora home</a></p></main></body></html>",
        status_code=status_code,
    )
