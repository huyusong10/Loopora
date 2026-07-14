from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from loopora.service import LooporaError
from loopora.strategy_source import StrategySourceError
from loopora.asset_errors import asset_mutation_error_message
from loopora.web_asset_validation_recovery import web_asset_field_errors
from loopora.web_route_context import WebRouteContext
from loopora.web_start_context import request_workdir_context
from loopora.web_start_context import request_workdir_context_return_to
from loopora.web_strategy_inputs import _normalize_orchestration_form, _orchestration_payload_from_mapping
from loopora.web_url_utils import safe_local_return_path, with_query_params


def register_orchestration_form_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/orchestrations/new")
    async def create_orchestration_from_form(request: Request):
        form = await request.form()
        values = _normalize_orchestration_form(form)
        return_to = request_workdir_context_return_to(
            request,
            safe_local_return_path(request.query_params.get("return_to", "")),
        )
        try:
            orchestration = ctx.svc().create_orchestration(**_orchestration_payload_from_mapping(form, default_to_preset=False))
            if return_to:
                return RedirectResponse(url=with_query_params(return_to, surface_updated="workflow"), status_code=303)
            return RedirectResponse(url=_saved_orchestration_url(request, orchestration["id"]), status_code=303)
        except (LooporaError, StrategySourceError, FileExistsError, OSError, ValueError) as exc:
            return ctx.render_new_orchestration(
                request,
                values=values,
                form_error=asset_mutation_error_message(exc, asset_label="orchestration"),
                form_field_errors=web_asset_field_errors(exc, asset_label="orchestration"),
            )

    @app.post("/orchestrations/{orchestration_id}/edit")
    async def update_orchestration_from_form(request: Request, orchestration_id: str):
        form = await request.form()
        values = _normalize_orchestration_form(form)
        orchestration = ctx.svc().get_orchestration(orchestration_id)
        return_to = request_workdir_context_return_to(
            request,
            safe_local_return_path(request.query_params.get("return_to", "")),
        )
        try:
            if orchestration.get("source") == "builtin":
                raise LooporaError("built-in orchestrations are read-only; create a new orchestration to customize one")
            updated = ctx.svc().update_orchestration(
                orchestration_id,
                **_orchestration_payload_from_mapping(form, default_to_preset=False),
            )
            if return_to:
                return RedirectResponse(url=with_query_params(return_to, surface_updated="workflow"), status_code=303)
            return RedirectResponse(url=_saved_orchestration_url(request, updated["id"]), status_code=303)
        except (LooporaError, StrategySourceError, FileExistsError, OSError, ValueError) as exc:
            return ctx.render_new_orchestration(
                request,
                values=values,
                form_error=asset_mutation_error_message(exc, asset_label="orchestration"),
                form_field_errors=web_asset_field_errors(exc, asset_label="orchestration"),
                orchestration=orchestration,
            )


def _saved_orchestration_url(request: Request, orchestration_id: object) -> str:
    return with_query_params(
        f"/orchestrations/{orchestration_id}/edit",
        workdir=request_workdir_context(request) or None,
        saved="1",
    )
