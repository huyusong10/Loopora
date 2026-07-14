from __future__ import annotations

import json
import logging
import time
from collections.abc import Mapping
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.types import ASGIApp, Receive, Scope, Send

from loopora.branding import APP_NAME
from loopora.diagnostics import get_logger, log_event
from loopora.service import LooporaError, create_service
from loopora.system_dialogs import pick_directory, pick_file, pick_save_file, reveal_path
from loopora.web_auth_middleware import install_auth_middleware
from loopora.web_project_scope import project_scope_template_context
from loopora.web_request_context import (
    _build_access_state,
    _is_loopback_host,
    _preferred_locale_from_accept_language,
    _preferred_request_locale,
)
from loopora.web_route_context_base import WebRouteDependencies
from loopora.web_routes import register_web_routes
from loopora.web_start_context import request_workdir_context
from loopora.web_start_context import request_project_scope_href
from loopora.web_start_context import support_context_href
from loopora.web_start_context import workdir_context_href
from loopora.web_start_context import workdir_context_preserving_href
from loopora.web_streaming import parse_sse_last_event_id
from loopora.web_url_utils import safe_local_return_path
from loopora.web_url_utils import with_query_params
from loopora.workdir_inputs import restricted_workdir_scope, same_workdir_identity, workdir_path_state

logger = get_logger(__name__)

STATIC_STYLE_LAYERS = (
    "styles/theme.css",
    "styles/base.css",
    "styles/layout.css",
    "styles/components.css",
    "styles/pages.css",
    "styles/legacy.css",
    "app.css",
)

__all__ = [
    "_is_loopback_host",
    "_preferred_locale_from_accept_language",
    "build_app",
]


def build_app(  # noqa: PLR0913 - Web app construction keeps explicit startup/auth/bind controls.
    service=None,
    *,
    bind_host: str = "127.0.0.1",
    bind_port: int = 8742,
    auth_token: str | None = None,
    allow_unsafe_open: bool = False,
    startup_workdir: str | None = None,
    demo_mode: bool = False,
    demo_evidence_path: str = "",
    demo_playground_workdir: str = "",
    demo_workdir_root: str = "",
    demo_real_task_command: str = "",
) -> FastAPI:
    access_state = _build_access_state(bind_host=bind_host, bind_port=bind_port, auth_token=auth_token)
    _validate_remote_access(access_state, allow_unsafe_open=allow_unsafe_open)
    app = FastAPI(title=APP_NAME)
    app.state.service = service or create_service()
    app.state.access_state = access_state
    app.state.startup_workdir = str(startup_workdir or "").strip()
    app.state.demo_mode = bool(demo_mode)
    app.state.demo_evidence_path = safe_local_return_path(demo_evidence_path) or ""
    app.state.demo_playground_workdir = str(demo_playground_workdir or "").strip()
    app.state.demo_workdir_root = _validate_demo_workdir_root(
        demo_mode=demo_mode,
        root=demo_workdir_root,
        startup_workdir=app.state.startup_workdir,
        playground_workdir=app.state.demo_playground_workdir,
    )
    app.state.demo_real_task_command = str(demo_real_task_command or "").strip() if demo_mode else ""
    if app.state.demo_workdir_root:
        app.add_middleware(_DemoWorkdirScopeMiddleware, root=app.state.demo_workdir_root)
    package_root = Path(__file__).parent
    templates = _build_templates(package_root)
    _mount_static_assets(app, package_root)
    log_event(
        logger,
        logging.INFO,
        "web.app.built",
        "Built web application instance",
        bind_host=bind_host,
        bind_port=bind_port,
        auth_enabled=bool(access_state["auth_enabled"]),
        remote_access_enabled=bool(access_state["remote_access_enabled"]),
    )
    auth_required_response = register_web_routes(
        app,
        dependencies=_web_route_dependencies(templates, access_state),
    )
    install_auth_middleware(app, access_state, auth_required_response, logger=logger)
    return app


def _validate_remote_access(access_state: Mapping[str, object], *, allow_unsafe_open: bool) -> None:
    if access_state["remote_access_enabled"] and not access_state["auth_enabled"] and not allow_unsafe_open:
        raise LooporaError("refusing to bind a non-loopback host without protection; use --auth-token '<token>' or explicitly pass --allow-unsafe-open")


