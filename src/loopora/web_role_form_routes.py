from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from loopora.service import LooporaError
from loopora.web_role_inputs import (
    _normalize_role_definition_form,
    _role_definition_payload_from_mapping,
)
from loopora.web_route_context import WebRouteContext
from loopora.web_url_utils import safe_local_return_path, with_query_params


def register_role_form_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/roles/new")
    async def create_role_definition_from_form(request: Request):
        form = await request.form()
        values = _normalize_role_definition_form(form)
        try:
            role_definition = ctx.svc().create_role_definition(**_role_definition_payload_from_mapping(form))
            return RedirectResponse(url=f"/roles/{role_definition['id']}/edit?saved=1", status_code=303)
        except (LooporaError, FileExistsError, OSError, ValueError) as exc:
            return ctx.render_new_role_definition(request, values=values, form_error=str(exc))

    @app.post("/roles/{role_definition_id}/edit")
    async def update_role_definition_from_form(request: Request, role_definition_id: str):
        form = await request.form()
        values = _normalize_role_definition_form(form)
        role_definition = ctx.svc().get_role_definition(role_definition_id)
        return_to = safe_local_return_path(request.query_params.get("return_to", ""))
        try:
            if role_definition.get("source") == "builtin":
                created = ctx.svc().create_role_definition(**_role_definition_payload_from_mapping(form))
                return RedirectResponse(url=f"/roles/{created['id']}/edit?saved=1", status_code=303)
            updated = ctx.svc().update_role_definition(role_definition_id, **_role_definition_payload_from_mapping(form))
            if return_to:
                return RedirectResponse(
                    url=with_query_params(return_to, surface_updated=f"role:{updated['id']}"),
                    status_code=303,
                )
            return RedirectResponse(url=f"/roles/{updated['id']}/edit?saved=1", status_code=303)
        except (LooporaError, FileExistsError, OSError, ValueError) as exc:
            return ctx.render_new_role_definition(
                request,
                values=values,
                form_error=str(exc),
                role_definition=role_definition,
            )
