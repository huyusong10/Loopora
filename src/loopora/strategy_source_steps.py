from __future__ import annotations

from collections.abc import Mapping

from typing import Any

from loopora.strategy_source_constants import ARCHETYPES

from loopora.strategy_source_errors import WorkflowError

from loopora.strategy_source_validation import normalize_string_list, unknown_keys

"""Strategy Source step action-policy defaults and validation."""



from loopora.strategy_source_constants import LEGACY_ROLE_TO_ARCHETYPE



STEP_ACTION_POLICY_KEYS = {"workspace", "can_block", "can_finish_run"}

STEP_ACTION_POLICY_WORKSPACES = {"read_only", "workspace_write"}

def normalize_step_policy_boolean(value: Any, *, field_name: str, default: bool) -> bool:
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
    raise WorkflowError(f"workflow step action_policy.{field_name} must be a boolean")

def default_strategy_step_action_policy(*, archetype: str | None = None, on_pass: str = "continue") -> dict[str, Any]:
    normalized_archetype = LEGACY_ROLE_TO_ARCHETYPE.get(str(archetype or "").strip().lower(), "")
    if normalized_archetype == "builder":
        return {"workspace": "workspace_write", "can_block": False, "can_finish_run": False}
    if normalized_archetype == "inspector":
        return {"workspace": "read_only", "can_block": True, "can_finish_run": False}
    if normalized_archetype == "gatekeeper":
        return {
            "workspace": "read_only",
            "can_block": True,
            "can_finish_run": str(on_pass or "continue").strip() == "finish_run",
        }
    return {"workspace": "read_only", "can_block": False, "can_finish_run": False}

def default_step_action_policy(*, archetype: str | None = None, on_pass: str = "continue") -> dict[str, Any]:
    return default_strategy_step_action_policy(archetype=archetype, on_pass=on_pass)

def normalize_strategy_step_action_policy_workspace(value: Any, *, default: str) -> str:
    if value is None or (isinstance(value, str) and not value.strip()):
        raw_workspace = str(default)
    elif not isinstance(value, str):
        raise WorkflowError("workflow step action_policy.workspace must be read_only or workspace_write")
    else:
        raw_workspace = value
    normalized = raw_workspace.strip().lower().replace("-", "_")
    if normalized in {"readonly", "read"}:
        normalized = "read_only"
    elif normalized in {"write", "workspace"}:
        normalized = "workspace_write"
    if normalized not in STEP_ACTION_POLICY_WORKSPACES:
        raise WorkflowError("workflow step action_policy.workspace must be read_only or workspace_write")
    return normalized

def normalize_step_action_policy_workspace(value: Any, *, default: str) -> str:
    return normalize_strategy_step_action_policy_workspace(value, default=default)

def normalize_strategy_step_action_policy(
    value: Any,
    *,
    archetype: str | None = None,
    on_pass: str = "continue",
) -> dict[str, Any]:
    normalized_archetype = LEGACY_ROLE_TO_ARCHETYPE.get(str(archetype or "").strip().lower(), "")
    defaults = default_strategy_step_action_policy(archetype=normalized_archetype, on_pass=on_pass)
    if value is None:
        policy = dict(defaults)
    else:
        if not isinstance(value, Mapping):
            raise WorkflowError("workflow step action_policy must be an object")
        action_policy_unknown_keys = unknown_keys(value, STEP_ACTION_POLICY_KEYS)
        if action_policy_unknown_keys:
            raise WorkflowError(
                f"workflow step action_policy contains unknown keys: {', '.join(action_policy_unknown_keys)}"
            )
        policy = {
            "workspace": normalize_strategy_step_action_policy_workspace(
                value.get("workspace", defaults["workspace"]),
                default=str(defaults["workspace"]),
            ),
            "can_block": normalize_step_policy_boolean(
                value.get("can_block"),
                field_name="can_block",
                default=bool(defaults["can_block"]),
            ),
            "can_finish_run": normalize_step_policy_boolean(
                value.get("can_finish_run"),
                field_name="can_finish_run",
                default=bool(defaults["can_finish_run"]),
            ),
        }

    if policy["workspace"] == "workspace_write" and normalized_archetype != "builder":
        raise WorkflowError("only Builder steps may set action_policy.workspace=workspace_write in v1")
    if policy["can_finish_run"] and normalized_archetype != "gatekeeper":
        raise WorkflowError("only GateKeeper steps may set action_policy.can_finish_run=true")
    if policy["can_finish_run"] and str(on_pass or "continue").strip() != "finish_run":
        raise WorkflowError("action_policy.can_finish_run=true requires on_pass=finish_run")
    return policy

