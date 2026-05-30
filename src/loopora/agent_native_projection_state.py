from __future__ import annotations

from typing import Any


def agent_native_active_step_is_stale(active: dict[str, Any], current_step_projection: dict[str, Any]) -> bool:
    source_sequence = _safe_int(current_step_projection.get("source_sequence"))
    if source_sequence <= 0:
        return False
    capsule = active.get("capsule") if isinstance(active.get("capsule"), dict) else {}
    active_step = active.get("step") if isinstance(active.get("step"), dict) else {}
    active_step_id = str(active_step.get("id") or capsule.get("step_id") or "").strip()
    active_iter = _safe_int(_first_present(active.get("iter_id"), capsule.get("iter")), default=-1)
    active_adapter = str(capsule.get("adapter") or active.get("adapter") or "").strip()
    projected_step_id = str(current_step_projection.get("step_id") or "").strip()
    projected_iter = _safe_int(current_step_projection.get("iteration"), default=-1)
    if not current_step_projection.get("claimable"):
        return bool(active_step_id)
    if active_step_id != projected_step_id or active_iter != projected_iter:
        return True
    pending_actor = current_step_projection.get("pending_actor") if isinstance(current_step_projection.get("pending_actor"), dict) else {}
    projected_adapter = str(pending_actor.get("adapter") or pending_actor.get("id") or "").strip()
    return bool(active_adapter and projected_adapter and active_adapter != projected_adapter)


def _safe_int(value: object, *, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _first_present(*values: object) -> object:
    return next((value for value in values if value is not None and value != ""), None)
