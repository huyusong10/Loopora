from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response

from loopora.markdown_tools import normalize_markdown_text, render_safe_markdown_html
from loopora.service import LooporaError
from loopora.specs import (
    SpecError,
    compile_markdown_spec,
    init_spec_file_for_strategy_source,
    render_spec_template_for_strategy_source,
)
from loopora.strategy_source import (
    StrategySourceError,
    builtin_strategy_prompt_markdown,
    normalize_strategy_role_display_name,
    validate_strategy_prompt_markdown,
)
from loopora.web_common_inputs import _coerce_bool
from loopora.web_route_context import WebRouteContext
from loopora.web_inputs import (
    _assert_spec_markdown_content,
    _load_spec_markdown_document,
    _resolve_spec_markdown_path,
    _spec_document_payload,
)
from loopora.web_strategy_inputs import _strategy_source_for_spec_template
from loopora.web_route_context_loop_pages import attachment_content_disposition


def register_spec_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    _register_spec_validation_api_routes(app)
    _register_spec_document_api_routes(app)
    _register_spec_save_api_route(app, ctx)
    _register_markdown_prompt_api_routes(app, ctx)
    _register_spec_template_api_routes(app, ctx)


def _register_spec_validation_api_routes(app: FastAPI) -> None:
    @app.get("/api/specs/validate")
    async def api_validate_spec(path: str = "") -> JSONResponse:
        path_text = path.strip()
        if not path_text:
            return JSONResponse({"ok": False, "error": "spec path is required"})
        try:
            spec_path, markdown_text = _load_spec_markdown_document(
                path_text,
                binary_error="spec validation only supports text markdown files",
            )
            compiled = compile_markdown_spec(markdown_text)
        except (FileNotFoundError, OSError, LooporaError, SpecError) as exc:
            return JSONResponse({"ok": False, "error": str(exc)})
        return JSONResponse(
            {
                "ok": True,
                "path": str(spec_path),
                "check_count": len(compiled["checks"]),
                "check_mode": compiled["check_mode"],
            }
        )


def _register_spec_document_api_routes(app: FastAPI) -> None:
    @app.get("/api/specs/preview")
    async def api_preview_spec(path: str = "") -> JSONResponse:
        path_text = path.strip()
        if not path_text:
            return JSONResponse({"ok": False, "error": "spec path is required"})
        try:
            spec_path, markdown_text = _load_spec_markdown_document(
                path_text,
                binary_error="spec preview only supports text markdown files",
            )
        except (FileNotFoundError, OSError, LooporaError) as exc:
            return JSONResponse({"ok": False, "error": str(exc)})
        return JSONResponse(_spec_document_payload(spec_path, markdown_text))

    @app.get("/api/specs/document")
    async def api_get_spec_document(path: str = "") -> JSONResponse:
        path_text = path.strip()
        if not path_text:
            return JSONResponse({"ok": False, "error": "spec path is required"})
        try:
            spec_path, markdown_text = _load_spec_markdown_document(
                path_text,
                binary_error="spec editor only supports text markdown files",
            )
        except (FileNotFoundError, OSError, LooporaError) as exc:
            return JSONResponse({"ok": False, "error": str(exc)})
        return JSONResponse(_spec_document_payload(spec_path, markdown_text))


def _register_spec_save_api_route(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.put("/api/specs/document")
    async def api_save_spec_document(request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        path_text = str(payload.get("path", "")).strip()
        markdown_text = normalize_markdown_text(str(payload.get("content", "")))
        if not path_text:
            return JSONResponse({"ok": False, "error": "spec path is required"})
        try:
            spec_path = _resolve_spec_markdown_path(path_text)
            _assert_spec_markdown_content(
                markdown_text.encode("utf-8"),
                binary_error="spec editor only supports text markdown files",
            )
        except LooporaError as exc:
            return JSONResponse({"ok": False, "error": str(exc)})
        if not spec_path.parent.exists():
            return JSONResponse({"ok": False, "error": f"spec parent directory does not exist: {spec_path.parent}"})
        try:
            spec_path.write_text(markdown_text, encoding="utf-8")
        except OSError as exc:
            return JSONResponse({"ok": False, "error": str(exc)})
        return JSONResponse(_spec_document_payload(spec_path, markdown_text))


def _register_markdown_prompt_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/api/markdown/render")
    async def api_render_markdown(request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        markdown_text = str(payload.get("markdown", ""))
        strip_front_matter = _coerce_bool(payload.get("strip_front_matter", False))
        return JSONResponse(
            {
                "ok": True,
                "rendered_html": render_safe_markdown_html(markdown_text, strip_front_matter=strip_front_matter),
            }
        )

    @app.post("/api/prompts/validate")
    async def api_validate_prompt(request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        markdown_text = str(payload.get("markdown", ""))
        expected_archetype = str(payload.get("archetype", "")).strip() or None
        try:
            metadata, body = validate_strategy_prompt_markdown(markdown_text, expected_archetype=expected_archetype)
        except StrategySourceError as exc:
            return JSONResponse({"ok": False, "error": str(exc)})
        return JSONResponse({"ok": True, "metadata": metadata, "body": body})

    @app.get("/api/prompts/templates/{prompt_ref}")
    async def api_prompt_template(prompt_ref: str, locale: Annotated[str | None, Query()] = None) -> Response:
        try:
            markdown_text = builtin_strategy_prompt_markdown(prompt_ref, locale=locale)
        except StrategySourceError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return Response(
            content=markdown_text,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": attachment_content_disposition(prompt_ref, default="prompt.md")},
        )


def _register_spec_template_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/api/specs/init")
    async def api_init_spec(request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        path_text = str(payload.get("path", "")).strip()
        if not path_text:
            return ctx.json_error("spec path is required")
        locale = str(payload.get("locale", "zh"))
        try:
            strategy_source = _strategy_source_for_spec_template(payload)
        except (LooporaError, StrategySourceError) as exc:
            return ctx.json_error_from_exception(exc)
        try:
            spec_path = _resolve_spec_markdown_path(path_text)
            created = init_spec_file_for_strategy_source(spec_path, locale=locale, strategy_source=strategy_source)
        except (FileExistsError, OSError, LooporaError) as exc:
            return ctx.json_error_from_exception(exc)
        return JSONResponse({"path": str(created.resolve())}, status_code=201)

    @app.post("/api/specs/template")
    async def api_spec_template(request: Request) -> JSONResponse:
        payload = await ctx.read_json_mapping(request)
        try:
            strategy_source = _strategy_source_for_spec_template(payload)
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
        label = normalize_strategy_role_display_name(role.get("name"), archetype=role.get("archetype")) or str(
            role.get("name", "")
        ).strip()
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
