from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from loopora.bundle_semantic_workflow_support import (
    _alignment_workflow_role_archetype,
    _review_steps_since_latest_builder,
)


def _lint_alignment_iteration_memory_inputs(
    workflow: Mapping[str, Any],
    *,
    role_by_key: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    steps = [step for step in workflow.get("steps", []) if isinstance(step, Mapping)]
    workflow_role_archetype = _alignment_workflow_role_archetype(workflow, role_by_key=role_by_key)
    issues: list[str] = []
    issues.extend(_parallel_review_iteration_memory_issues(steps, workflow_role_archetype=workflow_role_archetype))
    issues.extend(_guide_review_iteration_memory_issues(steps, workflow_role_archetype=workflow_role_archetype))
    issues.extend(_builder_review_iteration_memory_issues(steps, workflow_role_archetype=workflow_role_archetype))
    issues.extend(_builder_guide_iteration_memory_issues(steps, workflow_role_archetype=workflow_role_archetype))
    return issues


def _parallel_review_iteration_memory_issues(
    steps: list[Mapping[str, Any]],
    *,
    workflow_role_archetype: Mapping[str, str],
) -> list[str]:
    issues: list[str] = []
    for step in steps:
        step_id = str(step.get("id", "") or "").strip()
        role_id = str(step.get("role_id", "") or "")
        if not str(step.get("parallel_group", "") or "").strip():
            continue
        if workflow_role_archetype.get(role_id) not in {"inspector", "custom"}:
            continue
        if not _step_declares_iteration_memory(step):
            issues.append("parallel review step must declare inputs.iteration_memory so cross-iteration evidence flow is explicit: " + step_id)
        elif not _step_iteration_memory_includes_summary(step):
            issues.append("parallel review step must use inputs.iteration_memory=summary_only so previous GateKeeper verdict stays visible: " + step_id)
    return issues


def _guide_review_iteration_memory_issues(
    steps: list[Mapping[str, Any]],
    *,
    workflow_role_archetype: Mapping[str, str],
) -> list[str]:
    issues: list[str] = []
    for index, step in enumerate(steps):
        if workflow_role_archetype.get(str(step.get("role_id", "") or "")) != "guide":
            continue
        review_steps = _review_steps_since_latest_builder(
            steps[:index],
            workflow_role_archetype=workflow_role_archetype,
            include_guides=False,
        )
        if review_steps and not _step_declares_iteration_memory(step):
            issues.append(
                "Guide step after review must declare inputs.iteration_memory so repair guidance can use prior iteration evidence explicitly: "
                + str(step.get("id", "") or "").strip()
            )
        elif review_steps and not _step_iteration_memory_includes_summary(step):
            issues.append(
                "Guide step after review must use inputs.iteration_memory=summary_only so previous GateKeeper blockers and residual risks stay visible: "
                + str(step.get("id", "") or "").strip()
            )
    return issues


def _builder_review_iteration_memory_issues(
    steps: list[Mapping[str, Any]],
    *,
    workflow_role_archetype: Mapping[str, str],
) -> list[str]:
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
        if review_steps_since_builder and not guide_seen_since_builder and not _step_declares_iteration_memory(step):
            issues.append(
                "Builder step after review must declare inputs.iteration_memory so evidence-first repair does not rely on ambient context: " + step_id
            )
        elif review_steps_since_builder and not guide_seen_since_builder and not _step_iteration_memory_includes_summary(step):
            issues.append(
                "Builder step after review must use inputs.iteration_memory=summary_only so previous GateKeeper repair direction stays visible: "
                + step_id
            )
        review_steps_since_builder = []
        guide_seen_since_builder = False
    return issues


def _builder_guide_iteration_memory_issues(
    steps: list[Mapping[str, Any]],
    *,
    workflow_role_archetype: Mapping[str, str],
) -> list[str]:
    guide_seen_since_builder = False
    issues: list[str] = []
    for step in steps:
        step_id = str(step.get("id", "") or "").strip()
        archetype = workflow_role_archetype.get(str(step.get("role_id", "") or ""))
        if archetype == "guide":
            guide_seen_since_builder = True
            continue
        if archetype != "builder":
            continue
        if guide_seen_since_builder and not _step_declares_iteration_memory(step):
            issues.append("Builder step after Guide must declare inputs.iteration_memory so repair pass does not rely on ambient context: " + step_id)
        elif guide_seen_since_builder and not _step_iteration_memory_includes_summary(step):
            issues.append("Builder step after Guide must use inputs.iteration_memory=summary_only so previous GateKeeper verdict stays visible: " + step_id)
        guide_seen_since_builder = False
    return issues


def _step_declares_iteration_memory(step: Mapping[str, Any]) -> bool:
    return bool(_step_iteration_memory(step))


def _step_iteration_memory_includes_summary(step: Mapping[str, Any]) -> bool:
    return _step_iteration_memory(step) == "summary_only"


def _step_iteration_memory(step: Mapping[str, Any]) -> str:
    inputs = step.get("inputs") if isinstance(step.get("inputs"), Mapping) else {}
    return str(inputs.get("iteration_memory", "") if isinstance(inputs, Mapping) else "").strip()
