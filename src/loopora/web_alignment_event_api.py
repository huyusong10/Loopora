from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterator
from typing import Annotated

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from loopora.diagnostics import log_event, log_exception
from loopora.service_alignment_status import ALIGNMENT_ACTIVE_STATUSES
from loopora.web_route_context import WebRouteContext
from loopora.web_streaming import MAX_EVENT_CURSOR_ID, parse_sse_last_event_id, stream_error_payload


def register_alignment_event_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/api/alignments/sessions/{session_id}/events")
    async def api_alignment_events(
        session_id: str,
        after_id: Annotated[int, Query(ge=0, le=MAX_EVENT_CURSOR_ID)] = 0,
        limit: Annotated[int, Query(ge=1, le=5000)] = 200,
    ) -> JSONResponse:
        latest_event_id = _latest_alignment_event_id(ctx, session_id)
        if after_id > latest_event_id:
            return ctx.json_error("event cursor is out of range")
        return JSONResponse(ctx.svc().list_alignment_events(session_id, after_id=after_id, limit=limit))

    @app.get("/api/alignments/sessions/{session_id}/stream")
    async def api_alignment_stream(
        request: Request,
        session_id: str,
        after_id: Annotated[int, Query(ge=0, le=MAX_EVENT_CURSOR_ID)] = 0,
    ) -> Response:
        ctx.svc().get_alignment_session(session_id)
        latest_event_id = _latest_alignment_event_id(ctx, session_id)
        if after_id > latest_event_id:
            return ctx.json_error("event cursor is out of range")
        after_id = _resolve_alignment_stream_after_id(
            ctx,
            request,
            session_id=session_id,
            after_id=after_id,
            latest_event_id=latest_event_id,
        )
        return StreamingResponse(
            _alignment_event_stream(ctx, session_id=session_id, after_id=after_id),
            media_type="text/event-stream",
        )


def _alignment_event_stream(ctx: WebRouteContext, *, session_id: str, after_id: int) -> Iterator[str]:
    last_id = after_id
    while True:
        try:
            events = ctx.svc().list_alignment_events(session_id, after_id=last_id)
            for event in events:
                last_id = event["id"]
                yield f"id: {event['id']}\n"
                yield f"event: {event['event_type']}\n"
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            session = ctx.svc().get_alignment_session(session_id)
        except Exception as exc:  # noqa: BLE001 - SSE streams must surface failures as stream_error events.
            log_exception(
                ctx.logger,
                "web.alignment_stream.failed",
                "Alignment event stream failed",
                error=exc,
                session_id=session_id,
                after_id=last_id,
            )
            payload = stream_error_payload(owner_key="session_id", owner_id=session_id, after_id=last_id)
            yield "event: stream_error\n"
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            break
        if session["status"] not in ALIGNMENT_ACTIVE_STATUSES and not events:
            break
        yield ": keep-alive\n\n"
        time.sleep(1)


def _latest_alignment_event_id(ctx: WebRouteContext, session_id: str) -> int:
    return max(0, int(ctx.svc().latest_alignment_event_id(session_id) or 0))


def _resolve_alignment_stream_after_id(
    ctx: WebRouteContext,
    request: Request,
    *,
    session_id: str,
    after_id: int,
    latest_event_id: int,
) -> int:
    last_event_header = str(request.headers.get("last-event-id", "")).strip()
    if not last_event_header:
        return after_id
    parsed_header = parse_sse_last_event_id(last_event_header)
    if parsed_header is None or parsed_header > latest_event_id:
        log_event(
            ctx.logger,
            logging.WARNING,
            "web.alignment_stream.resume_cursor_invalid",
            "Ignored invalid or out-of-range SSE resume cursor and kept the request cursor",
            session_id=session_id,
            after_id=after_id,
            latest_event_id=latest_event_id,
            invalid_last_event_id=last_event_header,
        )
        return after_id
    return max(after_id, parsed_header)
