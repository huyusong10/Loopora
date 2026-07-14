from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi.responses import RedirectResponse

from loopora.action_readiness_projection import project_next_action_readiness_contract
from loopora.run_result_recording import run_result_is_lifecycle_failure
from loopora.run_worker_start import BACKGROUND_WORKER_START_ERROR
from loopora.service_types import LooporaError
from loopora.web_start_context import workdir_context_href
from loopora.web_url_utils import with_query_params


def start_run_async_error(service: Any, run: Mapping[str, object]) -> LooporaError | None:
    try:
        service.start_run_async(str(run["id"]))
    except LooporaError as exc:
        return exc
    return None


def is_background_worker_start_error(exc: BaseException) -> bool:
    return isinstance(exc, LooporaError) and str(exc) == BACKGROUND_WORKER_START_ERROR


def redirect_to_run_action_error(run_id: str, error: str, *, workdir_context: str = "") -> RedirectResponse:
    return RedirectResponse(
        url=with_query_params(workdir_context_href(f"/runs/{run_id}", workdir_context), run_action_error=error),
        status_code=303,
    )


def redirect_to_loop_start_error(loop_id: str, error: str, *, workdir_context: str = "") -> RedirectResponse:
    return RedirectResponse(
        url=with_query_params(workdir_context_href(f"/loops/{loop_id}", workdir_context), run_start_error=error),
        status_code=303,
    )


def web_run_start_failure_payload(
    run: Mapping[str, object],
    *,
    loop: Mapping[str, object] | None = None,
    redirect_url: str = "",
    action: str = "start_run",
    include_error: bool = True,
) -> dict[str, object]:
    run_payload = dict(run)
    run_id = str(run_payload.get("id") or "").strip()
    loop_id = str(run_payload.get("loop_id") or (loop or {}).get("id") or "").strip()
    next_action = _web_run_start_retry_action(loop_id, action=action)
    if run_result_is_lifecycle_failure(run_payload):
        run_payload["status_label"] = "run_start_failed"
        run_payload["run_recovery"] = "retry_run_start"
        run_payload["next_actions"] = _append_next_action(run_payload.get("next_actions"), next_action)
        project_next_action_readiness_contract(run_payload)
    next_actions = [next_action]
    target_redirect_url = redirect_url or _run_failure_redirect_url(
        run_id,
        workdir_context=_run_failure_workdir_context(run_payload, loop=loop),
    )
    payload: dict[str, object] = {
        "web_run_start_recovery_summary": {
            "ready": False,
            "run_recovery": "retry_run_start",
            "run_start_error": BACKGROUND_WORKER_START_ERROR,
            "run_id": run_id,
            "loop_id": loop_id,
            "redirect_url": target_redirect_url,
            "next_action_kinds": _web_action_kinds(next_actions),
        },
        "run_start_error": BACKGROUND_WORKER_START_ERROR,
        "run_recovery": "retry_run_start",
        "run": run_payload,
        "next_actions": next_actions,
    }
    if include_error:
        payload["error"] = BACKGROUND_WORKER_START_ERROR
    if loop is not None:
        payload["loop"] = dict(loop)
    if target_redirect_url:
        payload["redirect_url"] = target_redirect_url
    project_next_action_readiness_contract(payload, summary_key="web_run_start_recovery_summary")
    return payload


def _web_run_start_retry_action(loop_id: str, *, action: str) -> dict[str, str]:
    retry_action = {
        "kind": "retry_web_run_start",
        "target": "web_loop_start",
        "action": action,
    }
    if loop_id:
        retry_action["loop_id"] = loop_id
    return retry_action


def _append_next_action(existing_actions: object, next_action: dict[str, str]) -> list[object]:
    if isinstance(existing_actions, list):
        return [*existing_actions, next_action]
    return [next_action]


def _web_action_kinds(actions: list[dict[str, str]]) -> list[str]:
    return [str(action.get("kind") or "").strip() for action in actions if str(action.get("kind") or "").strip()]


def _run_failure_workdir_context(
    run: Mapping[str, object],
    *,
    loop: Mapping[str, object] | None,
) -> str:
    return str(run.get("workdir") or (loop or {}).get("workdir") or "").strip()


def _run_failure_redirect_url(run_id: str, *, workdir_context: str = "") -> str:
    if not run_id:
        return ""
    return with_query_params(
        workdir_context_href(f"/runs/{run_id}", workdir_context),
        run_action_error=BACKGROUND_WORKER_START_ERROR,
    )
