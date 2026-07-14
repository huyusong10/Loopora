from __future__ import annotations

from collections.abc import Mapping

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response

from loopora.asset_errors import asset_mutation_error_message
from loopora.agent_entry_run_projection import AGENT_NATIVE_WEB_START_ERROR
from loopora.service import LooporaError
from loopora.service_types import LooporaWorkdirUnavailableError
from loopora.spec_recovery_commands import effective_spec_init_strategy_context
from loopora.specs import SpecError
from loopora.web_run_dispatch import (
    is_background_worker_start_error,
    redirect_to_loop_start_error,
    redirect_to_run_action_error,
    start_run_async_error,
)
from loopora.web_workdir_recovery import (
    browser_recovery_submit_payload,
    web_alignment_workdir_ready,
    web_loop_create_spec_ready,
    web_loop_create_spec_recovery_payload,
    web_loop_create_workdir_recovery_payload,
    web_loop_start_workdir_recovery_payload,
)
from loopora.web_loop_inputs import (
    _loop_payload_from_mapping,
    _loop_strategy_preset_from_mapping,
    _loop_strategy_source_from_mapping,
    _normalize_loop_form,
    validate_loop_payload_compose_options,
)
from loopora.web_route_context import WebRouteContext
from loopora.web_start_context import request_workdir_context
from loopora.web_start_context import request_workdir_context_href
from loopora.web_start_context import request_resource_workdir_context_href
from loopora.web_start_context import resource_workdir_context


def register_loop_form_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.post("/loops/{loop_id}/runs")
    async def start_loop_run_from_form(request: Request, loop_id: str):
        return _start_loop_run_from_form_response(ctx, request, loop_id)

    @app.post("/loops/new/manual")
    @app.post("/loops/new")
    async def create_loop_from_form(request: Request):
        return await _create_loop_from_form_response(ctx, request)


def _start_loop_run_from_form_response(ctx: WebRouteContext, request: Request, loop_id: str) -> Response:
    agent_entry_start = ctx.svc().agent_entry_loop_start_projection(loop_id)
    if agent_entry_start:
        return redirect_to_loop_start_error(
            loop_id,
            AGENT_NATIVE_WEB_START_ERROR,
            workdir_context=request_workdir_context(request),
        )
    try:
        run = ctx.svc().start_next_run(loop_id)
        dispatch_response = _run_dispatch_form_error_response(ctx, request, loop_id, run)
        if dispatch_response is not None:
            return dispatch_response
    except LooporaWorkdirUnavailableError as exc:
        recovery = _browser_loop_start_recovery(
            request,
            loop_id,
            web_loop_start_workdir_recovery_payload(loop_id, exc.workdir),
        )
        return ctx.render_loop_detail(
            request,
            loop_id,
            run_start_error=str(recovery.get("error") or recovery.get("summary") or ""),
            run_start_recovery=recovery,
        )
    except LooporaError as exc:
        return redirect_to_loop_start_error(loop_id, str(exc), workdir_context=request_workdir_context(request))
    return RedirectResponse(url=request_resource_workdir_context_href(request, f"/runs/{run['id']}", run), status_code=303)


async def _create_loop_from_form_response(ctx: WebRouteContext, request: Request) -> Response:
    form = await request.form()
    values = _normalize_loop_form(form)
    try:
        validate_loop_payload_compose_options(form)
        recovery_response = _loop_create_form_recovery_response(ctx, request, form, values)
        if recovery_response is not None:
            return recovery_response
        loop_kwargs, start_immediately = _loop_payload_from_mapping(form)
        loop = ctx.svc().create_loop(**loop_kwargs)
        if start_immediately:
            return _created_loop_form_start_response(ctx, request, loop)
        return RedirectResponse(url=request_resource_workdir_context_href(request, f"/loops/{loop['id']}", loop), status_code=303)
    except LooporaWorkdirUnavailableError as exc:
        recovery = _browser_manual_loop_recovery(request, web_loop_create_workdir_recovery_payload(exc.workdir))
        return ctx.render_new_loop(
            request,
            page_mode="manual",
            values=values,
            form_error=str(recovery.get("error") or recovery.get("summary") or ""),
            form_recovery=recovery,
        )
    except (LooporaError, SpecError, FileExistsError, OSError, ValueError) as exc:
        return ctx.render_new_loop(
            request,
            page_mode="manual",
            values=values,
            form_error=asset_mutation_error_message(exc, asset_label="Loop", action="created"),
        )


