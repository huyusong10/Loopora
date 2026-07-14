from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import Request

from loopora.web_home_attention import home_loop_sections
from loopora.web_start_context import request_all_projects_scope_href
from loopora.web_start_context import request_project_scope_href
from loopora.web_start_context import request_workdir_context
from loopora.web_start_context import workdir_context_href
from loopora.web_url_utils import safe_local_return_path
from loopora.web_url_utils import with_query_params


TRANSIENT_LOOP_CREATE_RETURN_QUERY_KEYS = {"surface_updated"}


@dataclass(frozen=True, kw_only=True)
class NewLoopPageState:
    page_mode: str = "choice"
    values: Mapping[str, object] | None = None
    form_error: str | None = None
    form_recovery: Mapping[str, object] | None = None
    import_values: Mapping[str, object] | None = None
    import_error: str | None = None
    import_recovery: Mapping[str, object] | None = None


def new_loop_page_state_from_args(
    state: NewLoopPageState | None,
    raw_state: dict[str, object],
) -> NewLoopPageState:
    if state is not None:
        if raw_state:
            raise TypeError("new loop page state object cannot be combined with keyword fields")
        return state

    fields = dict(raw_state)
    page_state = NewLoopPageState(
        page_mode=fields.pop("page_mode", "choice"),
        values=fields.pop("values", None),
        form_error=fields.pop("form_error", None),
        form_recovery=fields.pop("form_recovery", None),
        import_values=fields.pop("import_values", None),
        import_error=fields.pop("import_error", None),
        import_recovery=fields.pop("import_recovery", None),
    )
    if fields:
        unexpected_fields = ", ".join(sorted(fields))
        raise TypeError(f"unexpected new loop page state fields: {unexpected_fields}")
    return page_state


def loop_create_page_context(
    request: Request,
    service,
    *,
    page_mode: str,
) -> dict[str, object]:
    workdir_context = request_workdir_context(request)
    existing_work_sections: Mapping[str, list[Mapping[str, object]]] = (
        home_loop_sections(service, workdir_context=workdir_context)
        if page_mode == "choice"
        else {"loops": [], "active_loops": [], "recent_loops": []}
    )
    all_existing_work_sections = (
        home_loop_sections(service)
        if page_mode == "choice" and workdir_context
        else existing_work_sections
    )
    return {
        "workdir_context": workdir_context,
        "asset_return_to": _current_loop_create_return_path(request, page_mode=page_mode),
        "create_choice_links": _create_choice_links(request),
        "create_choice_existing_work": _create_choice_existing_work_state(
            existing_work_sections,
            workdir_context=workdir_context,
            all_sections=all_existing_work_sections,
            all_work_href=request_all_projects_scope_href(request, "/"),
        ),
    }


def _create_choice_links(request: Request) -> dict[str, str]:
    workdir = request_workdir_context(request)
    if not workdir:
        return {
            "agent": request_project_scope_href(request, "/same-agent", workdir_context=""),
            "bundle": request_project_scope_href(request, "/loops/new/bundle", workdir_context=""),
            "existing": request_project_scope_href(request, "/#activity", workdir_context=""),
            "existing_attention": request_project_scope_href(request, "/#activity", workdir_context=""),
            "existing_saved": request_project_scope_href(request, "/#saved-loops", workdir_context=""),
            "import": request_project_scope_href(
                request,
                "/loops/new/manual#bundle-import-form",
                workdir_context="",
            ),
            "manual": request_project_scope_href(
                request,
                "/loops/new/manual#manual-loop-form",
                workdir_context="",
            ),
        }
    return {
        "agent": with_query_params("/same-agent", workdir=workdir),
        "bundle": with_query_params("/loops/new/bundle", alignment_workdir=workdir),
        "existing": with_query_params("/#activity", workdir=workdir),
        "existing_attention": with_query_params("/#activity", workdir=workdir),
        "existing_saved": with_query_params("/#saved-loops", workdir=workdir),
        "import": with_query_params("/loops/new/manual#bundle-import-form", workdir=workdir),
        "manual": with_query_params("/loops/new/manual#manual-loop-form", workdir=workdir),
    }


