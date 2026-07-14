from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from loopora.agent_adapter_check_utils import adapter_label
from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.agent_adapter_current_host import current_agent_host_detection
from loopora.agent_adapter_workdir_recovery import (
    AdapterWorkdirRetryPolicy,
    adapter_workdir_recovery_payload,
    adapter_workdir_state,
)
from loopora.agent_native_adapter_contracts import AGENT_ADAPTER_KINDS, normalize_agent_adapter_kind
from loopora.service import LooporaError
from loopora.web_route_context import WebRouteContext


def register_agent_adapter_api_routes(app: FastAPI, ctx: WebRouteContext) -> None:
    @app.get("/api/agent-adapters")
    async def api_list_agent_adapters(workdir: str = "") -> JSONResponse:
        return _list_agent_adapters_response(ctx, workdir)

    @app.get("/api/agent-adapters/{adapter}")
    async def api_get_agent_adapter(adapter: str, workdir: str = "") -> JSONResponse:
        return _get_agent_adapter_response(ctx, adapter=adapter, workdir=workdir)

    @app.post("/api/agent-adapters/{adapter}/install")
    async def api_install_agent_adapter(adapter: str, request: Request) -> JSONResponse:
        return await _mutate_agent_adapter(ctx, adapter=adapter, request=request, action="install")

    @app.post("/api/agent-adapters/{adapter}/uninstall")
    async def api_uninstall_agent_adapter(adapter: str, request: Request) -> JSONResponse:
        return await _mutate_agent_adapter(ctx, adapter=adapter, request=request, action="uninstall")

    @app.post("/api/agent-adapters/{adapter}/uninstall-preview")
    async def api_preview_uninstall_agent_adapter(adapter: str, request: Request) -> JSONResponse:
        return await _mutate_agent_adapter(ctx, adapter=adapter, request=request, action="uninstall_preview")


def _list_agent_adapters_response(ctx: WebRouteContext, workdir: str) -> JSONResponse:
    if not str(workdir or "").strip():
        return JSONResponse(_target_required_agent_adapter_list_payload())
    workdir_error = _adapter_workdir_error(workdir)
    if workdir_error is not None:
        return workdir_error
    root = _adapter_workdir(workdir)
    try:
        result = {
            "workdir": str(root),
            "current_agent_host": current_agent_host_detection(),
            "adapters": ctx.svc().list_agent_adapters(workdir=root),
        }
    except LooporaError as exc:
        return ctx.json_error_from_exception(exc)
    return JSONResponse(_web_agent_adapter_payload(result))


def _get_agent_adapter_response(ctx: WebRouteContext, *, adapter: str, workdir: str) -> JSONResponse:
    if not str(workdir or "").strip():
        return _target_required_agent_adapter_response(ctx, adapter)
    workdir_error = _adapter_workdir_error(workdir)
    if workdir_error is not None:
        return workdir_error
    root = _adapter_workdir(workdir)
    try:
        result = ctx.svc().get_agent_adapter(adapter, workdir=root)
    except LooporaError as exc:
        return ctx.json_error_from_exception(exc)
    return JSONResponse(_web_agent_adapter_payload(result))


async def _mutate_agent_adapter(ctx: WebRouteContext, *, adapter: str, request: Request, action: str) -> JSONResponse:
    try:
        payload = await ctx.read_json_mapping(request)
        workdir_error = _adapter_workdir_error(payload.get("workdir"))
        if workdir_error is not None:
            return workdir_error
        state = adapter_workdir_state(payload.get("workdir"))
        recovery_action = "uninstall" if action == "uninstall_preview" else action
        recovery = _adapter_workdir_recovery_response(adapter, action=recovery_action, workdir_state=state)
        if recovery is not None:
            return recovery
        root = Path(str(state["workdir"]))
        if action == "install":
            mutate = ctx.svc().install_agent_adapter
        elif action == "uninstall_preview":
            mutate = ctx.svc().preview_agent_adapter_uninstall
        else:
            mutate = ctx.svc().uninstall_agent_adapter
        result = mutate(adapter, workdir=root)
    except LooporaError as exc:
        return ctx.json_error_from_exception(exc)
    return JSONResponse(_web_agent_adapter_payload(result))


