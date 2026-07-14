from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from urllib.parse import parse_qs, parse_qsl, unquote, urlencode, urlsplit, urlunsplit

from fastapi import Request

from loopora.service_types import LooporaError
from loopora.web_url_utils import safe_local_return_path
from loopora.web_url_utils import with_query_params

PROJECT_SCOPE_QUERY_PARAM = "project_scope"
ALL_PROJECTS_SCOPE = "all"
SUPPORT_RETURN_QUERY_KEYS = {
    "alignment_session_id",
    "alignment_workdir",
    "panel",
    PROJECT_SCOPE_QUERY_PARAM,
    "tab",
    "workdir",
}


def request_workdir_context(request: Request) -> str:
    explicit_workdir = str(
        request.query_params.get("workdir") or request.query_params.get("alignment_workdir") or ""
    ).strip()
    if explicit_workdir:
        return safe_workdir_context(explicit_workdir)

    session_id = str(request.query_params.get("alignment_session_id") or "").strip()
    if session_id:
        service = getattr(request.app.state, "service", None)
        get_alignment_session = getattr(service, "get_alignment_session", None)
        if callable(get_alignment_session):
            try:
                session = get_alignment_session(session_id)
            except LooporaError:
                session = None
            if isinstance(session, Mapping):
                session_workdir = str(session.get("workdir") or "").strip()
                if session_workdir:
                    return safe_workdir_context(session_workdir)

    path_workdir = _path_entity_workdir_context(request, request.url.path)
    if path_workdir:
        return path_workdir
    if request_all_projects_scope(request):
        return ""
    return _request_return_to_workdir_context(request) or _startup_workdir_context(request)


def request_all_projects_scope(request: Request) -> bool:
    return str(request.query_params.get(PROJECT_SCOPE_QUERY_PARAM) or "").strip() == ALL_PROJECTS_SCOPE


def request_all_projects_scope_href(request: Request, url: str) -> str:
    if _startup_workdir_context(request) or request_all_projects_scope(request):
        return all_projects_scope_href(url)
    return str(url or "")


def request_project_scope_href(request: Request, url: str, *, workdir_context: str | None = None) -> str:
    context = request_workdir_context(request) if workdir_context is None else safe_workdir_context(workdir_context)
    if context:
        return workdir_context_href(url, context)
    if request_all_projects_scope(request):
        return all_projects_scope_href(url)
    return str(url or "")


def _startup_workdir_context(request: Request) -> str:
    return safe_workdir_context(getattr(request.app.state, "startup_workdir", "") or "")


def _request_return_to_workdir_context(request: Request) -> str:
    return_to = safe_local_return_path(request.query_params.get("return_to", ""))
    if not return_to:
        return ""
    parts = urlsplit(return_to)
    query = parse_qs(parts.query, keep_blank_values=True)
    explicit_workdir = str((query.get("workdir") or query.get("alignment_workdir") or [""])[0] or "").strip()
    if explicit_workdir:
        return safe_workdir_context(explicit_workdir)
    return _path_entity_workdir_context(request, parts.path)


def _path_entity_workdir_context(request: Request, path: str) -> str:
    service = getattr(request.app.state, "service", None)
    if service is None:
        return ""
    entity_lookup = _path_entity_lookup(path)
    if entity_lookup is None:
        return ""
    getter_name, entity_id = entity_lookup
    getter = getattr(service, getter_name, None)
    if not callable(getter):
        return ""
    try:
        entity = getter(entity_id)
    except LooporaError:
        return ""
    if not isinstance(entity, Mapping):
        return ""
    return safe_workdir_context(entity.get("workdir") or "")


def _path_entity_lookup(path: str) -> tuple[str, str] | None:
    segments = [unquote(segment) for segment in str(path or "").split("/") if segment]
    if len(segments) < 2:
        return None
    entity_type, entity_id = segments[0], segments[1]
    if entity_type == "loops" and entity_id == "new":
        return None
    entity_getters = {
        "bundles": "get_bundle",
        "loops": "get_loop",
        "runs": "get_run",
    }
    getter_name = entity_getters.get(entity_type)
    if not getter_name:
        return None
    return getter_name, entity_id


def workdir_context_href(url: str, workdir_context: str) -> str:
    target = str(url or "").strip()
    safe_context = safe_workdir_context(workdir_context)
    if not target:
        return target
    parts = urlsplit(target)
    query = parse_qs(parts.query, keep_blank_values=True)
    existing_context = str((query.get("workdir") or query.get("alignment_workdir") or [""])[0] or "").strip()
    if existing_context:
        if safe_workdir_context(existing_context):
            return _without_project_scope(target)
        target = _without_workdir_context(target)
    if not safe_context:
        return target
    return with_query_params(_without_project_scope(target), workdir=safe_context)


def all_projects_scope_href(url: str) -> str:
    target = _without_project_scope(_without_workdir_context(str(url or "")))
    return with_query_params(target, **{PROJECT_SCOPE_QUERY_PARAM: ALL_PROJECTS_SCOPE})


def support_context_href(current_path: str, workdir_context: str) -> str:
    support_href = workdir_context_href("/support", workdir_context)
    return_to = _support_return_path(current_path, workdir_context)
    if not return_to:
        return support_href
    return with_query_params(support_href, return_to=return_to)


def _support_return_path(current_path: str, workdir_context: str) -> str:
    return_to = safe_local_return_path(current_path)
    if not return_to:
        return ""
    parts = urlsplit(return_to)
    if parts.path in {"/", "/support"}:
        return ""
    query_items = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key in SUPPORT_RETURN_QUERY_KEYS
    ]
    stable_return_to = urlunsplit(("", "", parts.path or "/", urlencode(query_items), parts.fragment))
    return workdir_context_return_to(stable_return_to, workdir_context)


def resource_workdir_context(*resources: Mapping[str, object] | None, fallback: str = "") -> str:
    for resource in resources:
        if not isinstance(resource, Mapping):
            continue
        workdir = safe_workdir_context(resource.get("workdir") or "")
        if workdir:
            return workdir
    return safe_workdir_context(fallback)


def resource_workdir_context_href(
    url: str,
    *resources: Mapping[str, object] | None,
    fallback_workdir: str = "",
) -> str:
    return workdir_context_href(url, resource_workdir_context(*resources, fallback=fallback_workdir))


def workdir_context_preserving_href(url: str, workdir_context: str) -> str:
    return workdir_context_href(url, workdir_context)


def request_workdir_context_href(request: Request, url: str) -> str:
    return workdir_context_href(url, request_workdir_context(request))


def request_resource_workdir_context_href(
    request: Request,
    url: str,
    *resources: Mapping[str, object] | None,
) -> str:
    return resource_workdir_context_href(url, *resources, fallback_workdir=request_workdir_context(request))


def workdir_context_return_to(return_to: str, workdir_context: str) -> str:
    return workdir_context_preserving_href(return_to, workdir_context)


def request_workdir_context_return_to(request: Request, return_to: str) -> str:
    return workdir_context_return_to(return_to, request_workdir_context(request))


def _without_workdir_context(url: str) -> str:
    parts = urlsplit(str(url or ""))
    query_items = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key not in {"workdir", "alignment_workdir"}
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query_items), parts.fragment))


def _without_project_scope(url: str) -> str:
    parts = urlsplit(str(url or ""))
    query_items = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key != PROJECT_SCOPE_QUERY_PARAM
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query_items), parts.fragment))


def safe_workdir_context(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        return raw if Path(raw).expanduser().is_absolute() else ""
    except (OSError, RuntimeError, ValueError):
        return ""