class _DemoWorkdirScopeMiddleware:
    def __init__(self, app: ASGIApp, *, root: str) -> None:
        self.app = app
        self.root = root

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        with restricted_workdir_scope(self.root):
            await self.app(scope, receive, send)


def _validate_demo_workdir_root(
    *,
    demo_mode: bool,
    root: str,
    startup_workdir: str,
    playground_workdir: str,
) -> str:
    if not demo_mode:
        return ""
    selected_root = str(root or "").strip() or str(playground_workdir or "").strip()
    try:
        resolved_root = Path(selected_root).expanduser().resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise LooporaError("demo workdir root must be an existing directory") from exc
    if not selected_root or not resolved_root.is_dir():
        raise LooporaError("demo workdir root must be an existing directory")
    for candidate in (startup_workdir, playground_workdir):
        if not candidate:
            continue
        try:
            resolved_candidate = Path(candidate).expanduser().resolve(strict=True)
        except (OSError, RuntimeError, ValueError) as exc:
            raise LooporaError("demo project directories must exist inside the isolated workspace") from exc
        if not resolved_candidate.is_dir() or not resolved_candidate.is_relative_to(resolved_root):
            raise LooporaError("demo project directories must exist inside the isolated workspace")
    return str(resolved_root)


def _build_templates(package_root: Path) -> Jinja2Templates:
    static_root = package_root / "static"
    logo_root = package_root / "assets" / "logo"
    templates = Jinja2Templates(
        directory=str(package_root / "templates"),
        context_processors=[_template_context],
    )
    templates.env.auto_reload = True

    def versioned_asset_url(*, mount_path: str, asset_root: Path, path: str) -> str:
        normalized = path.lstrip("/")
        asset_path = asset_root / normalized
        try:
            version = asset_path.stat().st_mtime_ns
        except OSError:
            version = time.time_ns()
        return f"/{mount_path}/{normalized}?v={version}"

    def static_asset_url(path: str) -> str:
        return versioned_asset_url(mount_path="static", asset_root=static_root, path=path)

    def logo_asset_url(path: str) -> str:
        return versioned_asset_url(mount_path="logo", asset_root=logo_root, path=path)

    def static_style_urls() -> list[str]:
        return [static_asset_url(path) for path in STATIC_STYLE_LAYERS]

    templates.env.globals["static_asset_url"] = static_asset_url
    templates.env.globals["logo_asset_url"] = logo_asset_url
    templates.env.globals["static_style_urls"] = static_style_urls
    templates.env.globals["workdir_context_href"] = workdir_context_href
    templates.env.globals["workdir_context_preserving_href"] = workdir_context_preserving_href
    templates.env.globals["safe_local_return_path"] = safe_local_return_path
    templates.env.globals["with_query_params"] = with_query_params
    return templates


def _mount_static_assets(app: FastAPI, package_root: Path) -> None:
    app.mount("/static", StaticFiles(directory=str(package_root / "static")), name="static")
    app.mount("/logo", StaticFiles(directory=str(package_root / "assets" / "logo")), name="logo")


