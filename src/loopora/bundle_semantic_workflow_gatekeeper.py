from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from loopora.bundle_semantic_workflow_support import (
    _alignment_workflow_role_archetype,
    _review_steps_since_latest_builder,
    _step_missing_evidence_query_archetypes,
)


def _lint_alignment_finishing_gatekeeper_inputs(
    workflow: Mapping[str, Any],
    *,
    role_by_key: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    workflow_role_archetype = _alignment_workflow_role_archetype(workflow, role_by_key=role_by_key)
    issues: list[str] = []
    for step in workflow.get("steps", []):
        if not isinstance(step, Mapping):
            continue
        if workflow_role_archetype.get(str(step.get("role_id", "") or "")) != "gatekeeper":
            continue
        if str(step.get("on_pass", "") or "") != "finish_run":
            continue
        step_id = str(step.get("id", "") or "").strip()
        inputs = step.get("inputs") if isinstance(step.get("inputs"), Mapping) else {}
        handoffs_from = (inputs.get("handoffs_from") if isinstance(inputs, Mapping) else []) or []
        if not any(str(handoff or "").strip() for handoff in handoffs_from):
            issues.append("finishing GateKeeper step must name upstream handoffs in inputs.handoffs_from: " + step_id)
        if not (isinstance(inputs, Mapping) and inputs.get("evidence_query")):
            issues.append("finishing GateKeeper step must query upstream evidence in inputs.evidence_query: " + step_id)
    return issues


def _lint_alignment_review_gatekeeper_inputs(
    workflow: Mapping[str, Any],
    *,
    role_by_key: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    steps = [step for step in workflow.get("steps", []) if isinstance(step, Mapping)]
    workflow_role_archetype = _alignment_workflow_role_archetype(workflow, role_by_key=role_by_key)
    issues: list[str] = []
    for index, step in enumerate(steps):
        role_id = str(step.get("role_id", "") or "")
        if workflow_role_archetype.get(role_id) != "gatekeeper":
            continue
        if str(step.get("on_pass", "") or "") != "finish_run":
            continue
        review_steps = _review_steps_since_latest_builder(
            steps[:index],
            workflow_role_archetype=workflow_role_archetype,
        )
        if not review_steps:
            continue
        inputs = step.get("inputs") if isinstance(step.get("inputs"), Mapping) else {}
        handoffs_from = {str(handoff or "").strip() for handoff in (inputs.get("handoffs_from") if isinstance(inputs, Mapping) else []) or []}
        missing_handoffs = [step_id for step_id, _ in review_steps if step_id not in handoffs_from]
        if missing_handoffs:
            issues.append("finishing GateKeeper after review must include review handoffs in inputs.handoffs_from: " + ", ".join(missing_handoffs))
        missing_archetypes = _step_missing_evidence_query_archetypes(
            step,
            {archetype for _, archetype in review_steps},
        )
        if missing_archetypes:
            issues.append("finishing GateKeeper after review must query review evidence in inputs.evidence_query: " + ", ".join(missing_archetypes))
    return issues


def _lint_alignment_long_chain_gatekeeper_inputs(
    workflow: Mapping[str, Any],
    *,
    role_by_key: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    steps = [step for step in workflow.get("steps", []) if isinstance(step, Mapping)]
    workflow_role_archetype = _alignment_workflow_role_archetype(workflow, role_by_key=role_by_key)
    issues: list[str] = []
    for index, step in enumerate(steps):
        role_id = str(step.get("role_id", "") or "")
        if workflow_role_archetype.get(role_id) != "gatekeeper":
            continue
        if str(step.get("on_pass", "") or "") != "finish_run":
            continue
        prior_steps = steps[:index]
        prior_builder_steps = [
            str(prior_step.get("id", "") or "").strip()
            for prior_step in prior_steps
            if workflow_role_archetype.get(str(prior_step.get("role_id", "") or "")) == "builder"
        ]
        if len(prior_builder_steps) < 2:
            continue
        prior_governance_handoffs = {
            str(prior_step.get("id", "") or "").strip()
            for prior_step in prior_steps
            if workflow_role_archetype.get(str(prior_step.get("role_id", "") or "")) in {"inspector", "custom", "guide"}
        }
        prior_governance_handoffs.update(prior_builder_steps[:-1])
        inputs = step.get("inputs") if isinstance(step.get("inputs"), Mapping) else {}
        handoffs_from = {str(handoff or "").strip() for handoff in (inputs.get("handoffs_from") if isinstance(inputs, Mapping) else []) or []}
        if not handoffs_from.intersection(prior_governance_handoffs):
            issues.append(
                "long-chain GateKeeper must include an earlier phase, review, or Guide handoff in inputs.handoffs_from: "
                + str(step.get("id", "") or "").strip()
            )
    return issues


def _lint_alignment_parallel_gatekeeper_inputs(
    workflow: Mapping[str, Any],
    *,
    role_by_key: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    steps = [step for step in workflow.get("steps", []) if isinstance(step, Mapping)]
    workflow_role_archetype = _alignment_workflow_role_archetype(workflow, role_by_key=role_by_key)
    parallel_review_steps = [
        (
            str(step.get("id", "") or "").strip(),
            workflow_role_archetype.get(str(step.get("role_id", "") or "")),
        )
        for step in steps
        if str(step.get("parallel_group", "") or "").strip() and workflow_role_archetype.get(str(step.get("role_id", "") or "")) in {"inspector", "custom"}
    ]
    parallel_review_step_ids = [
        str(step.get("id", "") or "").strip()
        for step in steps
        if str(step.get("parallel_group", "") or "").strip() and workflow_role_archetype.get(str(step.get("role_id", "") or "")) in {"inspector", "custom"}
    ]
    if not parallel_review_step_ids:
        return []
    issues: list[str] = []
    for step in steps:
        if workflow_role_archetype.get(str(step.get("role_id", "") or "")) != "gatekeeper":
            continue
        if str(step.get("on_pass", "") or "") != "finish_run":
            continue
        inputs = step.get("inputs") if isinstance(step.get("inputs"), Mapping) else {}
        handoffs_from = {str(handoff or "").strip() for handoff in (inputs.get("handoffs_from") if isinstance(inputs, Mapping) else []) or []}
        missing = [step_id for step_id in parallel_review_step_ids if step_id not in handoffs_from]
        if missing:
            issues.append("GateKeeper step must include every parallel review handoff in inputs.handoffs_from: " + ", ".join(missing))
        expected_archetypes = {"builder", *(archetype for _, archetype in parallel_review_steps if archetype)}
        missing_archetypes = _step_missing_evidence_query_archetypes(step, expected_archetypes)
        if missing_archetypes:
            issues.append("GateKeeper step must query Builder and parallel review evidence in inputs.evidence_query: " + ", ".join(missing_archetypes))
    return issues


def _lint_alignment_gatekeeper_semantics(
    normalized: Mapping[str, Any],
    *,
    role_by_key: Mapping[str, Mapping[str, Any]],
    used_role_keys: list[object],
) -> list[str]:
    if str(normalized["loop"].get("completion_mode", "") or "").strip().lower() != "gatekeeper":
        return []
    issues: list[str] = []
    archetypes = {role_by_key[str(role_key)]["archetype"] for role_key in used_role_keys if str(role_key) in role_by_key}
    if "gatekeeper" not in archetypes:
        issues.append("gatekeeper completion mode requires a GateKeeper role")
    return issues
