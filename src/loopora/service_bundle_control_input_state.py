from __future__ import annotations

"""Workflow input-chain state helpers for bundle-control diagnostics."""

from collections.abc import Iterable


def initial_strategy_input_diagnostic_state() -> dict:
    return {
        "prior_step_ids": [],
        "prior_archetypes": set(),
        "latest_builder_step": "",
        "review_steps_since_builder": [],
        "guide_steps_since_builder": [],
        "parallel_review_groups": [],
    }


def advance_strategy_diagnostic_state(step_context: dict, state: dict) -> None:
    _record_parallel_review_group(step_context, state)
    if step_context["step_id"]:
        state["prior_step_ids"].append(step_context["step_id"])
    if step_context["archetype"]:
        state["prior_archetypes"].add(step_context["archetype"])


def input_missing_handoffs(inputs: dict, expected_step_ids: list[str]) -> list[str]:
    actual = _input_handoff_ids(inputs)
    return [step_id for step_id in expected_step_ids if step_id and step_id not in actual]


def input_names_any_handoff(inputs: dict, expected_step_ids: list[str]) -> bool:
    actual = _input_handoff_ids(inputs)
    return bool(actual.intersection({item for item in expected_step_ids if item}))


def input_queries_any_archetype(inputs: dict, expected_archetypes: set[str]) -> bool:
    actual = _input_evidence_query_archetypes(inputs)
    expected = {item for item in expected_archetypes if item}
    return bool(actual.intersection(expected))


def input_missing_evidence_archetypes(inputs: dict, expected_archetypes: set[str]) -> list[str]:
    actual = _input_evidence_query_archetypes(inputs)
    expected = {item for item in expected_archetypes if item}
    return sorted(expected.difference(actual))


def _record_parallel_review_group(step_context: dict, state: dict) -> None:
    parallel_group = str(step_context["step"].get("parallel_group") or "").strip()
    if not parallel_group or step_context["archetype"] not in {"inspector", "custom"} or not step_context["step_id"]:
        return
    groups = list(state.get("parallel_review_groups") or [])
    group = next((item for item in groups if item.get("parallel_group") == parallel_group), None)
    if group is None:
        group = {"parallel_group": parallel_group, "step_ids": [], "archetypes": set()}
        groups.append(group)
        state["parallel_review_groups"] = groups
    group["step_ids"].append(step_context["step_id"])
    group["archetypes"].add(step_context["archetype"])


def unique_in_order(values: Iterable[object]) -> list[str]:
    result: list[str] = []
    for value in values:
        normalized = str(value or "").strip()
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _input_handoff_ids(inputs: dict) -> set[str]:
    handoffs_from = inputs.get("handoffs_from") if isinstance(inputs, dict) else []
    return {str(item or "").strip() for item in list(handoffs_from or []) if str(item or "").strip()}


def _input_evidence_query_archetypes(inputs: dict) -> set[str]:
    evidence_query = inputs.get("evidence_query") if isinstance(inputs, dict) else {}
    if not isinstance(evidence_query, dict):
        return set()
    return {
        str(item or "").strip().lower()
        for item in list(evidence_query.get("archetypes") or [])
        if str(item or "").strip()
    }
