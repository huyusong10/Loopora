from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable, Mapping
from html import escape

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from loopora.branding import APP_AUTH_COOKIE
from loopora.diagnostics import log_event, log_exception
from loopora.token_security import token_matches
from loopora.web_request_context import _extract_request_token, _request_wants_json
from loopora.web_start_context import request_workdir_context, support_context_href
from loopora.web_url_utils import redirect_query_requires_safe_local_cleanup, safe_local_return_path, with_query_params

AUTH_COOKIE_NAME = APP_AUTH_COOKIE
AUTH_FORM_PATH = "/auth/token"
INTERNAL_API_ERROR_MESSAGE = "internal server error"
INTERNAL_PAGE_ERROR_MESSAGE = "Loopora could not render this page"


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
            response = await _call_next_or_internal_error(
                request,
                call_next,
                logger=logger,
                failure_message="HTTP request failed before authentication was required",
            )
            _log_web_response(request, response.status_code, start_time, logger=logger)
            return response

        if request.url.path.startswith(("/static/", "/logo/")):
            return await call_next(request)
        if _is_auth_form_submission(request):
            response = await _call_next_or_internal_error(
                request,
                call_next,
                logger=logger,
                failure_message="HTTP auth form submission failed",
            )
            _log_web_response(request, response.status_code, start_time, logger=logger)
            return response

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

        response = await _call_next_or_internal_error(
            request,
            call_next,
            logger=logger,
            failure_message="HTTP request failed",
        )
        response = _with_authenticated_query_token_cleanup(request, response)
        if request.cookies.get(APP_AUTH_COOKIE) != expected_token:
            response.set_cookie(AUTH_COOKIE_NAME, expected_token, httponly=True, samesite="lax")
        _log_web_response(request, response.status_code, start_time, logger=logger)
        return response


def _auth_token_matches(provided_token: str | None, expected_token: object) -> bool:
    return token_matches(provided_token, expected_token)


async def _call_next_or_internal_error(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
    *,
    logger: logging.Logger,
    failure_message: str,
) -> Response:
    try:
        return await call_next(request)
    except Exception as exc:  # noqa: BLE001 - request boundary must convert unknown failures to stable responses.
        log_exception(
            logger,
            "web.request.failed",
            failure_message,
            error=exc,
            method=request.method,
            request_path=request.url.path,
            status_code=500,
            client_ip=request.client.host if request.client else "",
        )
        return _internal_error_response(request)


def _is_auth_form_submission(request: Request) -> bool:
    return request.method == "POST" and request.url.path == AUTH_FORM_PATH


def _with_authenticated_query_token_cleanup(request: Request, response: Response) -> Response:
    if not _should_clean_authenticated_query_token(request):
        return response
    if 300 <= response.status_code < 400:
        return _redirect_response_with_token_stripped_location(response)
    redirect_target = _safe_token_stripped_request_target(request)
    if not redirect_target:
        return response
    return RedirectResponse(url=redirect_target, status_code=303)


def _should_clean_authenticated_query_token(request: Request) -> bool:
    if request.method != "GET" or request.url.path.startswith("/api/"):
        return False
    return redirect_query_requires_safe_local_cleanup(request.url.query)


def _redirect_response_with_token_stripped_location(response: Response) -> Response:
    location = response.headers.get("location", "")
    if location:
        response.headers["location"] = safe_local_return_path(location) or "/"
    return response


def _safe_token_stripped_request_target(request: Request) -> str | None:
    target = request.url.path
    if request.url.query:
        target = f"{target}?{request.url.query}"
    redirect_target = safe_local_return_path(target)
    if not redirect_target:
        return None
    original_target = f"{request.url.path}{'?' + request.url.query if request.url.query else ''}"
    return redirect_target if redirect_target != original_target else None


def _internal_error_response(request: Request) -> Response:
    if _request_wants_json(request):
        return JSONResponse({"error": INTERNAL_API_ERROR_MESSAGE}, status_code=500)
    return HTMLResponse(_internal_page_error_html(request), status_code=500)


def _internal_support_href(request: Request) -> str:
    current_path = f"{request.url.path}?{request.url.query}" if request.url.query else request.url.path
    return support_context_href(current_path, _safe_internal_workdir_context(request))


def _internal_home_href(request: Request) -> str:
    return _internal_context_href(request, "/")


def _internal_context_href(request: Request, path: str) -> str:
    workdir = _safe_internal_workdir_context(request)
    return with_query_params(path, workdir=workdir) if workdir else path


def _safe_internal_workdir_context(request: Request) -> str:
    try:
        return request_workdir_context(request)
    except Exception:  # noqa: BLE001 - the last-resort error page must not fail while recovering context.
        return str(request.query_params.get("workdir") or request.query_params.get("alignment_workdir") or "").strip()


def _internal_page_error_html(request: Request) -> str:
    home_href = _internal_home_href(request)
    support_href = _internal_support_href(request)
    return (
        "<!doctype html>"
        '<html lang="en">'
        "<head>"
        '<meta charset="utf-8" />'
        '<meta name="viewport" content="width=device-width, initial-scale=1" />'
        f"<title>{INTERNAL_PAGE_ERROR_MESSAGE}</title>"
        "</head>"
        "<body>"
        '<main data-testid="web-error-page"><h1>'
        f"{INTERNAL_PAGE_ERROR_MESSAGE}</h1>"
        '<p data-testid="web-error-status">Status 500</p>'
        "<p>The request failed before this view could finish loading. Open Support to copy redacted evidence, then retry.</p>"
        f'<p><a href="{escape(home_href, quote=True)}" data-testid="web-error-home-link">Return to Loopora home</a></p>'
        f'<p><a href="{escape(support_href, quote=True)}" data-testid="web-error-support-link">Open Support</a></p>'
        "</main>"
        "</body>"
        "</html>"
    )


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