def _template_context(request: Request) -> dict[str, object]:
    locale = _preferred_request_locale(request)
    demo_mode = bool(getattr(request.app.state, "demo_mode", False))
    demo_evidence_href = str(getattr(request.app.state, "demo_evidence_path", "") or "") if demo_mode else ""
    demo_playground_workdir = str(getattr(request.app.state, "demo_playground_workdir", "") or "").strip() if demo_mode else ""
    workdir_context = request_workdir_context(request)
    if demo_mode:
        workdir_context = _demo_request_workdir_context(
            request,
            workdir_context=workdir_context,
            playground_workdir=demo_playground_workdir,
        )
    demo_playground_active = bool(demo_playground_workdir and same_workdir_identity(workdir_context, demo_playground_workdir))
    demo_playground_href = with_query_params(
        "/loops/new/bundle",
        alignment_workdir=demo_playground_workdir or None,
    )
    demo_compose_href = with_query_params("/loops/new", workdir=demo_playground_workdir or None)
    demo_fit_href = with_query_params("/fit-guide", workdir=demo_playground_workdir or None)
    demo_fit_decision_href = with_query_params(
        "/fit-guide#tutorial-decision-tree-panel",
        workdir=demo_playground_workdir or None,
    )
    current_path = f"{request.url.path}?{request.url.query}" if request.url.query else request.url.path
    project_scope_context = project_scope_template_context(request, workdir_context=workdir_context)

    def scope_href(url: str) -> str:
        return request_project_scope_href(request, url, workdir_context=workdir_context)

    support_href = support_context_href(current_path, workdir_context)
    if project_scope_context["project_scope_explicit_all"]:
        support_href = request_project_scope_href(request, support_href, workdir_context=workdir_context)
    return {
        "page_locale": locale,
        "page_lang": "zh-CN" if locale == "zh" else "en",
        "current_return_to": safe_local_return_path(current_path) or request.url.path,
        "workdir_context": workdir_context,
        **project_scope_context,
        "demo_mode": demo_mode,
        "demo_evidence_href": demo_evidence_href,
        "demo_playground_href": demo_playground_href if demo_playground_workdir else "",
        "demo_playground_workdir": demo_playground_workdir,
        "demo_playground_active": demo_playground_active,
        "demo_real_task_command": str(getattr(request.app.state, "demo_real_task_command", "") or "") if demo_mode else "",
        "nav_home_href": scope_href("/"),
        "nav_bundles_href": scope_href("/bundles"),
        "nav_compose_href": demo_compose_href if demo_playground_workdir else scope_href("/loops/new"),
        "nav_web_compose_href": demo_playground_href if demo_playground_workdir else scope_href("/loops/new/bundle"),
        "nav_orchestrations_href": scope_href("/orchestrations"),
        "nav_roles_href": scope_href("/roles"),
        "nav_tutorial_href": demo_fit_href if demo_playground_workdir else scope_href("/fit-guide"),
        "nav_tutorial_fit_href": demo_fit_decision_href if demo_playground_workdir else scope_href("/fit-guide#tutorial-decision-tree-panel"),
        "nav_tools_href": scope_href("/same-agent"),
        "nav_support_href": support_href,
        "nav_manual_loop_href": scope_href("/loops/new/manual"),
        "nav_bundle_import_href": scope_href("/loops/new/manual#bundle-import-form"),
    }


def _demo_request_workdir_context(request: Request, *, workdir_context: str, playground_workdir: str) -> str:
    state = workdir_path_state(workdir_context) if workdir_context else {}
    if state.get("status") == "ready":
        return str(state["workdir"])
    fallback = playground_workdir if request.url.path.startswith("/loops/new") else str(request.app.state.startup_workdir)
    fallback_state = workdir_path_state(fallback) if fallback else {}
    return str(fallback_state.get("workdir") or "") if fallback_state.get("status") == "ready" else ""


async def _read_json_mapping(request: Request) -> Mapping[str, object]:
    try:
        payload = await request.json()
    except UnicodeDecodeError as exc:
        raise LooporaError("invalid JSON body: request body must be UTF-8 encoded") from exc
    except json.JSONDecodeError as exc:
        raise LooporaError(f"invalid JSON body: {exc.msg}") from exc
    if not isinstance(payload, Mapping):
        raise LooporaError("request body must be a JSON object")
    return payload


def _web_route_dependencies(
    templates: Jinja2Templates,
    access_state: Mapping[str, object],
) -> WebRouteDependencies:
    return WebRouteDependencies(
        templates=templates,
        access_state=access_state,
        logger=logger,
        read_json_mapping=_read_json_mapping,
        resolve_stream_after_id=_resolve_stream_after_id,
        pick_directory_dialog=lambda start_path=None: pick_directory(start_path),
        pick_file_dialog=lambda start_path=None: pick_file(start_path),
        pick_save_file_dialog=lambda start_path=None, **kwargs: pick_save_file(start_path, **kwargs),
        reveal_path_callback=lambda target: reveal_path(target),  # noqa: PLW0108 - keep late binding for host shortcut overrides.
    )


def _resolve_stream_after_id(request: Request, *, run_id: str, after_id: int, latest_event_id: int) -> int:
    last_event_header = str(request.headers.get("last-event-id", "")).strip()
    if not last_event_header:
        return after_id
    parsed_header = parse_sse_last_event_id(last_event_header)
    if parsed_header is None or parsed_header > latest_event_id:
        log_event(
            logger,
            logging.WARNING,
            "web.run_stream.resume_cursor_invalid",
            "Ignored invalid or out-of-range SSE resume cursor and kept the request cursor",
            run_id=run_id,
            after_id=after_id,
            latest_event_id=latest_event_id,
            invalid_last_event_id=last_event_header,
        )
        return after_id
    return max(after_id, parsed_header)
