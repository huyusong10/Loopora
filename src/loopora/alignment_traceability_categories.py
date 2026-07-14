from __future__ import annotations

"""Traceability category classifiers for alignment agreement and Agent candidates."""

import re

from loopora.alignment_traceability_candidate_catalog import (
    EXECUTION_STRATEGY_CATEGORY_PATTERNS,
    EXECUTION_STRATEGY_MARKER_PATTERNS,
    NO_ACCEPTED_RESIDUAL_RISK_BUNDLE_PATTERN,
    NO_ACCEPTED_RESIDUAL_RISK_TASK_PATTERN,
    RESIDUAL_RISK_BASE_CATEGORY,
    RESIDUAL_RISK_POLICY_CATEGORY_PATTERNS,
    RESIDUAL_RISK_POLICY_MARKER_PATTERNS,
    SUCCESS_SURFACE_BASE_CATEGORY,
    SUCCESS_SURFACE_CATEGORY_PATTERNS,
    SUCCESS_SURFACE_MARKER_PATTERNS,
    TRADEOFF_CATEGORY_PATTERNS,
    TRADEOFF_MARKER_PATTERNS,
)
from loopora.alignment_traceability_risk_categories import (
    agent_candidate_evidence_preference_categories as agent_candidate_evidence_preference_categories,
    agent_candidate_fake_done_categories as agent_candidate_fake_done_categories,
)


def agent_candidate_tradeoff_categories(task_text: str) -> list[tuple[str, str]]:
    text = str(task_text or "").strip()
    if not text:
        return []
    if not any(re.search(pattern, text, re.IGNORECASE) for pattern in TRADEOFF_MARKER_PATTERNS):
        return []
    return [(label, pattern) for label, pattern in TRADEOFF_CATEGORY_PATTERNS if re.search(pattern, text, re.IGNORECASE)]


def agent_candidate_has_labeled_execution_strategy(task_text: str) -> bool:
    return bool(
        re.search(
            r"\b(?:execution strategy|priority|priorities|priority order|next round|next pass)\b|执行策略|优先级|下一轮|下一步",
            str(task_text or ""),
            re.IGNORECASE,
        )
    )


def agent_candidate_execution_strategy_categories(task_text: str, *, require_explicit_marker: bool = True) -> list[tuple[str, str]]:
    text = str(task_text or "").strip()
    if not text:
        return []
    if require_explicit_marker and not any(re.search(pattern, text, re.IGNORECASE) for pattern in EXECUTION_STRATEGY_MARKER_PATTERNS):
        return []
    return [(label, pattern) for label, pattern in EXECUTION_STRATEGY_CATEGORY_PATTERNS if re.search(pattern, text, re.IGNORECASE)]


def agent_candidate_residual_risk_policy_categories(
    task_text: str,
    *,
    require_explicit_marker: bool = True,
) -> list[tuple[str, str]]:
    text = str(task_text or "").strip()
    if not text:
        return []
    if require_explicit_marker and not any(re.search(pattern, text, re.IGNORECASE) for pattern in RESIDUAL_RISK_POLICY_MARKER_PATTERNS):
        return []
    categories: list[tuple[str, str]] = [
        RESIDUAL_RISK_BASE_CATEGORY,
    ]
    if re.search(NO_ACCEPTED_RESIDUAL_RISK_TASK_PATTERN, text, re.IGNORECASE):
        categories.append(
            (
                "no-accepted-residual-risk",
                NO_ACCEPTED_RESIDUAL_RISK_BUNDLE_PATTERN,
            )
        )
        return categories
    categories.extend(
        (label, bundle_pattern)
        for label, task_pattern, bundle_pattern in RESIDUAL_RISK_POLICY_CATEGORY_PATTERNS
        if re.search(task_pattern, text, re.IGNORECASE)
    )
    return categories


def agent_candidate_success_surface_categories(task_text: str, *, require_explicit_marker: bool = True) -> list[tuple[str, str]]:
    text = str(task_text or "").strip()
    if not text:
        return []
    if require_explicit_marker and not any(re.search(pattern, text, re.IGNORECASE) for pattern in SUCCESS_SURFACE_MARKER_PATTERNS):
        return []
    categories: list[tuple[str, str]] = [
        SUCCESS_SURFACE_BASE_CATEGORY,
    ]
    categories.extend((label, pattern) for label, pattern in SUCCESS_SURFACE_CATEGORY_PATTERNS if re.search(pattern, text, re.IGNORECASE))
    return categories
