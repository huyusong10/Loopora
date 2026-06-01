from __future__ import annotations

"""Strategy Source run-control normalization rules."""

import re
from collections.abc import Mapping
from typing import Any

from loopora.strategy_source_errors import WorkflowError
from loopora.strategy_source_validation import (
    normalize_optional_strategy_source_identifier,
    normalize_strategy_source_identifier,
    unknown_keys,
)

STRATEGY_SOURCE_CONTROL_KEYS = {"id", "when", "call", "mode", "max_fires_per_run"}
STRATEGY_SOURCE_CONTROL_WHEN_KEYS = {"signal", "after"}
STRATEGY_SOURCE_CONTROL_CALL_KEYS = {"role_id"}
STRATEGY_SOURCE_CONTROL_SIGNALS = {"no_evidence_progress", "role_timeout", "step_failed", "gatekeeper_rejected"}
STRATEGY_SOURCE_CONTROL_MODES = {"advisory", "blocking", "repair_guidance"}
STRATEGY_SOURCE_CONTROL_ARCHETYPES = {"inspector", "guide", "gatekeeper"}
WORKFLOW_CONTROL_KEYS = STRATEGY_SOURCE_CONTROL_KEYS
WORKFLOW_CONTROL_WHEN_KEYS = STRATEGY_SOURCE_CONTROL_WHEN_KEYS
WORKFLOW_CONTROL_CALL_KEYS = STRATEGY_SOURCE_CONTROL_CALL_KEYS
WORKFLOW_CONTROL_SIGNALS = STRATEGY_SOURCE_CONTROL_SIGNALS
WORKFLOW_CONTROL_MODES = STRATEGY_SOURCE_CONTROL_MODES
WORKFLOW_CONTROL_ARCHETYPES = STRATEGY_SOURCE_CONTROL_ARCHETYPES
STRATEGY_SOURCE_CONTROL_AFTER_RE = re.compile(r"^\d+(?:\.\d+)?(?:ms|s|m|h)?$")
WORKFLOW_CONTROL_AFTER_RE = STRATEGY_SOURCE_CONTROL_AFTER_RE


