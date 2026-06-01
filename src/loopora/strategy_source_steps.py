from __future__ import annotations

"""Strategy Source step defaults, normalization, and compatibility exports."""

from collections.abc import Mapping
from typing import Any

from loopora.executor_command_args import validate_extra_cli_args_text
from loopora.strategy_source_constants import LEGACY_ROLE_TO_ARCHETYPE
from loopora.strategy_source_errors import WorkflowError
from loopora.strategy_source_parallel_groups import (
    PARALLEL_GROUP_ARCHETYPES as PARALLEL_GROUP_ARCHETYPES,
    normalize_step_parallel_group as normalize_step_parallel_group,
    normalize_strategy_step_parallel_group as normalize_strategy_step_parallel_group,
    strategy_source_step_parallel_group as strategy_source_step_parallel_group,
    validate_parallel_group_contiguity as validate_parallel_group_contiguity,
    validate_parallel_group_size as validate_parallel_group_size,
    validate_parallel_group_step as validate_parallel_group_step,
    validate_strategy_source_parallel_groups as validate_strategy_source_parallel_groups,
    validate_workflow_parallel_groups as validate_workflow_parallel_groups,
    workflow_step_parallel_group as workflow_step_parallel_group,
)
from loopora.strategy_source_step_inputs import (
    STEP_EVIDENCE_QUERY_KEYS as STEP_EVIDENCE_QUERY_KEYS,
    STEP_INPUT_KEYS as STEP_INPUT_KEYS,
    STEP_ITERATION_MEMORY_POLICIES as STEP_ITERATION_MEMORY_POLICIES,
    normalize_step_evidence_archetypes as normalize_step_evidence_archetypes,
    normalize_step_evidence_limit as normalize_step_evidence_limit,
    normalize_step_evidence_query as normalize_step_evidence_query,
    normalize_step_handoffs_from as normalize_step_handoffs_from,
    normalize_step_inputs as normalize_step_inputs,
    normalize_step_iteration_memory as normalize_step_iteration_memory,
    normalize_strategy_step_evidence_archetypes as normalize_strategy_step_evidence_archetypes,
    normalize_strategy_step_evidence_limit as normalize_strategy_step_evidence_limit,
    normalize_strategy_step_evidence_query as normalize_strategy_step_evidence_query,
    normalize_strategy_step_handoffs_from as normalize_strategy_step_handoffs_from,
    normalize_strategy_step_inputs as normalize_strategy_step_inputs,
    normalize_strategy_step_iteration_memory as normalize_strategy_step_iteration_memory,
)
from loopora.strategy_source_step_policy import (
    STEP_ACTION_POLICY_KEYS as STEP_ACTION_POLICY_KEYS,
    STEP_ACTION_POLICY_WORKSPACES as STEP_ACTION_POLICY_WORKSPACES,
    default_step_action_policy as default_step_action_policy,
    default_strategy_step_action_policy as default_strategy_step_action_policy,
    normalize_step_action_policy as normalize_step_action_policy,
    normalize_step_action_policy_workspace as normalize_step_action_policy_workspace,
    normalize_step_policy_boolean as normalize_step_policy_boolean,
    normalize_strategy_step_action_policy as normalize_strategy_step_action_policy,
    normalize_strategy_step_action_policy_workspace as normalize_strategy_step_action_policy_workspace,
)
from loopora.strategy_source_validation import (
    normalize_optional_strategy_source_identifier,
    normalize_strategy_source_identifier,
)

STEP_EXECUTION_FIELDS = (
    "on_pass",
    "model",
    "inherit_session",
    "extra_cli_args",
    "parallel_group",
    "inputs",
    "action_policy",
)


def default_strategy_step_inherit_session(archetype: str | None) -> bool:
    normalized_archetype = LEGACY_ROLE_TO_ARCHETYPE.get(str(archetype or "").strip().lower(), "")
    return normalized_archetype == "builder"


def default_step_inherit_session(archetype: str | None) -> bool:
    return default_strategy_step_inherit_session(archetype)


def normalize_strategy_step_inherit_session(value: Any, *, archetype: str | None = None) -> bool:
    default = default_strategy_step_inherit_session(archetype)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in {0, 1}:
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise WorkflowError("workflow step inherit_session must be a boolean")


def normalize_step_inherit_session(value: Any, *, archetype: str | None = None) -> bool:
    return normalize_strategy_step_inherit_session(value, archetype=archetype)


