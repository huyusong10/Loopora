from __future__ import annotations

import hmac
import logging
import time
from collections.abc import Callable, Mapping

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from loopora.branding import APP_AUTH_COOKIE
from loopora.diagnostics import log_event, log_exception
from loopora.web_request_context import _extract_request_token

AUTH_COOKIE_NAME = APP_AUTH_COOKIE
INTERNAL_API_ERROR_MESSAGE = "internal server error"


def install_auth_middleware(
    app: FastAPI,
    access_state: Mapping[str, object],
    auth_required_response: Callable[[Request], Response],
    *,
    logger: logging.Logger,
) -> None:
    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        start_time = time.perf_counter()
        expected_token = access_state["auth_token"]
        if not expected_token:
            try:
                response = await call_next(request)
            except Exception as exc:
                log_exception(
                    logger,
                    "web.request.failed",
                    "HTTP request failed before authentication was required",
                    error=exc,
                    method=request.method,
                    request_path=request.url.path,
                    status_code=500,
                    client_ip=request.client.host if request.client else "",
                )
                response = _internal_api_error_response(request)
                if response is not None:
                    return response
                raise
            _log_web_response(request, response.status_code, start_time, logger=logger)
            return response

        if request.url.path.startswith(("/static/", "/logo/")):
            return await call_next(request)

        provided_token = _extract_request_token(request)
        if not _auth_token_matches(provided_token, expected_token):
            response = auth_required_response(request)
            log_event(
                logger,
                logging.WARNING,
                "web.auth.rejected",
                "Rejected request with a missing or invalid auth token",
                method=request.method,
                request_path=request.url.path,
                status_code=response.status_code,
                client_ip=request.client.host if request.client else "",
            )
            _log_web_response(request, response.status_code, start_time, logger=logger)
            return response

        try:
            response = await call_next(request)
        except Exception as exc:
            log_exception(
                logger,
                "web.request.failed",
                "HTTP request failed",
                error=exc,
                method=request.method,
                request_path=request.url.path,
                status_code=500,
                client_ip=request.client.host if request.client else "",
            )
            response = _internal_api_error_response(request)
            if response is not None:
                return response
            raise
        if request.cookies.get(APP_AUTH_COOKIE) != expected_token:
            response.set_cookie(AUTH_COOKIE_NAME, expected_token, httponly=True, samesite="lax")
        _log_web_response(request, response.status_code, start_time, logger=logger)
        return response


def _auth_token_matches(provided_token: str | None, expected_token: object) -> bool:
    expected = str(expected_token or "")
    provided = str(provided_token or "")
    return bool(expected and provided) and hmac.compare_digest(provided, expected)


def _internal_api_error_response(request: Request) -> Response | None:
    if not request.url.path.startswith("/api/"):
        return None
    return JSONResponse({"error": INTERNAL_API_ERROR_MESSAGE}, status_code=500)


def _log_web_response(request: Request, status_code: int, started_at: float, *, logger: logging.Logger) -> None:
    path = request.url.path
    if path.startswith(("/static/", "/logo/")):
        return
    level = logging.ERROR if status_code >= 500 else (logging.WARNING if status_code >= 400 else logging.INFO)
    event = "web.request.failed" if status_code >= 500 else ("web.request.rejected" if status_code >= 400 else "web.request.completed")
    log_event(
        logger,
        level,
        event,
        "HTTP request completed",
        method=request.method,
        request_path=path,
        status_code=status_code,
        duration_ms=int((time.perf_counter() - started_at) * 1000),
        client_ip=request.client.host if request.client else "",
    )
