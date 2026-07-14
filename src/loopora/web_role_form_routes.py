from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from loopora.service import LooporaError
from loopora.asset_errors import asset_mutation_error_message
from loopora.web_asset_validation_recovery import web_asset_field_errors
from loopora.web_role_inputs import (
    _normalize_role_definition_form,
    _role_definition_payload_from_mapping,
)
from loopora.web_route_context import WebRouteContext
from loopora.web_start_context import request_workdir_context
from loopora.web_start_context import request_workdir_context_return_to
from loopora.web_url_utils import safe_local_return_path, with_query_params


def register_role_form_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/roles/new")
    async def create_role_definition_from_form(request: Request):
        form = await request.form()
        values = _normalize_role_definition_form(form)
        return_to = request_workdir_context_return_to(
            request,
            safe_local_return_path(request.query_params.get("return_to", "")),
        )
        try:
            role_definition = ctx.svc().create_role_definition(**_role_definition_payload_from_mapping(form))
            if return_to:
                return RedirectResponse(
                    url=with_query_params(return_to, surface_updated=f"role:{role_definition['id']}"),
                    status_code=303,
                )
            return RedirectResponse(url=_saved_role_definition_url(request, role_definition["id"]), status_code=303)
        except (LooporaError, FileExistsError, OSError, ValueError) as exc:
            return ctx.render_new_role_definition(
                request,
                values=values,
                form_error=asset_mutation_error_message(exc, asset_label="role definition"),
                form_field_errors=web_asset_field_errors(exc, asset_label="role definition"),
            )

    @app.post("/roles/{role_definition_id}/edit")
    async def update_role_definition_from_form(request: Request, role_definition_id: str):
        form = await request.form()
        values = _normalize_role_definition_form(form)
        role_definition = ctx.svc().get_role_definition(role_definition_id)
        return_to = request_workdir_context_return_to(
            request,
            safe_local_return_path(request.query_params.get("return_to", "")),
        )
        try:
            if role_definition.get("source") == "builtin":
                created = ctx.svc().create_role_definition(**_role_definition_payload_from_mapping(form))
                if return_to:
                    return RedirectResponse(
                        url=with_query_params(return_to, surface_updated=f"role:{created['id']}"),
                        status_code=303,
                    )
                return RedirectResponse(url=_saved_role_definition_url(request, created["id"]), status_code=303)
            updated = ctx.svc().update_role_definition(role_definition_id, **_role_definition_payload_from_mapping(form))
            if return_to:
                return RedirectResponse(
                    url=with_query_params(return_to, surface_updated=f"role:{updated['id']}"),
                    status_code=303,
                )
            return RedirectResponse(url=_saved_role_definition_url(request, updated["id"]), status_code=303)
        except (LooporaError, FileExistsError, OSError, ValueError) as exc:
            return ctx.render_new_role_definition(
                request,
                values=values,
                form_error=asset_mutation_error_message(exc, asset_label="role definition"),
                form_field_errors=web_asset_field_errors(exc, asset_label="role definition"),
                role_definition=role_definition,
            )


def _saved_role_definition_url(request: Request, role_definition_id: object) -> str:
    return with_query_params(
        f"/roles/{role_definition_id}/edit",
        workdir=request_workdir_context(request) or None,
        saved="1",
    )
