from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


def _review_steps_since_latest_builder(
    previous_steps: list[Mapping[str, Any]],
    *,
    workflow_role_archetype: Mapping[str, str],
    include_guides: bool = True,
) -> list[tuple[str, str]]:
    last_builder_index = -1
    for index, step in enumerate(previous_steps):
        if workflow_role_archetype.get(str(step.get("role_id", "") or "")) == "builder":
            last_builder_index = index
    review_steps: list[tuple[str, str]] = []
    review_archetypes = {"inspector", "custom", "guide"} if include_guides else {"inspector", "custom"}
    for step in previous_steps[last_builder_index + 1 :]:
        archetype = workflow_role_archetype.get(str(step.get("role_id", "") or ""))
        if archetype not in review_archetypes:
            continue
        step_id = str(step.get("id", "") or "").strip()
        if step_id:
            review_steps.append((step_id, archetype))
    return review_steps


def _alignment_workflow_role_archetype(
    workflow: Mapping[str, Any],
    *,
    role_by_key: Mapping[str, Mapping[str, Any]],
) -> dict[str, str]:
    return {
        str(role.get("id", "") or ""): str(role_by_key.get(str(role.get("role_definition_key", "") or ""), {}).get("archetype", "") or "")
        for role in workflow.get("roles", [])
        if isinstance(role, Mapping)
    }


def _alignment_workflow_role_definition_key(workflow: Mapping[str, Any]) -> dict[str, str]:
    return {str(role.get("id", "") or ""): str(role.get("role_definition_key", "") or "") for role in workflow.get("roles", []) if isinstance(role, Mapping)}


def _alignment_workflow_role_keys(workflow: Mapping[str, Any]) -> list[object]:
    return [role.get("role_definition_key", "") for role in workflow.get("roles", []) if isinstance(role, Mapping)]


def _parallel_review_role_text(role: Mapping[str, Any] | None) -> str:
    if not role:
        return ""
    value = "\n".join(
        [
            str(role.get("prompt_markdown", "") or ""),
            str(role.get("posture_notes", "") or ""),
        ]
    )
    return re.sub(r"\s+", " ", value).strip().lower()


def _step_evidence_query_mentions_archetypes(step: Mapping[str, Any], expected_archetypes: set[str]) -> bool:
    return not _step_missing_evidence_query_archetypes(step, expected_archetypes)


def _step_missing_evidence_query_archetypes(step: Mapping[str, Any], expected_archetypes: set[str]) -> list[str]:
    inputs = step.get("inputs") if isinstance(step.get("inputs"), Mapping) else {}
    evidence_query = inputs.get("evidence_query") if isinstance(inputs, Mapping) else {}
    archetypes = evidence_query.get("archetypes") if isinstance(evidence_query, Mapping) else []
    actual = {str(archetype or "").strip().lower() for archetype in archetypes or []}
    return sorted(expected_archetypes.difference(actual))
