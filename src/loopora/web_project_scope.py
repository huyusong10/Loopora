from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

from fastapi import Request

from loopora.settings import load_recent_workdirs
from loopora.web_start_context import request_all_projects_scope
from loopora.web_start_context import safe_workdir_context
from loopora.web_url_utils import safe_local_return_path
from loopora.workdir_inputs import PATH_PROBE_ERRORS, same_workdir_identity, workdir_path_state

PROJECT_SCOPE_FEEDBACK_VALUES = {"all", "selected", "target_unavailable"}
PROJECT_SCOPE_SAFE_RETURN_PATHS = {
    "/same-agent": "/same-agent",
    "/tools": "/same-agent",
}


def project_scope_template_context(request: Request, *, workdir_context: str) -> dict[str, object]:
    current = safe_workdir_context(workdir_context)
    feedback = str(request.query_params.get("project_scope_feedback") or "").strip()
    if feedback not in PROJECT_SCOPE_FEEDBACK_VALUES:
        feedback = ""
    access_state = getattr(request.app.state, "access_state", {})
    return_to = safe_project_scope_return_path(request.url.path)
    return {
        "project_scope_current_label": _project_label(current),
        "project_scope_explicit_all": bool(request_all_projects_scope(request) and not current),
        "project_scope_feedback": feedback,
        "project_scope_native_picker_enabled": bool(access_state.get("native_dialogs_enabled", False)),
        "project_scope_recent_items": _recent_project_items(current),
        "project_scope_requires_all_marker": bool(safe_workdir_context(getattr(request.app.state, "startup_workdir", "") or "")),
        "project_scope_return_to": return_to,
        "project_scope_stays_on_page": return_to != "/",
    }


def safe_project_scope_return_path(value: object) -> str:
    target = safe_local_return_path(str(value or ""))
    if not target:
        return "/"
    return PROJECT_SCOPE_SAFE_RETURN_PATHS.get(urlsplit(target).path, "/")


def _recent_project_items(current: str, *, limit: int = 5) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for candidate in load_recent_workdirs(limit=max(limit * 3, limit)):
        state = workdir_path_state(candidate)
        if state.get("status") != "ready":
            continue
        workdir = str(state.get("workdir") or "").strip()
        if not workdir or same_workdir_identity(workdir, current):
            continue
        if any(same_workdir_identity(workdir, item["workdir"]) for item in items):
            continue
        items.append({"label": _project_label(workdir), "workdir": workdir})
        if len(items) >= limit:
            break
    return items


def _project_label(workdir: str) -> str:
    value = str(workdir or "").strip()
    if not value:
        return ""
    try:
        path = Path(value)
        return path.name or path.anchor or value
    except PATH_PROBE_ERRORS:
        return value
