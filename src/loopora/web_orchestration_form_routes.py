from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from loopora.service import LooporaError
from loopora.strategy_source import StrategySourceError
from loopora.web_route_context import WebRouteContext
from loopora.web_strategy_inputs import _normalize_orchestration_form, _orchestration_payload_from_mapping
from loopora.web_url_utils import safe_local_return_path, with_query_params


def register_orchestration_form_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/orchestrations/new")
    async def create_orchestration_from_form(request: Request):
        form = await request.form()
        values = _normalize_orchestration_form(form)
        try:
            orchestration = ctx.svc().create_orchestration(**_orchestration_payload_from_mapping(form, default_to_preset=False))
            return RedirectResponse(url=f"/orchestrations/{orchestration['id']}/edit?saved=1", status_code=303)
        except (LooporaError, StrategySourceError, FileExistsError, OSError, ValueError) as exc:
            return ctx.render_new_orchestration(request, values=values, form_error=str(exc))

    @app.post("/orchestrations/{orchestration_id}/edit")
    async def update_orchestration_from_form(request: Request, orchestration_id: str):
        form = await request.form()
        values = _normalize_orchestration_form(form)
        orchestration = ctx.svc().get_orchestration(orchestration_id)
        return_to = safe_local_return_path(request.query_params.get("return_to", ""))
        try:
            if orchestration.get("source") == "builtin":
                raise LooporaError("built-in orchestrations are read-only; create a new orchestration to customize one")
            updated = ctx.svc().update_orchestration(
                orchestration_id,
                **_orchestration_payload_from_mapping(form, default_to_preset=False),
            )
            if return_to:
                return RedirectResponse(url=with_query_params(return_to, surface_updated="workflow"), status_code=303)
            return RedirectResponse(url=f"/orchestrations/{updated['id']}/edit?saved=1", status_code=303)
        except (LooporaError, StrategySourceError, FileExistsError, OSError, ValueError) as exc:
            return ctx.render_new_orchestration(
                request,
                values=values,
                form_error=str(exc),
                orchestration=orchestration,
            )
