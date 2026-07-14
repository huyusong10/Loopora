from __future__ import annotations

from typing import Any

from loopora.agent_native_projection_state import agent_native_active_step_view
from loopora.agent_native_role_dispatch import agent_native_accepted_native_tools
from loopora.service_types import LooporaConflictError
from loopora.structured_booleans import structured_bool_is_true


EXPLICIT_HOST_DISPATCH_ATTESTATION_SOURCE = "explicit_submit_flag"
LEGACY_HOST_DISPATCH_ATTESTATION_SOURCE = "legacy_template_auto_repair"
HOST_DISPATCH_ATTESTATION_SOURCES = {
    EXPLICIT_HOST_DISPATCH_ATTESTATION_SOURCE,
    LEGACY_HOST_DISPATCH_ATTESTATION_SOURCE,
}


def validate_agent_native_host_dispatch(context: dict[str, Any], dispatch: dict[str, Any] | None) -> dict[str, Any]:
    adapter = str(context["adapter"])
    run = context["run"]
    step_id = str(context["step_id"])
    active = context["active"]
    role_dispatch = _agent_native_role_dispatch_for_submit(active)
    if not isinstance(dispatch, dict) or not dispatch:
        raise LooporaConflictError("agent-native submit requires loopora_host_dispatch proof from the host native role agent")

    expected_agent = str(role_dispatch.get("target_agent") or "").strip()
    accepted_modes = {str(item) for item in list(role_dispatch.get("accepted_dispatch_modes") or []) if str(item).strip()}
    actual_agent = str(dispatch.get("actual_agent") or dispatch.get("agent_name") or "").strip()
    target_agent = str(dispatch.get("target_agent") or "").strip()
    dispatch_mode = str(dispatch.get("dispatch_mode") or dispatch.get("mode") or "").strip()
    if not isinstance(dispatch.get("inline"), bool):
        raise LooporaConflictError("agent-native host dispatch inline must be a literal boolean")
    inline = dispatch["inline"]

    if actual_agent != expected_agent or target_agent != expected_agent:
        raise LooporaConflictError(f"agent-native submit used {actual_agent or target_agent or 'unknown'} but expected {expected_agent}")
    if accepted_modes and dispatch_mode not in accepted_modes:
        raise LooporaConflictError(f"agent-native submit dispatch_mode must be one of {sorted(accepted_modes)}")
    if inline and not structured_bool_is_true(role_dispatch.get("inline_allowed")):
        raise LooporaConflictError("agent-native submit cannot claim inline role execution for this step")

    dispatch_run_id = _required_agent_native_dispatch_text(dispatch, "run_id")
    dispatch_step_id = _required_agent_native_dispatch_text(dispatch, "step_id")
    dispatch_adapter = _required_agent_native_dispatch_text(dispatch, "adapter")
    if dispatch_run_id != str(run["id"]):
        raise LooporaConflictError("agent-native host dispatch run_id does not match the submitted run")
    if dispatch_step_id != step_id:
        raise LooporaConflictError("agent-native host dispatch step_id does not match the submitted step")
    if dispatch_adapter != adapter:
        raise LooporaConflictError("agent-native host dispatch adapter does not match the submitted adapter")
    dispatch_position = _agent_native_dispatch_position(active, dispatch)
    _reject_unavailable_role_output_claim(dispatch)

    normalized = {
        "schema_version": _agent_native_dispatch_schema_version(dispatch),
        "adapter": adapter,
        "run_id": str(run["id"]),
        "step_id": step_id,
        "target_agent": expected_agent,
        "actual_agent": actual_agent,
        "dispatch_mode": dispatch_mode,
        "inline": inline,
        "attestation": str(dispatch.get("attestation") or "").strip(),
    }
    _attach_agent_native_attestation_source(normalized, dispatch)
    normalized.update(dispatch_position)
    native_trace = _agent_native_dispatch_trace(adapter, dispatch=dispatch, role_dispatch=role_dispatch)
    if native_trace:
        normalized["native_trace"] = native_trace
    return normalized


def _attach_agent_native_attestation_source(normalized: dict[str, Any], dispatch: dict[str, Any]) -> None:
    source = str(dispatch.get("attestation_source") or "").strip()
    if source and source not in HOST_DISPATCH_ATTESTATION_SOURCES:
        raise LooporaConflictError(
            "agent-native host dispatch attestation_source must be one of "
            f"{sorted(HOST_DISPATCH_ATTESTATION_SOURCES)}"
        )
    if source:
        normalized["attestation_source"] = source


def _required_agent_native_dispatch_text(dispatch: dict[str, Any], field: str) -> str:
    value = str(dispatch.get(field) or "").strip()
    if not value:
        raise LooporaConflictError(f"agent-native host dispatch {field} is required")
    return value


def _required_agent_native_dispatch_int(dispatch: dict[str, Any], field: str) -> int:
    value = dispatch.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise LooporaConflictError(f"agent-native host dispatch {field} is required")
    return value


def _agent_native_dispatch_schema_version(dispatch: dict[str, Any]) -> int:
    value = dispatch.get("schema_version")
    if value is None or value == "":
        return 1
    if isinstance(value, bool) or not isinstance(value, int):
        raise LooporaConflictError("agent-native host dispatch schema_version must be an integer")
    return value


