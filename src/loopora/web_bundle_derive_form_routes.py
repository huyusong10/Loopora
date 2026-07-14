from __future__ import annotations

from urllib.parse import urlencode

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from loopora.asset_errors import asset_mutation_error_message
from loopora.bundles import bundle_to_yaml
from loopora.service import LooporaError
from loopora.specs import SpecError
from loopora.web_bundle_import_recovery import web_bundle_import_text_workdir_recovery
from loopora.web_bundle_inputs import _normalize_bundle_derive_form
from loopora.web_route_context import WebRouteContext
from loopora.web_start_context import request_resource_workdir_context_href, request_workdir_context_href
from loopora.web_workdir_recovery import browser_recovery_submit_payload


def register_bundle_derive_form_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/bundles/derive")
    async def derive_bundle_from_form(request: Request):
        form = await request.form()
        derive_values = _normalize_bundle_derive_form(form)
        loop_id = str(form.get("loop_id", "")).strip()
        if not loop_id:
            return ctx.render_bundles(request, derive_values=derive_values, derive_error="loop id is required")
        if str(form.get("derive_action", "")).strip() == "save":
            return _save_derived_bundle_from_form(ctx, request, form, derive_values, loop_id)
        return _download_derived_bundle_redirect(request, form, loop_id)


def _save_derived_bundle_from_form(
    ctx: WebRouteContext,
    request: Request,
    form,
    derive_values: dict[str, object],
    loop_id: str,
):
    try:
        bundle = ctx.svc().derive_bundle_from_loop(
            loop_id,
            name=str(form.get("name", "")).strip() or None,
            description=str(form.get("description", "")),
            collaboration_summary=str(form.get("collaboration_summary", "")),
        )
        bundle_yaml = bundle_to_yaml(bundle)
        recovery = web_bundle_import_text_workdir_recovery(bundle_yaml, action="save_derived_bundle")
        if recovery is not None:
            recovery = browser_recovery_submit_payload(
                recovery,
                form_id="bundle-derive-form-fields",
                form_action=request_workdir_context_href(request, "/bundles/derive"),
                action_kinds=("retry_web_compose",),
            )
            return ctx.render_bundles(
                request,
                derive_values=derive_values,
                derive_error=str(recovery.get("error") or recovery.get("summary") or ""),
                derive_recovery=recovery,
            )
        saved = ctx.svc().import_bundle_text(bundle_yaml)
        return RedirectResponse(
            url=request_resource_workdir_context_href(request, f"/bundles/{saved['id']}?created_from_loop=1", saved),
            status_code=303,
        )
    except (LooporaError, SpecError, FileExistsError, OSError, ValueError) as exc:
        return ctx.render_bundles(
            request,
            derive_values=derive_values,
            derive_error=asset_mutation_error_message(exc, asset_label="plan file"),
        )


def _download_derived_bundle_redirect(request: Request, form, loop_id: str) -> RedirectResponse:
    query_params = {"loop_id": loop_id}
    for key in ("name", "description", "collaboration_summary"):
        value = str(form.get(key, "")).strip()
        if value:
            query_params[key] = value
    return RedirectResponse(
        url=request_workdir_context_href(request, f"/bundles/derive/export?{urlencode(query_params)}"),
        status_code=303,
    )