def normalize_strategy_step_on_pass(
    value: Any,
    *,
    archetype: str | None = None,
    default: str = "continue",
) -> str:
    normalized_archetype = LEGACY_ROLE_TO_ARCHETYPE.get(str(archetype or "").strip().lower(), "")
    normalized_default = str(default or "continue").strip() or "continue"
    normalized_value = str(value if value is not None else normalized_default).strip() or normalized_default
    if normalized_archetype != "gatekeeper":
        if normalized_value != "continue":
            raise WorkflowError("non-gatekeeper steps only support on_pass=continue")
        return "continue"
    if normalized_value not in {"continue", "finish_run"}:
        raise WorkflowError("gatekeeper step on_pass must be continue or finish_run")
    return normalized_value


def normalize_step_on_pass(
    value: Any,
    *,
    archetype: str | None = None,
    default: str = "continue",
) -> str:
    return normalize_strategy_step_on_pass(value, archetype=archetype, default=default)


def default_strategy_step_execution_settings(*, archetype: str | None = None) -> dict[str, Any]:
    normalized_archetype = LEGACY_ROLE_TO_ARCHETYPE.get(str(archetype or "").strip().lower(), "")
    return {
        "on_pass": "finish_run" if normalized_archetype == "gatekeeper" else "continue",
        "model": "",
        "inherit_session": default_strategy_step_inherit_session(normalized_archetype) if normalized_archetype else False,
        "extra_cli_args": "",
    }


def default_step_execution_settings(*, archetype: str | None = None) -> dict[str, Any]:
    return default_strategy_step_execution_settings(archetype=archetype)


def normalize_strategy_source_steps(
    raw_steps: list[Any],
    *,
    role_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    step_ids: set[str] = set()
    for index, raw_step in enumerate(raw_steps, start=1):
        steps.append(normalize_strategy_source_step(raw_step, index=index, role_by_id=role_by_id, step_ids=step_ids))
    validate_strategy_source_parallel_groups(steps, role_by_id)
    return steps


def normalize_workflow_steps(
    raw_steps: list[Any],
    *,
    role_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return normalize_strategy_source_steps(raw_steps, role_by_id=role_by_id)


def normalize_strategy_source_step(
    raw_step: Any,
    *,
    index: int,
    role_by_id: Mapping[str, Mapping[str, Any]],
    step_ids: set[str],
) -> dict[str, Any]:
    if not isinstance(raw_step, dict):
        raise WorkflowError("workflow steps must be objects")
    role_id = normalize_strategy_source_identifier(raw_step.get("role_id"), field_name="workflow step role_id")
    role = role_by_id.get(role_id)
    if role is None:
        raise WorkflowError(f"workflow step references unknown role_id: {role_id}")
    step_id = normalize_optional_strategy_source_identifier(
        raw_step.get("id"),
        default=f"step_{index:03d}",
        field_name="workflow step id",
    )
    if step_id in step_ids:
        raise WorkflowError(f"duplicate workflow step id: {step_id}")
    on_pass = normalize_strategy_step_on_pass(
        raw_step.get("on_pass"),
        archetype=role["archetype"],
        default="continue",
    )
    extra_cli_args = str(raw_step.get("extra_cli_args", "") or "").strip()
    validate_extra_cli_args_text(extra_cli_args)
    step_entry = {
        "id": step_id,
        "role_id": role_id,
        "on_pass": on_pass,
        "model": str(raw_step.get("model", "")).strip(),
        "inherit_session": normalize_strategy_step_inherit_session(
            raw_step.get("inherit_session"),
            archetype=role["archetype"],
        ),
        "extra_cli_args": extra_cli_args,
        "action_policy": normalize_strategy_step_action_policy(
            raw_step.get("action_policy"),
            archetype=role["archetype"],
            on_pass=on_pass,
        ),
    }
    parallel_group = normalize_strategy_step_parallel_group(raw_step.get("parallel_group"))
    if parallel_group:
        step_entry["parallel_group"] = parallel_group
    inputs = normalize_strategy_step_inputs(raw_step.get("inputs"))
    if inputs:
        step_entry["inputs"] = inputs
    step_ids.add(step_id)
    return step_entry


def normalize_workflow_step(
    raw_step: Any,
    *,
    index: int,
    role_by_id: Mapping[str, Mapping[str, Any]],
    step_ids: set[str],
) -> dict[str, Any]:
    return normalize_strategy_source_step(raw_step, index=index, role_by_id=role_by_id, step_ids=step_ids)
