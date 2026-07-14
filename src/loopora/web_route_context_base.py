from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from loopora.branding import APP_AUTH_COOKIE
from loopora.token_security import token_matches
from loopora.web_request_context import _request_wants_json
from loopora.web_url_utils import safe_local_return_path


StreamAfterResolver = Callable[[Request], int] | Callable[..., int]
SaveFilePicker = Callable[[str | None], str | None] | Callable[..., str | None]


@dataclass(frozen=True, kw_only=True)
class WebRouteDependencies:
    templates: Jinja2Templates
    access_state: Mapping[str, object]
    logger: logging.Logger
    read_json_mapping: Callable[[Request], Awaitable[Mapping[str, object]]]
    resolve_stream_after_id: StreamAfterResolver
    pick_directory_dialog: Callable[[str | None], str | None]
    pick_file_dialog: Callable[[str | None], str | None]
    pick_save_file_dialog: SaveFilePicker
    reveal_path_callback: Callable[[str], str]


def _required_web_route_dependency(fields: dict[str, object], field: str) -> object:
    try:
        return fields.pop(field)
    except KeyError as exc:
        raise TypeError(f"missing web route dependency: {field}") from exc


def web_route_dependencies_from_args(
    dependencies: WebRouteDependencies | None,
    raw_dependencies: dict[str, object],
) -> WebRouteDependencies:
    if dependencies is not None:
        if raw_dependencies:
            raise TypeError("web route dependencies object cannot be combined with keyword fields")
        return dependencies

    fields = dict(raw_dependencies)
    dependency_set = WebRouteDependencies(
        templates=_required_web_route_dependency(fields, "templates"),
        access_state=_required_web_route_dependency(fields, "access_state"),
        logger=_required_web_route_dependency(fields, "logger"),
        read_json_mapping=_required_web_route_dependency(fields, "read_json_mapping"),
        resolve_stream_after_id=_required_web_route_dependency(fields, "resolve_stream_after_id"),
        pick_directory_dialog=_required_web_route_dependency(fields, "pick_directory_dialog"),
        pick_file_dialog=_required_web_route_dependency(fields, "pick_file_dialog"),
        pick_save_file_dialog=_required_web_route_dependency(fields, "pick_save_file_dialog"),
        reveal_path_callback=_required_web_route_dependency(fields, "reveal_path_callback"),
    )
    if fields:
        unexpected_fields = ", ".join(sorted(fields))
        raise TypeError(f"unexpected web route dependencies: {unexpected_fields}")
    return dependency_set


class WebRouteContextBase:
    def __init__(
        self,
        app: FastAPI,
        dependencies: WebRouteDependencies | None = None,
        **raw_dependencies: object,
    ) -> None:
        dependencies = web_route_dependencies_from_args(dependencies, raw_dependencies)
        self.app = app
        self.templates = dependencies.templates
        self.access_state = dependencies.access_state
        self.logger = dependencies.logger
        self.read_json_mapping = dependencies.read_json_mapping
        self.resolve_stream_after_id = dependencies.resolve_stream_after_id
        self.pick_directory_dialog = dependencies.pick_directory_dialog
        self.pick_file_dialog = dependencies.pick_file_dialog
        self.pick_save_file_dialog = dependencies.pick_save_file_dialog
        self.reveal_path_callback = dependencies.reveal_path_callback

    def svc(self):
        return self.app.state.service

    @staticmethod
    def json_error(message: str, status_code: int = 400) -> JSONResponse:
        return JSONResponse({"error": message}, status_code=status_code)

    @staticmethod
    def error_status_code(exc: BaseException) -> int:
        if isinstance(exc, FileExistsError):
            return 409
        return int(getattr(exc, "status_code", 400) or 400)

    def json_error_from_exception(self, exc: BaseException) -> JSONResponse:
        return self.json_error(str(exc), status_code=self.error_status_code(exc))

    def render_auth_form(
        self,
        request: Request,
        *,
        return_to: str,
        status_code: int,
        token_invalid: bool = False,
    ) -> HTMLResponse:
        return HTMLResponse(
            self.templates.TemplateResponse(
                request,
                "auth.html",
                {
                    "request": request,
                    "return_to": return_to,
                    "token_invalid": token_invalid,
                },
            ).body.decode(),
            status_code=status_code,
            headers={"WWW-Authenticate": "Bearer"},
        )

    def render_auth_required(self, request: Request) -> HTMLResponse:
        return self.render_auth_form(
            request,
            return_to=_safe_request_return_path(request),
            status_code=401,
        )

    async def submit_auth_token(self, request: Request) -> Response:
        form = _urlencoded_form(await request.body())
        return_to = safe_local_return_path(_first_form_value(form, "return_to")) or "/"
        expected_token = self.access_state.get("auth_token")
        if not expected_token:
            return RedirectResponse(url=return_to, status_code=303)

        if not token_matches(_first_form_value(form, "token"), expected_token):
            return self.render_auth_form(
                request,
                return_to=return_to,
                status_code=401,
                token_invalid=True,
            )

        response = RedirectResponse(url=return_to, status_code=303)
        response.set_cookie(APP_AUTH_COOKIE, str(expected_token), httponly=True, samesite="lax")
        return response

    def auth_required_response(self, request: Request) -> Response:
        if _request_wants_json(request):
            return JSONResponse(
                {
                    "error": "auth token required",
                    "hint": "open the auth form or send Authorization: Bearer <your-token>",
                },
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
        return self.render_auth_required(request)


def _safe_request_return_path(request: Request) -> str:
    target = request.url.path
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return safe_local_return_path(target) or "/"


def _urlencoded_form(body: bytes) -> Mapping[str, list[str]]:
    return parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True)


def _first_form_value(form: Mapping[str, list[str]], key: str) -> str:
    values = form.get(key) or []
    return str(values[0] if values else "").strip()
