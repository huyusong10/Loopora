from __future__ import annotations

from typing import Any

from loopora.structured_numbers import coerced_int

AGENT_NATIVE_STEP_VIEW_KEY = "agent_step_view"


def agent_native_active_step_is_stale(active: dict[str, Any], current_step_projection: dict[str, Any]) -> bool:
    source_sequence = coerced_int(current_step_projection.get("source_sequence"))
    if source_sequence <= 0:
        return False
    step_view = agent_native_active_step_view(active)
    active_step = active.get("step") if isinstance(active.get("step"), dict) else {}
    active_step_id = str(active_step.get("id") or step_view.get("step_id") or "").strip()
    active_iter = coerced_int(_first_present(active.get("iter_id"), step_view.get("iter")), default=-1)
    active_adapter = str(step_view.get("adapter") or active.get("adapter") or "").strip()
    projected_step_id = str(current_step_projection.get("step_id") or "").strip()
    projected_iter = coerced_int(current_step_projection.get("iteration"), default=-1)
    if not current_step_projection.get("claimable"):
        return bool(active_step_id)
    if active_step_id != projected_step_id or active_iter != projected_iter:
        return True
    pending_actor = current_step_projection.get("pending_actor") if isinstance(current_step_projection.get("pending_actor"), dict) else {}
    projected_adapter = str(pending_actor.get("adapter") or pending_actor.get("id") or "").strip()
    return bool(active_adapter and projected_adapter and active_adapter != projected_adapter)


def agent_native_active_step_view(active: dict[str, Any]) -> dict[str, Any]:
    step_view = agent_native_active_step_view_payload(active)
    return dict(step_view) if isinstance(step_view, dict) else {}


def agent_native_active_step_view_payload(active: dict[str, Any]) -> object:
    return active.get(AGENT_NATIVE_STEP_VIEW_KEY)


def agent_native_active_step_view_fields(step_view: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {AGENT_NATIVE_STEP_VIEW_KEY: step_view}


def _first_present(*values: object) -> object:
    return next((value for value in values if value is not None and value != ""), None)