def normalize_step_action_policy(
    value: Any,
    *,
    archetype: str | None = None,
    on_pass: str = "continue",
) -> dict[str, Any]:
    return normalize_strategy_step_action_policy(value, archetype=archetype, on_pass=on_pass)

STEP_INPUT_KEYS = {"handoffs_from", "evidence_query", "iteration_memory"}

STEP_EVIDENCE_QUERY_KEYS = {"archetypes", "verifies", "limit"}

STEP_ITERATION_MEMORY_POLICIES = {"default", "none", "same_step", "same_role", "summary_only"}

def normalize_strategy_step_inputs(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise WorkflowError("workflow step inputs must be an object")
    input_unknown_keys = unknown_keys(value, STEP_INPUT_KEYS)
    if input_unknown_keys:
        raise WorkflowError(f"workflow step inputs contains unknown keys: {', '.join(input_unknown_keys)}")

    result: dict[str, Any] = {}
    handoffs_from = normalize_strategy_step_handoffs_from(value.get("handoffs_from"))
    if handoffs_from:
        result["handoffs_from"] = handoffs_from

    evidence_query = normalize_strategy_step_evidence_query(value.get("evidence_query"))
    if evidence_query:
        result["evidence_query"] = evidence_query

    iteration_memory = normalize_strategy_step_iteration_memory(value.get("iteration_memory"))
    if iteration_memory:
        result["iteration_memory"] = iteration_memory

    return result

def normalize_step_inputs(value: Any) -> dict[str, Any]:
    return normalize_strategy_step_inputs(value)

def normalize_strategy_step_handoffs_from(value: Any) -> list[str]:
    return normalize_string_list(value, field_name="workflow step inputs.handoffs_from")

def normalize_step_handoffs_from(value: Any) -> list[str]:
    return normalize_strategy_step_handoffs_from(value)

def normalize_strategy_step_evidence_query(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise WorkflowError("workflow step inputs.evidence_query must be an object")
    query_unknown = unknown_keys(value, STEP_EVIDENCE_QUERY_KEYS)
    if query_unknown:
        raise WorkflowError(f"workflow step inputs.evidence_query contains unknown keys: {', '.join(query_unknown)}")

    query: dict[str, Any] = {}
    archetypes = normalize_strategy_step_evidence_archetypes(value.get("archetypes"))
    if archetypes:
        query["archetypes"] = archetypes
    verifies = normalize_string_list(
        value.get("verifies"),
        field_name="workflow step inputs.evidence_query.verifies",
    )
    if verifies:
        query["verifies"] = verifies
    limit = normalize_strategy_step_evidence_limit(value.get("limit"))
    if limit is not None:
        query["limit"] = limit
    return query

def normalize_step_evidence_query(value: Any) -> dict[str, Any]:
    return normalize_strategy_step_evidence_query(value)

def normalize_strategy_step_evidence_archetypes(value: Any) -> list[str]:
    archetypes = normalize_string_list(
        value,
        field_name="workflow step inputs.evidence_query.archetypes",
    )
    invalid_archetypes = [item for item in archetypes if item not in ARCHETYPES]
    if invalid_archetypes:
        raise WorkflowError(
            "workflow step inputs.evidence_query.archetypes contains unknown archetypes: "
            + ", ".join(invalid_archetypes)
        )
    return archetypes

def normalize_step_evidence_archetypes(value: Any) -> list[str]:
    return normalize_strategy_step_evidence_archetypes(value)

def normalize_strategy_step_evidence_limit(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkflowError("workflow step inputs.evidence_query.limit must be an integer")
    limit = value
    if limit < 1 or limit > 100:
        raise WorkflowError("workflow step inputs.evidence_query.limit must be between 1 and 100")
    return limit

def normalize_step_evidence_limit(value: Any) -> int | None:
    return normalize_strategy_step_evidence_limit(value)

def normalize_strategy_step_iteration_memory(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise WorkflowError(
            "workflow step inputs.iteration_memory must be default, none, same_step, same_role, or summary_only"
        )
    iteration_memory = value.strip().lower()
    if iteration_memory == "all":
        iteration_memory = "default"
    if not iteration_memory:
        return ""
    if iteration_memory not in STEP_ITERATION_MEMORY_POLICIES:
        raise WorkflowError(
            "workflow step inputs.iteration_memory must be default, none, same_step, same_role, or summary_only"
        )
    return "" if iteration_memory == "default" else iteration_memory

def normalize_step_iteration_memory(value: Any) -> str:
    return normalize_strategy_step_iteration_memory(value)

"""Strategy Source parallel-group normalization and validation."""




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

"""Strategy Source step defaults, normalization, and compatibility exports."""


from loopora.executor_command_args import validate_extra_cli_args_text
from loopora.strategy_source_validation import (
    normalize_optional_strategy_source_identifier,
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
