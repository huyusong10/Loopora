from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from loopora.markdown_tools import render_safe_markdown_html
from loopora.service import LooporaError
from loopora.specs import init_spec_file_for_strategy_source, render_spec_template_for_strategy_source, spec_file_init_error
from loopora.strategy_source import StrategySourceError, normalize_strategy_role_display_name
from loopora.web_route_context import WebRouteContext
from loopora.web_spec_documents import _resolve_spec_markdown_path
from loopora.web_spec_output_recovery import web_spec_output_recovery_payload
from loopora.web_strategy_inputs import _strategy_source_for_spec_template_request


def register_spec_template_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/api/specs/init")
    async def api_init_spec(request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        path_text = str(payload.get("path", "")).strip()
        if not path_text:
            return ctx.json_error("spec path is required")
        locale = str(payload.get("locale", "zh"))
        try:
            strategy_source = _strategy_source_for_spec_template_request(
                payload,
                get_orchestration=ctx.svc().get_orchestration,
            )
        except (LooporaError, StrategySourceError) as exc:
            return ctx.json_error_from_exception(exc)
        try:
            spec_path = _resolve_spec_markdown_path(path_text)
            created = init_spec_file_for_strategy_source(spec_path, locale=locale, strategy_source=strategy_source)
        except (FileExistsError, OSError, LooporaError) as exc:
            return JSONResponse(
                web_spec_output_recovery_payload(
                    action="init",
                    validation_error=spec_file_init_error(exc),
                ),
                status_code=ctx.error_status_code(exc),
            )
        return JSONResponse({"path": str(created.resolve())}, status_code=201)

    @app.post("/api/specs/template")
    async def api_spec_template(request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        try:
            strategy_source = _strategy_source_for_spec_template_request(
                payload,
                get_orchestration=ctx.svc().get_orchestration,
            )
        except (LooporaError, StrategySourceError) as exc:
            return ctx.json_error_from_exception(exc)
        locale = str(payload.get("locale", "zh"))
        markdown_text = render_spec_template_for_strategy_source(locale=locale, strategy_source=strategy_source)
        return JSONResponse(
            {
                "ok": True,
                "content": markdown_text,
                "rendered_html": render_safe_markdown_html(markdown_text),
                "role_note_sections": _role_note_sections_from_strategy_source(strategy_source),
            }
        )


def _role_note_sections_from_strategy_source(strategy_source: dict | None) -> list[dict[str, str]]:
    if not strategy_source:
        return []
    sections: list[dict[str, str]] = []
    seen: set[str] = set()
    for role in strategy_source.get("roles", []):
        if not isinstance(role, dict):
            continue
        label = normalize_strategy_role_display_name(role.get("name"), archetype=role.get("archetype")) or str(role.get("name", "")).strip()
        normalized = label.lower()
        if not label or normalized in seen:
            continue
        seen.add(normalized)
        sections.append(
            {
                "heading": f"{label} Notes",
                "role_name": label,
                "archetype": str(role.get("archetype", "")).strip(),
            }
        )
    return sections