def normalize_strategy_source_controls(value: Any, *, role_by_id: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise WorkflowError("workflow.controls must be an array")
    result: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_control in enumerate(value, start=1):
        result.append(
            normalize_strategy_source_control(raw_control, index=index, role_by_id=role_by_id, seen_ids=seen_ids)
        )
    return result


def normalize_workflow_controls(value: Any, *, role_by_id: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    return normalize_strategy_source_controls(value, role_by_id=role_by_id)


def normalize_strategy_source_control(
    raw_control: Any,
    *,
    index: int,
    role_by_id: Mapping[str, Mapping[str, Any]],
    seen_ids: set[str],
) -> dict[str, Any]:
    if not isinstance(raw_control, Mapping):
        raise WorkflowError("workflow.controls entries must be objects")
    control_unknown_keys = unknown_keys(raw_control, STRATEGY_SOURCE_CONTROL_KEYS)
    if control_unknown_keys:
        raise WorkflowError(f"workflow control contains unknown keys: {', '.join(control_unknown_keys)}")
    control_id = normalize_strategy_source_control_id(raw_control.get("id"), index=index, seen_ids=seen_ids)
    signal, after = normalize_strategy_source_control_when(raw_control.get("when"), control_id=control_id)
    role_id = normalize_strategy_source_control_call(
        raw_control.get("call"),
        control_id=control_id,
        role_by_id=role_by_id,
    )
    return {
        "id": control_id,
        "when": {"signal": signal, "after": after},
        "call": {"role_id": role_id},
        "mode": normalize_strategy_source_control_mode(raw_control.get("mode")),
        "max_fires_per_run": normalize_strategy_source_control_max_fires(raw_control.get("max_fires_per_run")),
    }


def normalize_workflow_control(
    raw_control: Any,
    *,
    index: int,
    role_by_id: Mapping[str, Mapping[str, Any]],
    seen_ids: set[str],
) -> dict[str, Any]:
    return normalize_strategy_source_control(raw_control, index=index, role_by_id=role_by_id, seen_ids=seen_ids)


def normalize_strategy_source_control_id(value: Any, *, index: int, seen_ids: set[str]) -> str:
    control_id = normalize_optional_strategy_source_identifier(
        value,
        default=f"control_{index:03d}",
        field_name="workflow control id",
    )
    if control_id in seen_ids:
        raise WorkflowError(f"duplicate workflow control id: {control_id}")
    seen_ids.add(control_id)
    return control_id


def normalize_workflow_control_id(value: Any, *, index: int, seen_ids: set[str]) -> str:
    return normalize_strategy_source_control_id(value, index=index, seen_ids=seen_ids)


def normalize_strategy_source_control_when(value: Any, *, control_id: str) -> tuple[str, str]:
    if not isinstance(value, Mapping):
        raise WorkflowError(f"workflow control {control_id} requires when")
    when_unknown = unknown_keys(value, STRATEGY_SOURCE_CONTROL_WHEN_KEYS)
    if when_unknown:
        raise WorkflowError(f"workflow control {control_id}.when contains unknown keys: {', '.join(when_unknown)}")
    signal = str(value.get("signal") or "").strip()
    if signal not in STRATEGY_SOURCE_CONTROL_SIGNALS:
        raise WorkflowError(
            "workflow control when.signal must be one of: " + ", ".join(sorted(STRATEGY_SOURCE_CONTROL_SIGNALS))
        )
    raw_after = value.get("after")
    if raw_after is None or (isinstance(raw_after, str) and not raw_after.strip()):
        after = "0s"
    elif not isinstance(raw_after, str):
        raise WorkflowError("workflow control when.after must be an elapsed duration such as 30s, 20m, or 1h")
    else:
        after = raw_after.strip()
    if not STRATEGY_SOURCE_CONTROL_AFTER_RE.match(after):
        raise WorkflowError("workflow control when.after must be an elapsed duration such as 30s, 20m, or 1h")
    return signal, after


def normalize_workflow_control_when(value: Any, *, control_id: str) -> tuple[str, str]:
    return normalize_strategy_source_control_when(value, control_id=control_id)


def normalize_strategy_source_control_call(
    value: Any,
    *,
    control_id: str,
    role_by_id: Mapping[str, Mapping[str, Any]],
) -> str:
    if not isinstance(value, Mapping):
        raise WorkflowError(f"workflow control {control_id} requires call")
    call_unknown = unknown_keys(value, STRATEGY_SOURCE_CONTROL_CALL_KEYS)
    if call_unknown:
        raise WorkflowError(f"workflow control {control_id}.call contains unknown keys: {', '.join(call_unknown)}")
    role_id = normalize_strategy_source_identifier(
        value.get("role_id"),
        field_name=f"workflow control {control_id}.call.role_id",
    )
    role = role_by_id.get(role_id)
    if role is None:
        raise WorkflowError(f"workflow control {control_id} references unknown role_id: {role_id}")
    archetype = str(role.get("archetype") or "").strip()
    if archetype not in STRATEGY_SOURCE_CONTROL_ARCHETYPES:
        raise WorkflowError("workflow controls may only call Inspector, Guide, or GateKeeper roles")
    return role_id


def normalize_workflow_control_call(
    value: Any,
    *,
    control_id: str,
    role_by_id: Mapping[str, Mapping[str, Any]],
) -> str:
    return normalize_strategy_source_control_call(value, control_id=control_id, role_by_id=role_by_id)


def normalize_strategy_source_control_mode(value: Any) -> str:
    if value is None or (isinstance(value, str) and not value.strip()):
        mode = "advisory"
    elif not isinstance(value, str):
        raise WorkflowError("workflow control mode must be advisory, blocking, or repair_guidance")
    else:
        mode = value.strip()
    if mode not in STRATEGY_SOURCE_CONTROL_MODES:
        raise WorkflowError("workflow control mode must be advisory, blocking, or repair_guidance")
    return mode


def normalize_workflow_control_mode(value: Any) -> str:
    return normalize_strategy_source_control_mode(value)


def normalize_strategy_source_control_max_fires(value: Any) -> int:
    raw_value = 1 if value is None or value == "" else value
    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        raise WorkflowError("workflow control max_fires_per_run must be an integer")
    max_fires = raw_value
    if max_fires < 1 or max_fires > 20:
        raise WorkflowError("workflow control max_fires_per_run must be between 1 and 20")
    return max_fires


def normalize_workflow_control_max_fires(value: Any) -> int:
    return normalize_strategy_source_control_max_fires(value)