def _adapter_workdir(value: str) -> Path:
    raw = str(value or "").strip()
    if not raw:
        raise LooporaError("target project directory is required")
    return Path(raw).expanduser().resolve()


def _adapter_workdir_error(value: object) -> JSONResponse | None:
    raw = str(value or "").strip()
    if not raw or Path(raw).expanduser().is_absolute():
        return None
    return JSONResponse(
        {
            "error": "target_project_absolute_path_required",
            "message": "Use a server-side absolute target project path for Agent adapter status and mutations.",
            "target_project_required": True,
            "recovery_action": "choose_target_project",
            "next_action_kind": "choose_workdir",
        },
        status_code=400,
    )


def _target_required_agent_adapter_list_payload() -> dict[str, Any]:
    state = adapter_workdir_state(None)
    return {
        "workdir": "",
        "target_project_required": True,
        "workdir_state": state,
        "current_agent_host": current_agent_host_detection(),
        "adapters": [_target_required_agent_adapter_status(adapter, workdir_state=state) for adapter in AGENT_ADAPTER_KINDS],
        "next_actions": _target_required_agent_adapter_actions(),
    }


def _target_required_agent_adapter_response(ctx: WebRouteContext, adapter: str) -> JSONResponse:
    try:
        payload = _target_required_agent_adapter_payload(adapter)
    except LooporaError as exc:
        return ctx.json_error_from_exception(exc)
    return JSONResponse(payload)


def _target_required_agent_adapter_payload(adapter: str) -> dict[str, Any]:
    state = adapter_workdir_state(None)
    kind = normalize_agent_adapter_kind(adapter)
    return {
        **_target_required_agent_adapter_status(kind, workdir_state=state),
        "target_project_required": True,
        "workdir_state": state,
        "next_actions": _target_required_agent_adapter_actions(),
    }


def _target_required_agent_adapter_status(adapter: str, *, workdir_state: dict[str, object]) -> dict[str, Any]:
    return {
        "adapter": adapter,
        "label": adapter_label(adapter),
        "workdir": "",
        "implemented": True,
        "status": "blocked_by_workdir",
        "summary": str(workdir_state.get("summary") or ""),
        "managed_files": [],
        "manifest_path": "",
        "error": "",
    }


def _target_required_agent_adapter_actions() -> list[dict[str, object]]:
    return [
        {
            "kind": "choose_workdir",
            "command_ready": False,
            "command_blockers": ["target_project_required"],
        }
    ]


def _web_agent_adapter_payload(payload: dict[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    adapters = result.get("adapters")
    if isinstance(adapters, list):
        result["adapters"] = [_web_agent_adapter_payload(item) if isinstance(item, dict) else item for item in adapters]
    policy = result.get("first_task_handoff_policy")
    if isinstance(policy, dict):
        result["first_task_handoff_policy"] = _copyable_first_task_handoff_policy(policy)
    return result


def _copyable_first_task_handoff_policy(policy: dict[str, Any]) -> dict[str, str]:
    result = {str(key): str(value) for key, value in policy.items() if str(value or "").strip()}
    raw_fit_command = result.get("fit_command", "").strip()
    if not raw_fit_command:
        return result
    fit_command = copyable_loopora_command(raw_fit_command)
    result["fit_command"] = fit_command
    result["copy_rule"] = result.get("copy_rule", "").replace(raw_fit_command, fit_command)
    return result


def _adapter_workdir_recovery_response(
    adapter: str,
    *,
    action: str,
    workdir_state: dict[str, object],
) -> JSONResponse | None:
    if workdir_state["status"] == "ready":
        return None
    payload = adapter_workdir_recovery_payload(
        adapter,
        action=action,
        workdir_state=workdir_state,
        retry_policy=AdapterWorkdirRetryPolicy(before_readiness=True),
    )
    return JSONResponse(payload, status_code=400)
