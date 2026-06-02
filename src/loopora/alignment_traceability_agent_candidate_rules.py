from __future__ import annotations

import re

from loopora.alignment_traceability_categories import (
    agent_candidate_evidence_preference_categories,
    agent_candidate_execution_strategy_categories,
    agent_candidate_fake_done_categories,
    agent_candidate_has_labeled_execution_strategy,
    agent_candidate_residual_risk_policy_categories,
    agent_candidate_success_surface_categories,
    agent_candidate_tradeoff_categories,
)


def alignment_agent_candidate_tradeoff_issues(task_text: str, *, normalized_bundle_text: str) -> list[str]:
    categories = agent_candidate_tradeoff_categories(task_text)
    if len(categories) < 2:
        return []
    return _category_projection_issues(
        categories,
        normalized_bundle_text=normalized_bundle_text,
        message_prefix="agent-first candidate must project explicit host Agent judgment tradeoffs into runnable surfaces: ",
    )


def alignment_agent_candidate_execution_strategy_issues(task_text: str, *, normalized_bundle_text: str) -> list[str]:
    categories = agent_candidate_execution_strategy_categories(task_text)
    if not categories:
        return []
    if len(categories) < 2 and not agent_candidate_has_labeled_execution_strategy(task_text):
        return []
    return _category_projection_issues(
        categories,
        normalized_bundle_text=normalized_bundle_text,
        message_prefix="agent-first candidate must project explicit host Agent execution strategy into runnable surfaces: ",
    )


def alignment_agent_candidate_residual_risk_policy_issues(task_text: str, *, normalized_bundle_text: str) -> list[str]:
    categories = agent_candidate_residual_risk_policy_categories(task_text)
    if not categories:
        return []
    return _category_projection_issues(
        categories,
        normalized_bundle_text=normalized_bundle_text,
        message_prefix="agent-first candidate must project explicit host Agent residual-risk policy into runnable surfaces: ",
    )


def alignment_agent_candidate_success_surface_issues(task_text: str, *, normalized_bundle_text: str) -> list[str]:
    categories = agent_candidate_success_surface_categories(task_text)
    if not categories:
        return []
    return _category_projection_issues(
        categories,
        normalized_bundle_text=normalized_bundle_text,
        message_prefix="agent-first candidate must project explicit host Agent success criteria into runnable surfaces: ",
    )


def alignment_agent_candidate_fake_done_issues(task_text: str, *, normalized_bundle_text: str) -> list[str]:
    categories = agent_candidate_fake_done_categories(task_text)
    if not categories:
        return []
    return _category_projection_issues(
        categories,
        normalized_bundle_text=normalized_bundle_text,
        message_prefix="agent-first candidate must project explicit host Agent fake-done risks into runnable surfaces: ",
    )


def alignment_agent_candidate_evidence_preference_issues(task_text: str, *, normalized_bundle_text: str) -> list[str]:
    categories = agent_candidate_evidence_preference_categories(task_text)
    if not categories:
        return []
    return _category_projection_issues(
        categories,
        normalized_bundle_text=normalized_bundle_text,
        message_prefix="agent-first candidate must project explicit host Agent evidence preferences into runnable surfaces: ",
    )


def _category_projection_issues(
    categories: list[tuple[str, str]],
    *,
    normalized_bundle_text: str,
    message_prefix: str,
) -> list[str]:
    missing = [
        label
        for label, bundle_pattern in categories
        if not re.search(bundle_pattern, normalized_bundle_text, re.IGNORECASE)
    ]
    if not missing:
        return []
    return [message_prefix + "missing " + ", ".join(missing)]