def _loop_create_form_recovery_response(
    ctx: WebRouteContext,
    request: Request,
    payload: Mapping[str, object],
    values: dict[str, object],
) -> Response | None:
    workdir_text = str(values.get("workdir", "")).strip()
    if not web_alignment_workdir_ready(workdir_text):
        recovery = _browser_manual_loop_recovery(request, web_loop_create_workdir_recovery_payload(workdir_text))
        return ctx.render_new_loop(
            request,
            page_mode="manual",
            values=values,
            form_error=str(recovery.get("error") or recovery.get("summary") or ""),
            form_recovery=recovery,
        )
    spec_path_text = str(values.get("spec_path", "")).strip()
    if not web_loop_create_spec_ready(spec_path_text):
        recovery = _browser_manual_loop_recovery(
            request,
            web_loop_create_spec_recovery_payload(
                spec_path_text,
                orchestration_id=values.get("orchestration_id", ""),
                strategy_preset=_loop_strategy_preset_from_mapping(payload),
                strategy_context=effective_spec_init_strategy_context(
                    orchestration_id=values.get("orchestration_id", ""),
                    strategy_preset=_loop_strategy_preset_from_mapping(payload),
                    strategy_source=_loop_strategy_source_from_mapping(payload),
                ),
            ),
        )
        return ctx.render_new_loop(
            request,
            page_mode="manual",
            values=values,
            form_error=str(recovery.get("error") or recovery.get("summary") or ""),
            form_recovery=recovery,
        )
    return None


def _browser_manual_loop_recovery(request: Request, recovery: dict[str, object]) -> dict[str, object]:
    return browser_recovery_submit_payload(
        recovery,
        form_id="new-loop-form",
        form_action=request_workdir_context_href(request, "/loops/new/manual"),
        action_kinds=("retry_web_compose",),
    )


def _browser_loop_start_recovery(request: Request, loop_id: str, recovery: dict[str, object]) -> dict[str, object]:
    return browser_recovery_submit_payload(
        recovery,
        form_id="loop-start-run-retry-form",
        form_action=request_workdir_context_href(request, f"/loops/{loop_id}/runs"),
        action_kinds=("retry_web_run_start",),
    )


def _created_loop_form_start_response(ctx: WebRouteContext, request: Request, loop: dict) -> RedirectResponse:
    run = ctx.svc().start_run(str(loop["id"]))
    dispatch_response = _run_dispatch_form_error_response(ctx, request, str(loop["id"]), run)
    if dispatch_response is not None:
        return dispatch_response
    return RedirectResponse(url=request_resource_workdir_context_href(request, f"/runs/{run['id']}", run, loop), status_code=303)


def _run_dispatch_form_error_response(
    ctx: WebRouteContext,
    request: Request,
    loop_id: str,
    run: dict,
) -> RedirectResponse | None:
    dispatch_error = start_run_async_error(ctx.svc(), run)
    if dispatch_error is None:
        return None
    if is_background_worker_start_error(dispatch_error):
        return redirect_to_run_action_error(
            str(run["id"]),
            str(dispatch_error),
            workdir_context=resource_workdir_context(run, fallback=request_workdir_context(request)),
        )
    return redirect_to_loop_start_error(
        loop_id,
        str(dispatch_error),
        workdir_context=resource_workdir_context(run, fallback=request_workdir_context(request)),
    )
