from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from loopora.bundle_semantic_text import (
    _semantic_text_is_specific,
    _semantic_text_mentions_workflow_judgment_flow,
)

import re



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


def _lint_alignment_workflow_intent(workflow: Mapping[str, Any]) -> list[str]:
    intent = workflow.get("collaboration_intent", "")
    issues: list[str] = []
    if not str(intent or "").strip():
        return ["workflow.collaboration_intent is required"]
    if not _semantic_text_is_specific(intent, min_chars=64):
        issues.append("workflow.collaboration_intent must explain the task-specific judgment order")
    if not _semantic_text_mentions_workflow_judgment_flow(intent):
        issues.append("workflow.collaboration_intent must explain evidence flow, GateKeeper closure, and weak-evidence or fake-done exposure")
    return issues


def _lint_alignment_parallel_review_inputs(
    workflow: Mapping[str, Any],
    *,
    role_by_key: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    steps = [step for step in workflow.get("steps", []) if isinstance(step, Mapping)]
    workflow_role_archetype = _alignment_workflow_role_archetype(workflow, role_by_key=role_by_key)
    workflow_role_key = _alignment_workflow_role_definition_key(workflow)
    review_steps_by_group: dict[str, list[tuple[str, str, tuple[str, ...]]]] = {}
    issues: list[str] = []
    for step in steps:
        step_id = str(step.get("id", "") or "").strip()
        parallel_group = str(step.get("parallel_group", "") or "").strip()
        if not parallel_group:
            continue
        role_id = str(step.get("role_id", "") or "")
        if workflow_role_archetype.get(role_id) not in {"inspector", "custom"}:
            continue
        inputs = step.get("inputs") if isinstance(step.get("inputs"), Mapping) else {}
        handoffs_from = (inputs.get("handoffs_from") if isinstance(inputs, Mapping) else []) or []
        handoff_ids = tuple(sorted(str(handoff or "").strip() for handoff in handoffs_from if str(handoff or "").strip()))
        review_steps_by_group.setdefault(parallel_group, []).append((step_id, workflow_role_key.get(role_id, ""), handoff_ids))
        if not any(str(handoff or "").strip() for handoff in handoffs_from):
            issues.append("parallel review step must name upstream handoffs in inputs.handoffs_from: " + step_id)
        if not _step_evidence_query_mentions_archetypes(step, {"builder"}):
            issues.append("parallel review step must query Builder evidence in inputs.evidence_query: " + step_id)
    for review_steps in review_steps_by_group.values():
        role_keys = [role_key for _, role_key, _ in review_steps]
        if len(role_keys) > 1 and len(set(role_keys)) < len(role_keys):
            issues.append("parallel review steps must use distinct role_definition_key values: " + ", ".join(step_id for step_id, _, _ in review_steps))
        handoff_sets = [handoffs for _, _, handoffs in review_steps if handoffs]
        if len(handoff_sets) > 1 and len(set(handoff_sets)) > 1:
            issues.append("parallel review steps must read the same upstream handoffs: " + ", ".join(step_id for step_id, _, _ in review_steps))
        role_texts = [_parallel_review_role_text(role_by_key.get(role_key)) for role_key in role_keys]
        if len(role_texts) > 1 and len(set(role_texts)) < len(role_texts):
            issues.append("parallel review role_definitions must have responsibility-specific prompt and posture: " + ", ".join(role_keys))
    return issues


def _lint_alignment_review_builder_inputs(
    workflow: Mapping[str, Any],
    *,
    role_by_key: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    steps = [step for step in workflow.get("steps", []) if isinstance(step, Mapping)]
    workflow_role_archetype = _alignment_workflow_role_archetype(workflow, role_by_key=role_by_key)
    previous_builder_steps: list[str] = []
    issues: list[str] = []
    for step in steps:
        step_id = str(step.get("id", "") or "").strip()
        role_id = str(step.get("role_id", "") or "")
        archetype = workflow_role_archetype.get(role_id)
        if archetype == "builder":
            previous_builder_steps.append(step_id)
            continue
        if archetype not in {"inspector", "custom"} or not previous_builder_steps:
            continue
        inputs = step.get("inputs") if isinstance(step.get("inputs"), Mapping) else {}
        handoffs_from = {str(handoff or "").strip() for handoff in (inputs.get("handoffs_from") if isinstance(inputs, Mapping) else []) or []}
        if not handoffs_from.intersection(previous_builder_steps):
            issues.append("review step after Builder must name a Builder handoff in inputs.handoffs_from: " + step_id)
        if not _step_evidence_query_mentions_archetypes(step, {"builder"}):
            issues.append("review step after Builder must query Builder evidence in inputs.evidence_query: " + step_id)
    return issues


def _lint_alignment_guide_review_inputs(
    workflow: Mapping[str, Any],
    *,
    role_by_key: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    steps = [step for step in workflow.get("steps", []) if isinstance(step, Mapping)]
    workflow_role_archetype = _alignment_workflow_role_archetype(workflow, role_by_key=role_by_key)
    issues: list[str] = []
    for index, step in enumerate(steps):
        if workflow_role_archetype.get(str(step.get("role_id", "") or "")) != "guide":
            continue
        review_steps = _review_steps_since_latest_builder(
            steps[:index],
            workflow_role_archetype=workflow_role_archetype,
            include_guides=False,
        )
        if not review_steps:
            continue
        step_id = str(step.get("id", "") or "").strip()
        inputs = step.get("inputs") if isinstance(step.get("inputs"), Mapping) else {}
        handoffs_from = {str(handoff or "").strip() for handoff in (inputs.get("handoffs_from") if isinstance(inputs, Mapping) else []) or []}
        missing_handoffs = [review_step_id for review_step_id, _ in review_steps if review_step_id not in handoffs_from]
        if missing_handoffs:
            issues.append("Guide step after review must include review handoffs in inputs.handoffs_from: " + step_id)
        missing_archetypes = _step_missing_evidence_query_archetypes(
            step,
            {archetype for _, archetype in review_steps},
        )
        if missing_archetypes:
            issues.append("Guide step after review must query review evidence in inputs.evidence_query: " + ", ".join(missing_archetypes))
    return issues


def _lint_alignment_builder_review_inputs(
    workflow: Mapping[str, Any],
    *,
    role_by_key: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    steps = [step for step in workflow.get("steps", []) if isinstance(step, Mapping)]
    workflow_role_archetype = _alignment_workflow_role_archetype(workflow, role_by_key=role_by_key)
    review_steps_since_builder: list[str] = []
    guide_seen_since_builder = False
    issues: list[str] = []
    for step in steps:
        step_id = str(step.get("id", "") or "").strip()
        archetype = workflow_role_archetype.get(str(step.get("role_id", "") or ""))
        if archetype in {"inspector", "custom"}:
            review_steps_since_builder.append(step_id)
            continue
        if archetype == "guide":
            guide_seen_since_builder = True
            continue
        if archetype != "builder":
            continue
        if review_steps_since_builder and not guide_seen_since_builder:
            inputs = step.get("inputs") if isinstance(step.get("inputs"), Mapping) else {}
            handoffs_from = {str(handoff or "").strip() for handoff in (inputs.get("handoffs_from") if isinstance(inputs, Mapping) else []) or []}
            missing = [review_step_id for review_step_id in review_steps_since_builder if review_step_id not in handoffs_from]
            if missing:
                issues.append("Builder step after review must include review handoffs in inputs.handoffs_from: " + step_id)
        review_steps_since_builder = []
        guide_seen_since_builder = False
    return issues


def _lint_alignment_builder_guide_inputs(
    workflow: Mapping[str, Any],
    *,
    role_by_key: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    steps = [step for step in workflow.get("steps", []) if isinstance(step, Mapping)]
    workflow_role_archetype = _alignment_workflow_role_archetype(workflow, role_by_key=role_by_key)
    guide_steps_since_builder: list[str] = []
    review_steps_since_builder: list[str] = []
    issues: list[str] = []
    for step in steps:
        step_id = str(step.get("id", "") or "").strip()
        archetype = workflow_role_archetype.get(str(step.get("role_id", "") or ""))
        if archetype in {"inspector", "custom"}:
            if step_id:
                review_steps_since_builder.append(step_id)
            continue
        if archetype == "guide":
            if step_id:
                guide_steps_since_builder.append(step_id)
            continue
        if archetype != "builder":
            continue
        if guide_steps_since_builder:
            inputs = step.get("inputs") if isinstance(step.get("inputs"), Mapping) else {}
            handoffs_from = {str(handoff or "").strip() for handoff in (inputs.get("handoffs_from") if isinstance(inputs, Mapping) else []) or []}
            if not handoffs_from.intersection(guide_steps_since_builder):
                issues.append("Builder step after Guide must name a Guide handoff in inputs.handoffs_from: " + step_id)
            missing_review_handoffs = [review_step_id for review_step_id in review_steps_since_builder if review_step_id not in handoffs_from]
            if missing_review_handoffs:
                issues.append("Builder step after Guide must also include review handoffs in inputs.handoffs_from: " + step_id)
        guide_steps_since_builder = []
        review_steps_since_builder = []
    return issues
