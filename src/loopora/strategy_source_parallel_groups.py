from __future__ import annotations

"""Strategy Source parallel-group normalization and validation."""

from collections.abc import Mapping
from typing import Any

from loopora.strategy_source_errors import WorkflowError
from loopora.strategy_source_validation import normalize_strategy_source_identifier

PARALLEL_GROUP_ARCHETYPES = {"inspector", "custom"}


def normalize_strategy_step_parallel_group(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str) and not value.strip():
        return ""
    return normalize_strategy_source_identifier(value, field_name="workflow step parallel_group")


def normalize_step_parallel_group(value: Any) -> str:
    return normalize_strategy_step_parallel_group(value)


def validate_strategy_source_parallel_groups(
    steps: list[dict[str, Any]],
    role_by_id: dict[str, dict[str, Any]],
) -> None:
    seen_closed_groups: set[str] = set()
    active_group = ""
    for step in steps:
        group = strategy_source_step_parallel_group(step)
        active_group = validate_parallel_group_contiguity(
            group,
            active_group=active_group,
            seen_closed_groups=seen_closed_groups,
        )
        if group:
            validate_parallel_group_step(step, role_by_id=role_by_id)
    if active_group:
        seen_closed_groups.add(active_group)
    validate_parallel_group_size(steps)


def validate_workflow_parallel_groups(steps: list[dict[str, Any]], role_by_id: dict[str, dict[str, Any]]) -> None:
    validate_strategy_source_parallel_groups(steps, role_by_id)


def strategy_source_step_parallel_group(step: Mapping[str, Any]) -> str:
    return str(step.get("parallel_group") or "").strip()


def workflow_step_parallel_group(step: Mapping[str, Any]) -> str:
    return strategy_source_step_parallel_group(step)


def validate_parallel_group_contiguity(
    group: str,
    *,
    active_group: str,
    seen_closed_groups: set[str],
) -> str:
    if not group:
        if active_group:
            seen_closed_groups.add(active_group)
        return ""
    if group in seen_closed_groups and group != active_group:
        raise WorkflowError("workflow parallel_group steps must be contiguous")
    if active_group and group != active_group:
        seen_closed_groups.add(active_group)
    return group


def validate_parallel_group_step(step: Mapping[str, Any], *, role_by_id: Mapping[str, Mapping[str, Any]]) -> None:
    role = role_by_id.get(str(step.get("role_id") or ""))
    archetype = str((role or {}).get("archetype") or "")
    action_policy = step.get("action_policy") if isinstance(step.get("action_policy"), Mapping) else {}
    if str(action_policy.get("workspace") or "").strip() == "workspace_write":
        raise WorkflowError("workflow parallel_group steps must be read-only")
    if bool(action_policy.get("can_finish_run")):
        raise WorkflowError("workflow parallel_group steps may not finish runs")
    if archetype not in PARALLEL_GROUP_ARCHETYPES:
        raise WorkflowError("workflow parallel_group currently supports inspector and custom steps only")


def validate_parallel_group_size(steps: list[dict[str, Any]]) -> None:
    counts: dict[str, int] = {}
    for step in steps:
        group = strategy_source_step_parallel_group(step)
        if group:
            counts[group] = counts.get(group, 0) + 1
    singletons = [group for group, count in counts.items() if count < 2]
    if singletons:
        raise WorkflowError("workflow parallel_group must contain at least two contiguous steps")
