from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from loopora.asset_errors import asset_mutation_error_message
from loopora.service import LooporaError
from loopora.specs import SpecError
from loopora.web_route_context import WebRouteContext
from loopora.web_start_context import request_resource_workdir_context_href


def register_bundle_edit_form_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/bundles/{bundle_id}/edit")
    async def update_bundle_from_form(request: Request, bundle_id: str):
        form = await request.form()
        values = {
            "description": str(form.get("description", "")),
            "collaboration_summary": str(form.get("collaboration_summary", "")),
            "spec_markdown": str(form.get("spec_markdown", "")),
        }
        try:
            updated = ctx.svc().update_bundle(
                bundle_id,
                description=str(form.get("description", "")),
                collaboration_summary=str(form.get("collaboration_summary", "")),
                spec_markdown=str(form.get("spec_markdown", "")),
            )
            return RedirectResponse(url=request_resource_workdir_context_href(request, f"/bundles/{bundle_id}?saved=1", updated), status_code=303)
        except (LooporaError, SpecError, OSError, ValueError) as exc:
            return ctx.render_bundle_detail(
                request,
                bundle_id,
                values=values,
                form_error=asset_mutation_error_message(exc, asset_label="plan file"),
            )
