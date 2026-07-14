from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from loopora.markdown_tools import normalize_markdown_text
from loopora.service import LooporaError
from loopora.specs import SpecError, compile_markdown_spec, save_spec_file, spec_file_save_error
from loopora.web_route_context import WebRouteContext
from loopora.web_spec_documents import (
    _assert_spec_markdown_content,
    _load_spec_markdown_document,
    _resolve_spec_markdown_path,
    _spec_document_payload,
    _spec_document_read_error,
    _spec_document_save_error,
)
from loopora.web_spec_output_recovery import web_spec_output_recovery_payload


def register_spec_document_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    _register_spec_validation_api_routes(app)
    _register_spec_document_read_api_routes(app)
    _register_spec_save_api_route(app, ctx)


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
            return JSONResponse({"ok": False, "error": _spec_document_read_error(exc)})
        return JSONResponse(
            {
                "ok": True,
                "path": str(spec_path),
                "check_count": len(compiled["checks"]),
                "check_mode": compiled["check_mode"],
            }
        )


def _register_spec_document_read_api_routes(app: FastAPI) -> None:
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
            return JSONResponse({"ok": False, "error": _spec_document_read_error(exc)})
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
            return JSONResponse({"ok": False, "error": _spec_document_read_error(exc)})
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
        except OSError as exc:
            return JSONResponse(
                web_spec_output_recovery_payload(
                    action="save_document",
                    validation_error=_spec_document_save_error(exc),
                )
            )
        except LooporaError as exc:
            return JSONResponse({"ok": False, "error": str(exc)})
        if not spec_path.parent.exists():
            return JSONResponse(
                web_spec_output_recovery_payload(
                    action="save_document",
                    validation_error="spec parent directory does not exist",
                )
            )
        try:
            save_spec_file(spec_path, markdown_text, create_parent=False)
        except OSError as exc:
            return JSONResponse(
                web_spec_output_recovery_payload(
                    action="save_document",
                    validation_error=spec_file_save_error(exc),
                )
            )
        return JSONResponse(_spec_document_payload(spec_path, markdown_text))