def _agent_native_role_dispatch_for_submit(active: dict[str, Any]) -> dict[str, Any]:
    step_view = agent_native_active_step_view(active)
    role_dispatch = step_view.get("role_dispatch") if isinstance(step_view.get("role_dispatch"), dict) else {}
    if not role_dispatch:
        raise LooporaConflictError("agent-native role_dispatch is required")
    if not structured_bool_is_true(role_dispatch.get("required")):
        raise LooporaConflictError("agent-native role_dispatch.required must be literal true")
    if not isinstance(role_dispatch.get("inline_allowed"), bool):
        raise LooporaConflictError("agent-native role_dispatch.inline_allowed must be a literal boolean")
    if not str(role_dispatch.get("target_agent") or "").strip():
        raise LooporaConflictError("agent-native role_dispatch.target_agent is required")
    accepted_modes = role_dispatch.get("accepted_dispatch_modes")
    if not isinstance(accepted_modes, list) or not any(str(item).strip() for item in accepted_modes):
        raise LooporaConflictError("agent-native role_dispatch.accepted_dispatch_modes must be a non-empty list")
    return role_dispatch


def _agent_native_dispatch_trace(
    adapter: str,
    *,
    dispatch: dict[str, Any],
    role_dispatch: dict[str, Any],
) -> dict[str, Any]:
    trace_payload = dispatch.get("native_trace") if isinstance(dispatch.get("native_trace"), dict) else {}
    accepted_tools = [
        str(item).strip()
        for item in list(role_dispatch.get("accepted_native_tools") or agent_native_accepted_native_tools(adapter))
        if str(item).strip()
    ]
    accepted_tool_set = {item.lower() for item in accepted_tools}
    tool_name = _agent_native_optional_dispatch_text(dispatch.get("native_tool_name") or dispatch.get("tool_name") or trace_payload.get("tool_name"))
    trace_ref = _agent_native_optional_dispatch_text(dispatch.get("native_trace_ref") or trace_payload.get("event_ref"))
    trace: dict[str, Any] = {}
    if tool_name:
        trace["tool_name"] = tool_name
        if accepted_tool_set:
            trace["official_tool_match"] = tool_name.lower() in accepted_tool_set
            trace["accepted_native_tools"] = accepted_tools
    if trace_ref:
        trace["trace_ref"] = trace_ref
    if isinstance(trace_payload.get("available"), bool):
        trace["available"] = trace_payload["available"]
    for source_key, target_key in (
        ("tool_call_id", "tool_call_id"),
        ("parent_tool_use_id", "parent_tool_use_id"),
        ("subagent_run_id", "subagent_run_id"),
        ("event_ref", "event_ref"),
        ("transcript_ref", "transcript_ref"),
        ("notes", "notes"),
    ):
        value = _agent_native_optional_dispatch_text(trace_payload.get(source_key))
        if value:
            trace[target_key] = value
    if trace and "available" not in trace:
        trace["available"] = True
    return trace


def _reject_unavailable_role_output_claim(dispatch: dict[str, Any]) -> None:
    claim_text = _agent_native_dispatch_claim_text(dispatch)
    if not claim_text:
        return
    role_output_unavailable = any(
        phrase in claim_text
        for phrase in (
            "returned no output",
            "returned no structured output",
            "no structured output",
            "role output unavailable",
            "without role output",
            "role agent output unavailable",
            "subagent output unavailable",
        )
    )
    main_constructed_result = (
        any(actor in claim_text for actor in ("main session", "main orchestrator", "orchestrator session"))
        and any(phrase in claim_text for phrase in ("constructed the wrapper", "constructed wrapper", "constructed the result"))
    )
    if role_output_unavailable or main_constructed_result:
        raise LooporaConflictError(
            "agent-native host dispatch role agent output is unavailable; do not submit main-session reconstructed role proof"
        )


def _agent_native_dispatch_claim_text(dispatch: dict[str, Any]) -> str:
    trace_payload = dispatch.get("native_trace") if isinstance(dispatch.get("native_trace"), dict) else {}
    parts = [
        dispatch.get("attestation"),
        dispatch.get("notes"),
        trace_payload.get("notes"),
    ]
    return " ".join(" ".join(str(part or "").split()).lower() for part in parts if str(part or "").strip())


def _agent_native_optional_dispatch_text(value: object, *, limit: int = 320) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text[:limit]


def _agent_native_dispatch_position(active: dict[str, Any], dispatch: dict[str, Any]) -> dict[str, int]:
    position: dict[str, int] = {}
    expected_iter = _agent_native_expected_dispatch_int(active, "iter_id", "iter")
    expected_step_order = _agent_native_expected_dispatch_int(active, "step_order", "step_order")
    if expected_iter is not None:
        dispatch_iter = _required_agent_native_dispatch_int(dispatch, "iter")
        if dispatch_iter != expected_iter:
            raise LooporaConflictError("agent-native host dispatch iter does not match the claimed agent-native step")
        position["iter"] = expected_iter
    if expected_step_order is not None:
        dispatch_step_order = _required_agent_native_dispatch_int(dispatch, "step_order")
        if dispatch_step_order != expected_step_order:
            raise LooporaConflictError("agent-native host dispatch step_order does not match the claimed agent-native step")
        position["step_order"] = expected_step_order
    return position


def _agent_native_expected_dispatch_int(active: dict[str, Any], active_field: str, step_view_field: str) -> int | None:
    value = active.get(active_field)
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    step_view = agent_native_active_step_view(active)
    value = step_view.get(step_view_field)
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None