def _create_choice_existing_work_state(
    sections: Mapping[str, list[Mapping[str, object]]],
    *,
    workdir_context: str = "",
    all_sections: Mapping[str, list[Mapping[str, object]]] | None = None,
    all_work_href: str = "/",
) -> dict[str, object]:
    loops = list(sections.get("loops") or [])
    active_items = list(sections.get("active_loops") or [])
    recent_loops = list(sections.get("recent_loops") or [])
    all_sections = all_sections or sections
    all_loops = list(all_sections.get("loops") or [])
    all_active_items = list(all_sections.get("active_loops") or [])
    all_recent_loops = list(all_sections.get("recent_loops") or [])
    primary_activity = active_items[0] if active_items else {}
    if not primary_activity and recent_loops:
        primary_activity = recent_loops[0]
    primary_saved_loop = loops[0] if len(loops) == 1 else {}
    active_alignment_count = sum(
        1 for item in active_items if str(item.get("source_kind") or "").strip() == "alignment_session"
    )
    has_activity = bool(active_items) or bool(recent_loops)
    has_saved_loops = bool(loops)
    scoped_activity_count = len(active_items) + len(recent_loops)
    all_activity_count = len(all_active_items) + len(all_recent_loops)
    hidden_activity_count = max(0, all_activity_count - scoped_activity_count)
    hidden_loop_count = max(0, len(all_loops) - len(loops))
    return {
        "has_work": has_activity or has_saved_loops,
        "has_activity": has_activity,
        "has_saved_loops": has_saved_loops,
        "loop_count": len(loops),
        "all_loop_count": len(all_loops),
        "hidden_loop_count": hidden_loop_count,
        "all_activity_count": all_activity_count,
        "hidden_activity_count": hidden_activity_count,
        "has_hidden_work": bool(workdir_context and (hidden_activity_count or hidden_loop_count)),
        "all_work_href": all_work_href,
        "active_attention_count": len(active_items),
        "active_alignment_session_count": active_alignment_count,
        "primary_activity_action_kind": str(primary_activity.get("attention_action_kind") or ""),
        "primary_activity_action_zh": str(primary_activity.get("attention_action_zh") or ""),
        "primary_activity_action_en": str(primary_activity.get("attention_action_en") or ""),
        "primary_activity_href": _create_choice_primary_activity_href(
            primary_activity,
            workdir_context=workdir_context,
        ),
        "primary_activity_source_kind": str(primary_activity.get("source_kind") or ""),
        "recent_loop_count": len(recent_loops),
        "primary_saved_loop_href": _create_choice_primary_saved_loop_href(
            primary_saved_loop,
            workdir_context=workdir_context,
        ),
    }


def _create_choice_primary_activity_href(
    primary_activity: Mapping[str, object],
    *,
    workdir_context: str = "",
) -> str:
    target = str(primary_activity.get("card_href") or "").strip()
    if not target:
        return ""
    return workdir_context_href(target, workdir_context)


def _create_choice_primary_saved_loop_href(
    primary_saved_loop: Mapping[str, object],
    *,
    workdir_context: str = "",
) -> str:
    target = str(primary_saved_loop.get("detail_href") or primary_saved_loop.get("card_href") or "").strip()
    if not target:
        return ""
    return workdir_context_href(target, workdir_context)


def _current_loop_create_return_path(request: Request, *, page_mode: str) -> str:
    query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(request.url.query, keep_blank_values=True)
            if key not in TRANSIENT_LOOP_CREATE_RETURN_QUERY_KEYS
        ]
    )
    local_path = safe_local_return_path(f"{request.url.path}?{query}" if query else request.url.path) or "/loops/new"
    if page_mode == "manual":
        parts = urlsplit(local_path)
        return urlunsplit(("", "", parts.path or "/loops/new/manual", parts.query, "manual-loop-form"))
    return local_path
