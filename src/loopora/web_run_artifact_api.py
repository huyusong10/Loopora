from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse, Response

from loopora.branding import FILE_ROOT_QUERY_PATTERN
from loopora.run_artifact_catalog import list_run_artifacts as _list_run_artifacts
from loopora.run_takeaways import build_run_key_takeaways
from loopora.web_overviews import _artifact_record_or_404
from loopora.web_route_context import WebRouteContext
from loopora.web_url_utils import attachment_content_disposition


def register_run_artifact_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/api/runs/{run_id}/artifacts")
    async def api_run_artifacts(run_id: str) -> JSONResponse:
        run = ctx.svc().get_run(run_id)
        return JSONResponse(_list_run_artifacts(run))

    @app.get("/api/runs/{run_id}/key-takeaways")
    async def api_run_key_takeaways(run_id: str) -> JSONResponse:
        run = ctx.svc().get_run(run_id)
        return JSONResponse(build_run_key_takeaways(run))

    @app.get("/api/runs/{run_id}/evidence-package")
    async def api_run_evidence_package(run_id: str) -> Response:
        package = ctx.svc().build_run_evidence_package(run_id)
        return Response(
            content=package.content,
            media_type="application/zip",
            headers={
                "Content-Disposition": attachment_content_disposition(package.filename, default="loopora-evidence.zip"),
                "Content-Length": str(len(package.content)),
            },
        )

    @app.get("/api/runs/{run_id}/artifacts/{artifact_id}")
    async def api_run_artifact_preview(run_id: str, artifact_id: str) -> JSONResponse:
        run = ctx.svc().get_run(run_id)
        artifact = _artifact_record_or_404(run, artifact_id)
        artifact_path = Path(run["runs_dir"]) / artifact["relative_path"]
        relative_path = _artifact_api_path(run_id, artifact)
        if not artifact_path.exists():
            return JSONResponse(_missing_artifact_payload(run_id, artifact))
        preview = ctx.svc().preview_file(run_id, root="loopora", relative_path=relative_path)
        preview["artifact"] = {
            **artifact,
            "path": relative_path,
        }
        return JSONResponse(preview)

    @app.get("/api/runs/{run_id}/artifacts/{artifact_id}/download")
    async def api_run_artifact_download(run_id: str, artifact_id: str) -> Response:
        run = ctx.svc().get_run(run_id)
        artifact = _artifact_record_or_404(run, artifact_id)
        artifact_path = Path(run["runs_dir"]) / artifact["relative_path"]
        if not artifact_path.exists():
            return JSONResponse(_missing_artifact_payload(run_id, artifact), status_code=404)
        relative_path = _artifact_api_path(run_id, artifact)
        return _attachment_file_response(ctx.svc().download_file_path(run_id, root="loopora", relative_path=relative_path))


def register_file_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/api/files")
    async def api_preview_file(
        run_id: str,
        root: Annotated[str, Query(pattern=FILE_ROOT_QUERY_PATTERN)] = "workdir",
        path: str = "",
    ) -> JSONResponse:
        return JSONResponse(ctx.svc().preview_file(run_id, root=root, relative_path=path))

    @app.get("/api/files/download")
    async def api_download_file(
        run_id: str,
        root: Annotated[str, Query(pattern=FILE_ROOT_QUERY_PATTERN)] = "workdir",
        path: str = "",
    ) -> FileResponse:
        return _attachment_file_response(ctx.svc().download_file_path(run_id, root=root, relative_path=path))


def _attachment_file_response(path: Path) -> FileResponse:
    return FileResponse(
        path,
        media_type="application/octet-stream",
        headers={"Content-Disposition": attachment_content_disposition(path.name, default="download")},
    )


def _artifact_api_path(run_id: str, artifact: dict) -> str:
    return f"runs/{run_id}/{artifact['relative_path']}"


def _missing_artifact_payload(run_id: str, artifact: dict) -> dict:
    return {
        "kind": "missing",
        "artifact": {
            **artifact,
            "path": _artifact_api_path(run_id, artifact),
        },
        "message": "missing",
    }
