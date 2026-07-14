from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response

from loopora.asset_errors import asset_mutation_error_message
from loopora.service import LooporaError
from loopora.service_types import LooporaWorkdirUnavailableError
from loopora.specs import SpecError
from loopora.web_bundle_import_recovery import (
    web_bundle_import_file_workdir_recovery,
    web_bundle_import_text_workdir_recovery,
)
from loopora.web_bundle_inputs import (
    _normalize_bundle_import_form,
    bundle_import_preview_reviewed,
)
from loopora.web_bundle_run_routes import bundle_import_run_dispatch_response
from loopora.web_common_inputs import _coerce_bool
from loopora.web_route_context import WebRouteContext
from loopora.web_start_context import (
    request_resource_workdir_context_href,
    request_workdir_context_href,
)
from loopora.web_workdir_recovery import (
    browser_recovery_submit_payload,
    web_loop_start_workdir_recovery_payload,
)

CREATE_LOOP_IMPORT_START_PREVIEW_REQUIRED = "Preview the Plan File before starting it immediately."


def register_bundle_import_form_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    _register_create_loop_bundle_import_routes(app, ctx)
    _register_bundle_import_routes(app, ctx)


def _register_create_loop_bundle_import_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/loops/new/manual/import-bundle")
    @app.post("/loops/new/bundle/import-bundle")
    @app.post("/loops/new/import-bundle")
    async def import_bundle_from_create_loop_form(request: Request):
        return await _import_bundle_from_create_loop_form_response(ctx, request)


async def _import_bundle_from_create_loop_form_response(ctx: WebRouteContext, request: Request) -> Response:
    form = await request.form()
    import_values = _normalize_bundle_import_form(form)
    try:
        recovery_response = _bundle_create_loop_import_recovery_response(ctx, request, form, import_values)
        if recovery_response is not None:
            return recovery_response
        preview_response = _bundle_create_loop_import_start_preview_response(ctx, request, form, import_values)
        if preview_response is not None:
            return preview_response
        bundle = _import_bundle_from_form_fields(ctx, form)
        return _bundle_create_loop_import_success_response(ctx, request, form, import_values, bundle)
    except (LooporaError, SpecError, FileExistsError, OSError, ValueError) as exc:
        return _render_create_loop_bundle_import_error(
            ctx,
            request,
            form,
            import_values,
            asset_mutation_error_message(exc, asset_label="plan file", action="imported"),
        )


def _bundle_create_loop_import_recovery_response(
    ctx: WebRouteContext,
    request: Request,
    form,
    import_values: dict[str, object],
) -> Response | None:
    recovery = _bundle_import_recovery_from_form(form)
    if recovery is None:
        return None
    recovery = _browser_bundle_import_recovery(request, recovery, form_action="/loops/new/manual/import-bundle")
    return _render_create_loop_bundle_import_error(
        ctx,
        request,
        form,
        import_values,
        str(recovery.get("error") or recovery.get("summary") or ""),
        import_recovery=recovery,
    )


def _bundle_create_loop_import_start_preview_response(
    ctx: WebRouteContext,
    request: Request,
    form,
    import_values: dict[str, object],
) -> Response | None:
    if not _coerce_bool(form.get("start_immediately")) or bundle_import_preview_reviewed(
        form,
        form.get("bundle_preview_reviewed"),
    ):
        return None
    return _render_create_loop_bundle_import_error(
        ctx,
        request,
        form,
        import_values,
        CREATE_LOOP_IMPORT_START_PREVIEW_REQUIRED,
    )


def _bundle_create_loop_import_success_response(
    ctx: WebRouteContext,
    request: Request,
    form,
    import_values: dict[str, object],
    bundle: dict,
) -> Response:
    loop_id = str(bundle.get("loop_id", "") or "").strip()
    if not loop_id:
        return RedirectResponse(url=request_resource_workdir_context_href(request, f"/bundles/{bundle['id']}", bundle), status_code=303)
    if not _coerce_bool(form.get("start_immediately")):
        return RedirectResponse(url=request_resource_workdir_context_href(request, f"/loops/{loop_id}", bundle), status_code=303)
    return _start_imported_bundle_loop_from_create_form(ctx, request, form, import_values, loop_id)


