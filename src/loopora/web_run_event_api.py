from __future__ import annotations

import json
import time
from collections.abc import Iterator
from typing import Annotated

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from loopora.diagnostics import log_exception
from loopora.web_route_context import WebRouteContext
from loopora.web_streaming import MAX_EVENT_CURSOR_ID, stream_error_payload


def register_run_event_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/api/runs/{run_id}/events")
    async def api_run_events(
        run_id: str,
        after_id: Annotated[int, Query(ge=0, le=MAX_EVENT_CURSOR_ID)] = 0,
        limit: Annotated[int, Query(ge=1, le=5000)] = 200,
    ) -> JSONResponse:
        latest_event_id = _latest_run_event_id(ctx, run_id)
        if after_id > latest_event_id:
            return ctx.json_error("event cursor is out of range")
        return JSONResponse(ctx.svc().stream_events(run_id, after_id=after_id, limit=limit))

    @app.get("/api/runs/{run_id}/stream")
    async def api_run_stream(
        request: Request,
        run_id: str,
        after_id: Annotated[int, Query(ge=0, le=MAX_EVENT_CURSOR_ID)] = 0,
    ) -> Response:
        latest_event_id = _latest_run_event_id(ctx, run_id)
        if after_id > latest_event_id:
            return ctx.json_error("event cursor is out of range")
        after_id = ctx.resolve_stream_after_id(
            request,
            run_id=run_id,
            after_id=after_id,
            latest_event_id=latest_event_id,
        )
        return StreamingResponse(_run_event_stream(ctx, run_id=run_id, after_id=after_id), media_type="text/event-stream")


def _latest_run_event_id(ctx: WebRouteContext, run_id: str) -> int:
    return max(0, int(ctx.svc().latest_run_event_id(run_id) or 0))


def _run_event_stream(ctx: WebRouteContext, *, run_id: str, after_id: int) -> Iterator[str]:
    last_id = after_id
    while True:
        try:
            events = ctx.svc().stream_events(run_id, after_id=last_id)
            for event in events:
                last_id = event["id"]
                yield f"id: {event['id']}\n"
                yield f"event: {event['event_type']}\n"
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            run = ctx.svc().get_run(run_id)
        except Exception as exc:  # noqa: BLE001 - SSE streams must surface failures as stream_error events.
            log_exception(
                ctx.logger,
                "web.run_stream.failed",
                "Run event stream failed",
                error=exc,
                run_id=run_id,
                after_id=last_id,
            )
            payload = stream_error_payload(owner_key="run_id", owner_id=run_id, after_id=last_id)
            yield "event: stream_error\n"
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            break
        if run["status"] in {"succeeded", "failed", "stopped"} and not events:
            break
        yield ": keep-alive\n\n"
        time.sleep(1)
