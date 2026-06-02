from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from loopora.service import LooporaError
from loopora.specs import SpecError
from loopora.web_bundle_inputs import (
    _normalize_bundle_derive_form,
    _normalize_bundle_import_form,
)
from loopora.web_common_inputs import _coerce_bool
from loopora.web_route_context import WebRouteContext


def register_bundle_form_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    _register_create_loop_bundle_import_routes(app, ctx)
    _register_bundle_import_routes(app, ctx)
    _register_bundle_edit_routes(app, ctx)
    _register_bundle_derive_routes(app, ctx)


def _register_create_loop_bundle_import_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/loops/new/manual/import-bundle")
    @app.post("/loops/new/bundle/import-bundle")
    @app.post("/loops/new/import-bundle")
    async def import_bundle_from_create_loop_form(request: Request):
        form = await request.form()
        import_values = _normalize_bundle_import_form(form)
        try:
            bundle = _import_bundle_from_form_fields(ctx, form)
            loop_id = str(bundle.get("loop_id", "") or "").strip()
            if not loop_id:
                return RedirectResponse(url=f"/bundles/{bundle['id']}", status_code=303)
            if _coerce_bool(form.get("start_immediately")):
                run = ctx.svc().start_run(loop_id)
                ctx.svc().start_run_async(run["id"])
                return RedirectResponse(url=f"/runs/{run['id']}", status_code=303)
            return RedirectResponse(url=f"/loops/{loop_id}", status_code=303)
        except (LooporaError, SpecError, FileExistsError, OSError, ValueError) as exc:
            return ctx.render_new_loop(request, page_mode="manual", import_values=import_values, import_error=str(exc))


def _register_bundle_import_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/bundles/import")
    async def import_bundle_from_form(request: Request):
        form = await request.form()
        import_values = _normalize_bundle_import_form(form)
        try:
            bundle = _import_bundle_from_form_fields(ctx, form)
            return RedirectResponse(url=f"/bundles/{bundle['id']}", status_code=303)
        except (LooporaError, SpecError, FileExistsError, OSError, ValueError) as exc:
            return ctx.render_new_loop(request, page_mode="manual", import_values=import_values, import_error=str(exc))


def _register_bundle_edit_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/bundles/{bundle_id}/edit")
    async def update_bundle_from_form(request: Request, bundle_id: str):
        form = await request.form()
        values = {
            "description": str(form.get("description", "")),
            "collaboration_summary": str(form.get("collaboration_summary", "")),
            "spec_markdown": str(form.get("spec_markdown", "")),
        }
        try:
            ctx.svc().update_bundle(
                bundle_id,
                description=str(form.get("description", "")),
                collaboration_summary=str(form.get("collaboration_summary", "")),
                spec_markdown=str(form.get("spec_markdown", "")),
            )
            return RedirectResponse(url=f"/bundles/{bundle_id}?saved=1", status_code=303)
        except (LooporaError, SpecError, OSError, ValueError) as exc:
            return ctx.render_bundle_detail(request, bundle_id, values=values, form_error=str(exc))


def _register_bundle_derive_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/bundles/derive")
    async def derive_bundle_from_form(request: Request):
        form = await request.form()
        derive_values = _normalize_bundle_derive_form(form)
        loop_id = str(form.get("loop_id", "")).strip()
        if not loop_id:
            return ctx.render_bundles(request, derive_values=derive_values, derive_error="loop id is required")
        query_params = {"loop_id": loop_id}
        for key in ("name", "description", "collaboration_summary"):
            value = str(form.get(key, "")).strip()
            if value:
                query_params[key] = value
        return RedirectResponse(url=f"/bundles/derive/export?{urlencode(query_params)}", status_code=303)


def _import_bundle_from_form_fields(ctx: WebRouteContext, form) -> dict:
    bundle_path = str(form.get("bundle_path", "")).strip()
    bundle_yaml = str(form.get("bundle_yaml", ""))
    replace_bundle_id = str(form.get("replace_bundle_id", "")).strip() or None
    if bundle_yaml.strip():
        return ctx.svc().import_bundle_text(bundle_yaml, replace_bundle_id=replace_bundle_id)
    if bundle_path:
        return ctx.svc().import_bundle_file(Path(bundle_path), replace_bundle_id=replace_bundle_id)
    raise LooporaError("bundle path or bundle YAML is required")
