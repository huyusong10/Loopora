from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from loopora.diagnose_doctor import (
    build_doctor_report,
    build_target_required_doctor_report,
    doctor_public_json_payload,
)
from loopora.diagnose_doctor_web_state import DEFAULT_WEB_HOST, DEFAULT_WEB_PORT
from loopora.support_guidance import normalize_support_guidance_language, support_public_issue_bundle_text
from loopora.web_route_context import WebRouteContext


def register_diagnostics_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/api/diagnostics/doctor")
    async def api_doctor(
        *,
        workdir: str = "",
        public: Annotated[bool, Query()] = False,
    ) -> JSONResponse:
        host = str(ctx.access_state.get("bind_host") or DEFAULT_WEB_HOST)
        port = _diagnostic_web_port(ctx.access_state.get("bind_port"))
        if not str(workdir or "").strip():
            report = build_target_required_doctor_report(
                web_host=host,
                web_port=port,
                web_already_running=True,
                web_auth_enabled=bool(ctx.access_state.get("auth_enabled")),
            )
            return JSONResponse(doctor_public_json_payload(report) if public else report)
        workdir_error = _diagnostic_workdir_error(workdir)
        if workdir_error is not None:
            return workdir_error
        root = _diagnostic_workdir(workdir)
        report = build_doctor_report(
            workdir=root,
            web_host=host,
            web_port=port,
            web_already_running=True,
            web_auth_enabled=bool(ctx.access_state.get("auth_enabled")),
        )
        return JSONResponse(doctor_public_json_payload(report) if public else report)

    @app.get("/api/diagnostics/public-issue-bundle")
    async def api_public_issue_bundle(
        *,
        workdir: str = "",
        language: str = "en",
    ) -> Response:
        if not str(workdir or "").strip():
            return JSONResponse(
                {
                    "error": "target_project_required",
                    "message": "A target project is required before generating a public issue support bundle.",
                    "target_project_required": True,
                    "recovery_action": "choose_target_project",
                    "next_action_kind": "choose_workdir_for_public_report",
                },
                status_code=400,
            )
        workdir_error = _diagnostic_workdir_error(workdir)
        if workdir_error is not None:
            return workdir_error
        root = _diagnostic_workdir(workdir)
        host = str(ctx.access_state.get("bind_host") or DEFAULT_WEB_HOST)
        port = _diagnostic_web_port(ctx.access_state.get("bind_port"))
        report = build_doctor_report(
            workdir=root,
            web_host=host,
            web_port=port,
            web_already_running=True,
            web_auth_enabled=bool(ctx.access_state.get("auth_enabled")),
        )
        return PlainTextResponse(
            support_public_issue_bundle_text(
                doctor_public_json_payload(report),
                language=_diagnostic_support_language(language),
            ),
            media_type="text/plain; charset=utf-8",
        )

    @app.get("/api/diagnostics/local-assets")
    async def api_local_asset_diagnostics() -> JSONResponse:
        return JSONResponse(ctx.svc().local_asset_diagnostics())


def _diagnostic_workdir(value: str) -> Path:
    raw = str(value or "").strip()
    return Path(raw).expanduser() if raw else Path.cwd()


def _diagnostic_workdir_error(value: str) -> JSONResponse | None:
    raw = str(value or "").strip()
    if not raw or Path(raw).expanduser().is_absolute():
        return None
    return JSONResponse(
        {
            "error": "target_project_absolute_path_required",
            "message": "Use a server-side absolute target project path for diagnostics.",
            "target_project_required": True,
            "recovery_action": "choose_target_project",
            "next_action_kind": "choose_workdir_for_public_report",
        },
        status_code=400,
    )


def _diagnostic_web_port(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return DEFAULT_WEB_PORT


def _diagnostic_support_language(value: str) -> str:
    try:
        return normalize_support_guidance_language(value)
    except ValueError:
        return "en"
