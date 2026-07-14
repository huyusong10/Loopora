from __future__ import annotations

"""Shared marker patterns for Agent-candidate traceability risk classifiers."""

import re
from collections.abc import Iterable


EXPLICIT_FAKE_DONE_MARKER_PATTERNS = (
    r"\bfake[- ]?(?:done|completion)\b",
    r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b",
    r"\b(?:looks|appears|seems)\s+(?:done|complete|finished|working)\b",
    r"\b(?:only|just|merely)\s+(?:a\s+)?(?:claim|screenshot|download|export|mock|stub|static)\b",
    r"\bhappy[- ]path[- ]only\b",
    r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b",
    r"假完成",
    r"(?:必须|需要|应当|要).{0,16}(?:阻断|拒绝)",
    r"看起来.{0,12}(?:完成|可用|通过)",
    r"(?:不能|不可|不要|不得).{0,16}(?:通过|算完成|收尾)",
)

FAKE_DONE_BLOCKING_PATTERN = (
    r"\bfake[- ]?(?:done|completion)\b|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
    r"假完成|阻断|不得通过|不能通过"
)

FAKE_DONE_PROOF_GAP_MARKER_PATTERN = (
    r"\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
    r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
    r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
    r"\b(?:only|just|merely)\b|假完成|阻断|拒绝|不得通过|不能通过"
)

FAKE_DONE_PROOF_GAP_OR_ONLY_MARKER_PATTERN = FAKE_DONE_PROOF_GAP_MARKER_PATTERN + r"|只有"
FAKE_DONE_PROOF_GAP_OR_MISSING_MARKER_PATTERN = FAKE_DONE_PROOF_GAP_OR_ONLY_MARKER_PATTERN + r"|没有"
FAKE_DONE_HAPPY_PATH_MARKER_PATTERN = FAKE_DONE_PROOF_GAP_OR_ONLY_MARKER_PATTERN + r"|happy[- ]?path"
FAKE_DONE_HAPPY_PATH_MOCK_MARKER_PATTERN = FAKE_DONE_HAPPY_PATH_MARKER_PATTERN + r"|mock|stub|模拟"

EXPLICIT_EVIDENCE_MARKER_PATTERNS = (
    r"\b(?:evidence|proof|verification|verify)\b.{0,80}\b(?:must|should|prefer|include|require|needs?)\b",
    r"\b(?:must|should|prefer|include|require|needs?)\b.{0,80}\b(?:evidence|proof|verification|verify)\b",
    r"证据.{0,24}(?:必须|需要|优先|包括|包含)",
    r"(?:必须|需要|优先|包括|包含).{0,24}(?:证据|证明|验证)",
)

EVIDENCE_PROOF_PATTERN = r"\b(?:evidence|proof|verify|verification|verified|proven)\b|证据|证明|验证|已证明"


def marker_matches_any(text: str, patterns: Iterable[str]) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def risk_marker_near_domain_pattern(
    marker_pattern: str,
    domain_pattern: str,
    *,
    window: int,
    extra_marker_pattern: str = "",
) -> str:
    combined_marker_pattern = marker_pattern
    if extra_marker_pattern:
        combined_marker_pattern = rf"{combined_marker_pattern}|{extra_marker_pattern}"
    return (
        rf"(?:{combined_marker_pattern}).{{0,{window}}}(?:{domain_pattern})"
        rf"|(?:{domain_pattern}).{{0,{window}}}(?:{combined_marker_pattern})"
    )
