from __future__ import annotations

from typing import Any

from loopora.agent_native_role_dispatch import agent_native_accepted_native_tools
from loopora.service_agent_native_contracts import (
    AGENT_NATIVE_WORKSPACE_ARTIFACT_FIELDS,
    _agent_native_schema_validation_issues,
    _agent_native_string_list,
    _agent_native_unknown_coverage_target_ids,
)
from loopora.service_types import LooporaConflictError
from loopora.structured_booleans import structured_bool_is_true


def validate_agent_native_step_output_contract(output: dict[str, Any], *, active: dict[str, Any]) -> None:
    output_schema = _agent_native_output_schema(active)
    if not output_schema:
        raise LooporaConflictError("agent-native output_schema is required")

    _agent_native_required_capsule_object(active, "judgment_contract")
    _agent_native_required_capsule_object(active, "required_coverage")
    action_policy = _agent_native_required_capsule_object(active, "action_policy")
    _validate_agent_native_action_policy(action_policy)
    _validate_agent_native_known_evidence_ids(active)

    if str(action_policy.get("workspace") or "").strip() != "workspace_write":
        workspace_fields = [field for field in AGENT_NATIVE_WORKSPACE_ARTIFACT_FIELDS if _agent_native_string_list(output.get(field))]
        if workspace_fields:
            raise LooporaConflictError(
                "agent-native read-only step cannot claim workspace artifact fields: " + ", ".join(workspace_fields)
            )

    schema_issues = _agent_native_schema_validation_issues(output, output_schema)
    if schema_issues:
        raise LooporaConflictError(
            "agent-native result does not match output_schema: "
            + "; ".join(schema_issues[:6])
            + ("..." if len(schema_issues) > 6 else "")
        )

    unknown_targets = _agent_native_unknown_coverage_target_ids(output, active=active)
    if unknown_targets:
        raise LooporaConflictError(
            "agent-native coverage_results_unknown_target_id: "
            + ", ".join(unknown_targets[:4])
            + ("..." if len(unknown_targets) > 4 else "")
        )


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
    normalized.update(dispatch_position)
    native_trace = _agent_native_dispatch_trace(adapter, dispatch=dispatch, role_dispatch=role_dispatch)
    if native_trace:
        normalized["native_trace"] = native_trace
    return normalized


def _agent_native_output_schema(active: dict[str, Any]) -> dict[str, Any]:
    capsule = active.get("capsule") if isinstance(active.get("capsule"), dict) else {}
    output_schema = capsule.get("output_schema") if isinstance(capsule.get("output_schema"), dict) else {}
    return dict(output_schema)


def _agent_native_required_capsule_object(active: dict[str, Any], field_name: str) -> dict[str, Any]:
    capsule = active.get("capsule") if isinstance(active.get("capsule"), dict) else {}
    value = capsule.get(field_name)
    if not isinstance(value, dict) or not value:
        raise LooporaConflictError(f"agent-native {field_name} is required")
    return dict(value)


def _validate_agent_native_known_evidence_ids(active: dict[str, Any]) -> None:
    capsule = active.get("capsule") if isinstance(active.get("capsule"), dict) else {}
    if "known_evidence_ids" not in capsule or not isinstance(capsule.get("known_evidence_ids"), list):
        raise LooporaConflictError("agent-native known_evidence_ids must be a list")
    if any(not isinstance(item, str) for item in capsule["known_evidence_ids"]):
        raise LooporaConflictError("agent-native known_evidence_ids must contain strings")


def _validate_agent_native_action_policy(action_policy: dict[str, Any]) -> None:
    workspace = str(action_policy.get("workspace") or "").strip()
    if workspace not in {"read_only", "workspace_write"}:
        raise LooporaConflictError("agent-native action_policy.workspace must be read_only or workspace_write")
    for field in ("can_block", "can_finish_run"):
        if not isinstance(action_policy.get(field), bool):
            raise LooporaConflictError(f"agent-native action_policy.{field} must be a literal boolean")


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
    capsule = active.get("capsule") if isinstance(active.get("capsule"), dict) else {}
    role_dispatch = capsule.get("role_dispatch") if isinstance(capsule.get("role_dispatch"), dict) else {}
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


def _agent_native_expected_dispatch_int(active: dict[str, Any], active_field: str, capsule_field: str) -> int | None:
    value = active.get(active_field)
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    capsule = active.get("capsule") if isinstance(active.get("capsule"), dict) else {}
    value = capsule.get(capsule_field)
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None
