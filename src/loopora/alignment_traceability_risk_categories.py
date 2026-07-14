from __future__ import annotations

"""Fake-done and evidence-preference traceability categories for Agent candidates."""

import re

from loopora.alignment_traceability_evidence_catalog import EVIDENCE_PREFERENCE_CATEGORY_PATTERNS
from loopora.alignment_traceability_fake_done_catalog import FAKE_DONE_CATEGORY_PATTERNS
from loopora.alignment_traceability_risk_markers import (
    EVIDENCE_PROOF_PATTERN,
    EXPLICIT_EVIDENCE_MARKER_PATTERNS,
    EXPLICIT_FAKE_DONE_MARKER_PATTERNS,
    FAKE_DONE_BLOCKING_PATTERN,
    marker_matches_any,
)


def agent_candidate_fake_done_categories(task_text: str, *, require_explicit_marker: bool = True) -> list[tuple[str, str]]:
    text = str(task_text or "").strip()
    if not text:
        return []
    if require_explicit_marker and not marker_matches_any(text, EXPLICIT_FAKE_DONE_MARKER_PATTERNS):
        return []
    categories: list[tuple[str, str]] = [
        ("fake-done/blocking", FAKE_DONE_BLOCKING_PATTERN),
    ]
    categories.extend(
        (label, bundle_pattern) for label, task_pattern, bundle_pattern in FAKE_DONE_CATEGORY_PATTERNS if re.search(task_pattern, text, re.IGNORECASE)
    )
    return categories


def agent_candidate_evidence_preference_categories(
    task_text: str,
    *,
    require_explicit_marker: bool = True,
) -> list[tuple[str, str]]:
    text = str(task_text or "").strip()
    if not text:
        return []
    if require_explicit_marker and not marker_matches_any(text, EXPLICIT_EVIDENCE_MARKER_PATTERNS):
        return []
    categories: list[tuple[str, str]] = [
        ("evidence/proof", EVIDENCE_PROOF_PATTERN),
    ]
    categories.extend((label, pattern) for label, pattern in EVIDENCE_PREFERENCE_CATEGORY_PATTERNS if re.search(pattern, text, re.IGNORECASE))
    return categories
