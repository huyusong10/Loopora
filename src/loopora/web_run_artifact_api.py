from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

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

    @app.get("/api/runs/{run_id}/artifacts/{artifact_id}")
    async def api_run_artifact_preview(run_id: str, artifact_id: str) -> JSONResponse:
        run = ctx.svc().get_run(run_id)
        artifact = _artifact_record_or_404(run, artifact_id)
        artifact_path = Path(run["runs_dir"]) / artifact["relative_path"]
        relative_path = f"runs/{run_id}/{artifact['relative_path']}"
        if not artifact_path.exists():
            return JSONResponse(
                {
                    "kind": "missing",
                    "artifact": {
                        **artifact,
                        "path": relative_path,
                    },
                    "message": "missing",
                }
            )
        preview = ctx.svc().preview_file(run_id, root="loopora", relative_path=relative_path)
        preview["artifact"] = {
            **artifact,
            "path": relative_path,
        }
        return JSONResponse(preview)

    @app.get("/api/runs/{run_id}/artifacts/{artifact_id}/download")
    async def api_run_artifact_download(run_id: str, artifact_id: str) -> FileResponse:
        run = ctx.svc().get_run(run_id)
        artifact = _artifact_record_or_404(run, artifact_id)
        artifact_path = Path(run["runs_dir"]) / artifact["relative_path"]
        if not artifact_path.exists():
            raise HTTPException(status_code=404, detail="artifact not found")
        relative_path = f"runs/{run_id}/{artifact['relative_path']}"
        return _attachment_file_response(ctx.svc().download_file_path(run_id, root="loopora", relative_path=relative_path))


def register_file_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/api/files")
    async def api_preview_file(
        run_id: str,
        root: str = Query(default="workdir", pattern=FILE_ROOT_QUERY_PATTERN),
        path: str = "",
    ) -> JSONResponse:
        return JSONResponse(ctx.svc().preview_file(run_id, root=root, relative_path=path))

    @app.get("/api/files/download")
    async def api_download_file(
        run_id: str,
        root: str = Query(default="workdir", pattern=FILE_ROOT_QUERY_PATTERN),
        path: str = "",
    ) -> FileResponse:
        return _attachment_file_response(ctx.svc().download_file_path(run_id, root=root, relative_path=path))


def _attachment_file_response(path: Path) -> FileResponse:
    return FileResponse(
        path,
        media_type="application/octet-stream",
        headers={"Content-Disposition": attachment_content_disposition(path.name, default="download")},
    )
