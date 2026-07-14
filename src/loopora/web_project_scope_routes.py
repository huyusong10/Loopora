from __future__ import annotations

from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from loopora.settings import remember_recent_workdir
from loopora.web_project_scope import safe_project_scope_return_path
from loopora.web_route_context import WebRouteContext
from loopora.web_start_context import all_projects_scope_href
from loopora.web_start_context import safe_workdir_context
from loopora.web_start_context import workdir_context_href
from loopora.web_url_utils import with_query_params
from loopora.workdir_inputs import workdir_path_state


def register_project_scope_routes(app: FastAPI, ctx: WebRouteContext) -> None:  # noqa: ARG001 - route parity
    @app.post("/project-scope")
    async def select_project_scope(request: Request) -> RedirectResponse:
        form = parse_qs((await request.body()).decode("utf-8", errors="replace"), keep_blank_values=True)
        workdir = str((form.get("workdir") or [""])[0] or "").strip()
        return_to = safe_project_scope_return_path((form.get("return_to") or [""])[0])
        if not workdir:
            return _project_scope_redirect(feedback="all", return_to=return_to)

        safe_workdir = safe_workdir_context(workdir)
        target_state = workdir_path_state(safe_workdir) if safe_workdir else {}
        target_workdir = str(target_state.get("workdir") or "").strip()
        if target_state.get("status") != "ready" or not target_workdir:
            return _project_scope_redirect(feedback="target_unavailable", return_to=return_to)

        remember_recent_workdir(target_workdir)
        return _project_scope_redirect(workdir=target_workdir, feedback="selected", return_to=return_to)


def _project_scope_redirect(*, workdir: str = "", feedback: str, return_to: str = "/") -> RedirectResponse:
    target = workdir_context_href(return_to, workdir) if workdir else all_projects_scope_href(return_to)
    return RedirectResponse(
        url=with_query_params(target, project_scope_feedback=feedback),
        status_code=303,
    )
