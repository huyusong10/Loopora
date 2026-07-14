from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import Response

from loopora.asset_errors import asset_mutation_error_message
from loopora.service import LooporaError
from loopora.web_bundle_export_recovery import web_bundle_export_generation_recovery_payload
from loopora.web_route_context import WebRouteContext
from loopora.web_start_context import request_workdir_context
from loopora.web_start_context import workdir_context_href
from loopora.web_url_utils import attachment_content_disposition


def register_bundle_export_page_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/bundles/derive/export")
    async def derive_bundle_export(
        request: Request,
        loop_id: str,
        name: str = "",
        description: str = "",
        collaboration_summary: str = "",
    ) -> Response:
        try:
            bundle = ctx.svc().derive_bundle_from_loop(
                loop_id,
                name=name.strip() or None,
                description=description,
                collaboration_summary=collaboration_summary,
            )
        except (LooporaError, OSError, UnicodeError, ValueError) as exc:
            return ctx.render_bundles(
                request,
                derive_values={
                    "loop_id": loop_id,
                    "name": name,
                    "description": description,
                    "collaboration_summary": collaboration_summary,
                },
                derive_error=asset_mutation_error_message(exc, asset_label="plan file", action="generated"),
            )
        filename = f"{bundle['metadata']['name'] or loop_id}.yml"
        from loopora.bundles import bundle_to_yaml

        return Response(
            content=bundle_to_yaml(bundle),
            media_type="application/yaml; charset=utf-8",
            headers={"Content-Disposition": attachment_content_disposition(filename, default=f"{loop_id}.yml")},
        )

    @app.get("/bundles/{bundle_id}/export")
    async def bundle_export_page(request: Request, bundle_id: str) -> Response:
        return _browser_bundle_export_response(request, ctx, bundle_id)


def _browser_bundle_export_response(request: Request, ctx: WebRouteContext, bundle_id: str) -> Response:
    try:
        bundle = ctx.svc().export_bundle(bundle_id)
        from loopora.bundles import bundle_to_yaml

        yaml_text = bundle_to_yaml(bundle)
    except (LooporaError, OSError, UnicodeError, ValueError) as exc:
        recovery = web_bundle_export_generation_recovery_payload(
            bundle_id,
            exc,
            retry_surface="page",
            workdir_context=request_workdir_context(request),
        )
        recovery = _browser_bundle_export_context_recovery(request, recovery)
        return ctx.render_bundles(
            request,
            derive_error=str(recovery.get("error") or "plan file could not be generated"),
            derive_recovery=recovery,
        )

    return Response(
        content=yaml_text,
        media_type="application/yaml; charset=utf-8",
        headers={
            "Content-Disposition": attachment_content_disposition(
                f"{bundle['metadata']['name'] or bundle_id}.yml",
                default=f"{bundle_id}.yml",
            )
        },
    )


def _browser_bundle_export_context_recovery(request: Request, recovery: dict[str, object]) -> dict[str, object]:
    workdir_context = request_workdir_context(request)
    if not workdir_context:
        return recovery
    projected = dict(recovery)
    actions = recovery.get("next_actions")
    if not isinstance(actions, list):
        return projected
    projected_actions: list[dict[str, object]] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        projected_action = dict(action)
        redirect_url = str(projected_action.get("redirect_url") or "").strip()
        if redirect_url:
            projected_action["redirect_url"] = workdir_context_href(redirect_url, workdir_context)
        projected_actions.append(projected_action)
    projected["next_actions"] = projected_actions
    return projected
