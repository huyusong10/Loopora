from __future__ import annotations

from typing import Any

from loopora.agent_native_projection_state import agent_native_active_step_view
from loopora.agent_native_result_schema import agent_native_schema_validation_issues
from loopora.agent_native_evidence_contracts import (
    AGENT_NATIVE_WORKSPACE_ARTIFACT_FIELDS,
    _agent_native_string_list,
    _agent_native_unknown_coverage_target_ids,
)
from loopora.agent_native_host_dispatch_validation import (
    validate_agent_native_host_dispatch as validate_agent_native_host_dispatch,
)
from loopora.service_types import LooporaConflictError


def validate_agent_native_step_output_contract(output: dict[str, Any], *, active: dict[str, Any]) -> None:
    output_schema = _agent_native_output_schema(active)
    if not output_schema:
        raise LooporaConflictError("agent-native output_schema is required")

    _agent_native_required_step_view_object(active, "judgment_contract")
    _agent_native_required_step_view_object(active, "required_coverage")
    action_policy = _agent_native_required_step_view_object(active, "action_policy")
    _validate_agent_native_action_policy(action_policy)
    _validate_agent_native_known_evidence_ids(active)

    if str(action_policy.get("workspace") or "").strip() != "workspace_write":
        workspace_fields = [field for field in AGENT_NATIVE_WORKSPACE_ARTIFACT_FIELDS if _agent_native_string_list(output.get(field))]
        if workspace_fields:
            raise LooporaConflictError(
                "agent-native read-only step cannot claim workspace artifact fields: " + ", ".join(workspace_fields)
            )

    schema_issues = agent_native_schema_validation_issues(output, output_schema)
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


def _agent_native_output_schema(active: dict[str, Any]) -> dict[str, Any]:
    step_view = agent_native_active_step_view(active)
    output_schema = step_view.get("output_schema") if isinstance(step_view.get("output_schema"), dict) else {}
    return dict(output_schema)


def _agent_native_required_step_view_object(active: dict[str, Any], field_name: str) -> dict[str, Any]:
    step_view = agent_native_active_step_view(active)
    value = step_view.get(field_name)
    if not isinstance(value, dict) or not value:
        raise LooporaConflictError(f"agent-native {field_name} is required")
    return dict(value)


def _validate_agent_native_known_evidence_ids(active: dict[str, Any]) -> None:
    step_view = agent_native_active_step_view(active)
    if "known_evidence_ids" not in step_view or not isinstance(step_view.get("known_evidence_ids"), list):
        raise LooporaConflictError("agent-native known_evidence_ids must be a list")
    if any(not isinstance(item, str) for item in step_view["known_evidence_ids"]):
        raise LooporaConflictError("agent-native known_evidence_ids must contain strings")


def _validate_agent_native_action_policy(action_policy: dict[str, Any]) -> None:
    workspace = str(action_policy.get("workspace") or "").strip()
    if workspace not in {"read_only", "workspace_write"}:
        raise LooporaConflictError("agent-native action_policy.workspace must be read_only or workspace_write")
    for field in ("can_block", "can_finish_run"):
        if not isinstance(action_policy.get(field), bool):
            raise LooporaConflictError(f"agent-native action_policy.{field} must be a literal boolean")
