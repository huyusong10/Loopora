from __future__ import annotations

"""Strategy Source warning and finish-gate detection rules."""

from collections.abc import Mapping
from typing import Any


def strategy_source_warnings(strategy_source: dict) -> list[str]:
    role_by_id = {role["id"]: role for role in strategy_source.get("roles", [])}
    steps = list(strategy_source.get("steps", []))
    warnings: list[str] = []
    if not strategy_source_has_finish_gatekeeper_step(strategy_source):
        warnings.append(
            "This workflow has no GateKeeper finish step, so it should be paired with round-based completion or updated before gate-based execution."
        )
    warnings.extend(strategy_source_guide_input_warnings(steps, role_by_id))
    gate_before_builder = False
    gate_after_builder_without_inspector = False
    seen_builder = False
    seen_inspector_after_builder = False
    for index, step in enumerate(steps):
        role = role_by_id.get(step["role_id"], {})
        archetype = role.get("archetype")
        if archetype == "builder":
            seen_builder = True
            seen_inspector_after_builder = False
        elif archetype == "inspector" and seen_builder:
            seen_inspector_after_builder = True
        elif archetype == "gatekeeper":
            if any(
                role_by_id.get(other["role_id"], {}).get("archetype") == "builder"
                for other in steps[index + 1 :]
            ):
                gate_before_builder = True
            if seen_builder and not seen_inspector_after_builder:
                gate_after_builder_without_inspector = True
    if gate_before_builder:
        warnings.append("GateKeeper appears before a later Builder step, so it may only judge pre-change evidence.")
    if gate_after_builder_without_inspector:
        warnings.append("GateKeeper appears after Builder without a later Inspector step, so it may judge stale evidence.")
    return warnings


def workflow_warnings(workflow: dict) -> list[str]:
    return strategy_source_warnings(workflow)


def strategy_source_guide_input_warnings(
    steps: list[dict[str, Any]],
    role_by_id: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    warnings: list[str] = []
    for step in steps:
        role = role_by_id.get(step["role_id"], {})
        if role.get("archetype") != "guide":
            continue
        inputs = step.get("inputs") if isinstance(step.get("inputs"), Mapping) else {}
        if not inputs.get("handoffs_from") or not inputs.get("evidence_query"):
            warnings.append(f"Guide step {step['id']} has incomplete upstream inputs, so it may rely on ambient context.")
    return warnings


def workflow_guide_input_warnings(
    steps: list[dict[str, Any]],
    role_by_id: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    return strategy_source_guide_input_warnings(steps, role_by_id)


def strategy_source_has_finish_gatekeeper_step(strategy_source: dict[str, Any] | None) -> bool:
    if not strategy_source:
        return False
    role_by_id = {
        str(role.get("id", "")).strip(): role
        for role in strategy_source.get("roles", [])
        if isinstance(role, dict)
    }
    for raw_step in strategy_source.get("steps", []):
        if not isinstance(raw_step, dict):
            continue
        role = role_by_id.get(str(raw_step.get("role_id", "")).strip())
        if not role or role.get("archetype") != "gatekeeper":
            continue
        if str(raw_step.get("on_pass", "continue") or "continue").strip() == "finish_run":
            return True
    return False


def has_finish_gatekeeper_step(workflow: dict[str, Any] | None) -> bool:
    return strategy_source_has_finish_gatekeeper_step(workflow)
