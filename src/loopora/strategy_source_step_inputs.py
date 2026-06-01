from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from loopora.strategy_source_constants import ARCHETYPES
from loopora.strategy_source_errors import WorkflowError
from loopora.strategy_source_validation import normalize_string_list, unknown_keys

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