def _start_imported_bundle_loop_from_create_form(
    ctx: WebRouteContext,
    request: Request,
    form,
    import_values: dict[str, object],
    loop_id: str,
) -> Response:
    try:
        run = ctx.svc().start_run(loop_id)
    except LooporaWorkdirUnavailableError as exc:
        recovery = _browser_bundle_import_recovery(
            request,
            web_loop_start_workdir_recovery_payload(loop_id, exc.workdir),
            form_action=f"/loops/{loop_id}/runs",
            action_kinds=("retry_web_run_start",),
        )
        return _render_create_loop_bundle_import_error(
            ctx,
            request,
            form,
            import_values,
            str(recovery.get("error") or recovery.get("summary") or ""),
            import_recovery=recovery,
        )
    dispatch_response = bundle_import_run_dispatch_response(ctx, request, loop_id, run)
    if dispatch_response is not None:
        return dispatch_response
    return RedirectResponse(url=request_resource_workdir_context_href(request, f"/runs/{run['id']}", run), status_code=303)


def _render_create_loop_bundle_import_error(  # noqa: PLR0913 - form rerendering needs request, values, error, and optional recovery context.
    ctx: WebRouteContext,
    request: Request,
    form,
    import_values: dict[str, object],
    error: str,
    *,
    import_recovery: dict[str, object] | None = None,
) -> Response:
    if not _form_has_replace_intent(form):
        import_values["replace_bundle_id"] = ""
    return ctx.render_new_loop(
        request,
        page_mode="manual",
        import_values=import_values,
        import_error=error,
        import_recovery=import_recovery,
    )


def _register_bundle_import_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/bundles/import")
    async def import_bundle_from_form(request: Request):
        form = await request.form()
        import_values = _normalize_bundle_import_form(form)
        try:
            recovery = _bundle_import_recovery_from_form(form)
            if recovery is not None:
                if not _form_has_replace_intent(form):
                    import_values["replace_bundle_id"] = ""
                recovery = _browser_bundle_import_recovery(request, recovery, form_action="/bundles/import")
                return ctx.render_bundles(
                    request,
                    import_values=import_values,
                    import_error=str(recovery.get("error") or recovery.get("summary") or ""),
                    import_recovery=recovery,
                )
            bundle = _import_bundle_from_form_fields(ctx, form)
            return RedirectResponse(url=request_resource_workdir_context_href(request, f"/bundles/{bundle['id']}", bundle), status_code=303)
        except (LooporaError, SpecError, FileExistsError, OSError, ValueError) as exc:
            if not _form_has_replace_intent(form):
                import_values["replace_bundle_id"] = ""
            return ctx.render_bundles(
                request,
                import_values=import_values,
                import_error=asset_mutation_error_message(exc, asset_label="plan file", action="imported"),
            )


def _import_bundle_from_form_fields(ctx: WebRouteContext, form) -> dict:
    bundle_path = str(form.get("bundle_path", "")).strip()
    bundle_yaml = str(form.get("bundle_yaml", ""))
    replace_bundle_id = _replace_bundle_id_from_web_form(form)
    if bundle_yaml.strip():
        return ctx.svc().import_bundle_text(bundle_yaml, replace_bundle_id=replace_bundle_id)
    if bundle_path:
        return ctx.svc().import_bundle_file(Path(bundle_path), replace_bundle_id=replace_bundle_id)
    raise LooporaError("bundle path or bundle YAML is required")


def _browser_bundle_import_recovery(
    request: Request,
    recovery: dict[str, object],
    *,
    form_action: str,
    action_kinds: tuple[str, ...] = ("retry_web_compose",),
) -> dict[str, object]:
    return browser_recovery_submit_payload(
        recovery,
        form_id="bundle-import-form-fields",
        form_action=request_workdir_context_href(request, form_action),
        action_kinds=action_kinds,
    )


def _bundle_import_recovery_from_form(form) -> dict[str, object] | None:
    bundle_path = str(form.get("bundle_path", "")).strip()
    bundle_yaml = str(form.get("bundle_yaml", ""))
    action = "replace_bundle" if _form_has_replace_intent(form) else "import_bundle"
    if bundle_yaml.strip():
        return web_bundle_import_text_workdir_recovery(bundle_yaml, action=action)
    if bundle_path:
        return web_bundle_import_file_workdir_recovery(Path(bundle_path), action=action)
    return None


def _form_has_replace_intent(form) -> bool:
    return str(form.get("import_intent", "")).strip() == "replace"


def _replace_bundle_id_from_web_form(form) -> str | None:
    replace_bundle_id = str(form.get("replace_bundle_id", "")).strip()
    if not replace_bundle_id:
        return None
    if not _form_has_replace_intent(form):
        raise LooporaError("plan replacement must start from an explicit replace action")
    return replace_bundle_id
