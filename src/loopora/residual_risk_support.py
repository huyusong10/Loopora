from __future__ import annotations

from collections.abc import Iterable
import re

from loopora.residual_risk_markers import (
    NO_RESIDUAL_RISK_MARKERS,
    RESIDUAL_RISK_EXCEPTION_MARKERS,
    RESIDUAL_RISK_HANDOFF_MARKERS,
    RESIDUAL_RISK_MANAGEMENT_MARKERS,
    UNMANAGED_RESIDUAL_RISK_DETAIL_PATTERNS,
    VAGUE_RESIDUAL_RISK_ACCEPTANCE_PATTERNS,
    VAGUE_RESIDUAL_RISK_MARKERS,
)


def residual_risk_is_meaningful(value: object) -> bool:
    if not isinstance(value, str):
        return False
    normalized = _normalized_residual_risk_text(value)
    if not normalized:
        return False
    if normalized in NO_RESIDUAL_RISK_MARKERS:
        return False
    if normalized.startswith("no ") and "residual risk" in normalized:
        return _has_residual_risk_exception(normalized)
    return True


def residual_risk_is_managed(value: object) -> bool:
    if not residual_risk_is_meaningful(value):
        return False
    normalized = _normalized_residual_risk_text(value)
    if normalized in VAGUE_RESIDUAL_RISK_MARKERS:
        return False
    if _has_vague_residual_risk_acceptance(normalized) and not _has_residual_risk_handoff_path(normalized):
        return False
    if _has_unmanaged_residual_risk_detail(normalized) and not _has_fail_closed_residual_risk_management(normalized):
        return False
    return any(_management_marker_is_present(marker, normalized) for marker in RESIDUAL_RISK_MANAGEMENT_MARKERS)


def residual_risk_is_unmanaged(value: object) -> bool:
    return residual_risk_is_meaningful(value) and not residual_risk_is_managed(value)


def meaningful_residual_risks(values: object) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            str(value).strip()
            for value in _residual_risk_values(values)
            if residual_risk_is_meaningful(value)
        )
    )


def unmanaged_residual_risks(values: object) -> tuple[str, ...]:
    return tuple(value for value in meaningful_residual_risks(values) if residual_risk_is_unmanaged(value))


def residual_risk_policy_disallows_acceptance(value: object) -> bool:
    normalized = _normalized_residual_risk_text(value)
    if not normalized:
        return False
    return any(
        _regex_search(pattern, normalized)
        for pattern in (
            r"\b(?:no|none|zero)\b.{0,80}\b(?:accepted|acceptable|allowed|carried)?\s*residual risks?\b",
            r"\b(?:no|none|zero)\b.{0,80}\bresidual risks?\b.{0,80}\b(?:accepted|acceptable|allowed|carried)\b",
            r"\b(?:do not|don't|cannot|can't|must not|never)\b.{0,80}\baccept\b.{0,80}\bresidual risks?\b",
            r"\bresidual risks?\b.{0,80}\b(?:not accepted|not acceptable|cannot be accepted|must not be accepted)\b",
            r"(?:不接受|不能接受|不可接受|不允许).{0,30}残余风险",
            r"残余风险.{0,30}(?:不接受|不能接受|不可接受|不允许)",
        )
    )


def residual_risk_text_matches_or_previews_any(candidate: object, references: Iterable[object]) -> bool:
    candidate_text = _normalized_residual_risk_preview_text(candidate)
    if not candidate_text:
        return False
    candidate_prefix = _residual_risk_preview_prefix(candidate_text)
    for reference in references:
        reference_text = _normalized_residual_risk_preview_text(reference)
        if not reference_text:
            continue
        if candidate_text == reference_text:
            return True
        if candidate_prefix and candidate_prefix != candidate_text and reference_text.startswith(candidate_prefix):
            return True
    return False


def _residual_risk_values(values: object) -> tuple[object, ...]:
    if isinstance(values, str):
        return (values,)
    if isinstance(values, Iterable):
        return tuple(values)
    return ()


def _normalized_residual_risk_text(value: object) -> str:
    return " ".join(str(value or "").split()).lower().strip(" .。")


def _normalized_residual_risk_preview_text(value: object) -> str:
    return " ".join(str(value or "").split()).lower().strip()


def _residual_risk_preview_prefix(value: str) -> str:
    if value.endswith("..."):
        return value[:-3].rstrip()
    if value.endswith("…"):
        return value[:-1].rstrip()
    return value


def _has_residual_risk_exception(normalized: str) -> bool:
    padded = f" {normalized} "
    return any(marker in padded for marker in RESIDUAL_RISK_EXCEPTION_MARKERS)


def _regex_search(pattern: str, value: str) -> bool:
    return bool(re.search(pattern, value, re.IGNORECASE))


def _has_unmanaged_residual_risk_detail(normalized: str) -> bool:
    return any(_regex_search(pattern, normalized) for pattern in UNMANAGED_RESIDUAL_RISK_DETAIL_PATTERNS)


def _has_vague_residual_risk_acceptance(normalized: str) -> bool:
    return any(_regex_search(pattern, normalized) for pattern in VAGUE_RESIDUAL_RISK_ACCEPTANCE_PATTERNS)


def _has_residual_risk_handoff_path(normalized: str) -> bool:
    return _has_fail_closed_residual_risk_management(normalized) or any(
        _management_marker_is_present(marker, normalized) for marker in RESIDUAL_RISK_HANDOFF_MARKERS
    )


def _has_fail_closed_residual_risk_management(normalized: str) -> bool:
    return any(
        _regex_search(pattern, normalized)
        for pattern in (
            r"\bfail(?:s|ed|ing)? closed\b",
            r"\bmust block\b",
            r"\bmust fail\b",
            r"\bblocks? closure\b",
            r"失败关闭",
            r"必须阻断",
            r"必须失败",
        )
    )


def _management_marker_is_present(marker: str, normalized: str) -> bool:
    if marker.isascii() and re.search(r"[a-z]", marker):
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(marker)}(?![a-z0-9])", normalized))
    return marker in normalized
