from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from loopora.alignment_guidance import load_alignment_guidance_assets
from loopora.alignment_traceability_categories import agent_candidate_success_surface_categories
from loopora.alignment_traceability_risk_categories import (
    agent_candidate_evidence_preference_categories,
    agent_candidate_fake_done_categories,
)
from loopora.executor_alignment_task_projection_scope import projection_scoped_labels


@dataclass(frozen=True)
class AlignmentTaskDomainProjection:
    success_focus: str
    fake_done_focus: str
    evidence_focus: str
    evidence_verifies: list[str]


TASK_DOMAIN_PROJECTION_ASSET_NAME = "task-domain-projection.json"


def alignment_task_domain_projection(
    task_text: str,
    *,
    display_language: str = "",
) -> AlignmentTaskDomainProjection:
    language = _projection_display_language(display_language)
    labels = _task_domain_labels(task_text)
    success_focus = _projection_text(labels, default=_default_success_focus(language), language=language)
    fake_done_labels = _dedupe([*_task_fake_done_labels(task_text), *labels])
    fake_done_focus = _fake_done_projection_text(fake_done_labels, language=language)
    evidence_labels = _dedupe([*_task_evidence_labels(task_text), *labels])
    evidence_focus = _projection_text(evidence_labels, default=_default_evidence_focus(language), language=language)
    evidence_verifies = _projection_verifies(evidence_labels)
    return AlignmentTaskDomainProjection(
        success_focus=success_focus,
        fake_done_focus=fake_done_focus,
        evidence_focus=evidence_focus,
        evidence_verifies=evidence_verifies,
    )


def _task_domain_labels(task_text: str) -> list[str]:
    return projection_scoped_labels(
        task_text,
        (
            label
            for label, _pattern in agent_candidate_success_surface_categories(
                task_text,
                require_explicit_marker=False,
            )
        ),
    )


def _task_fake_done_labels(task_text: str) -> list[str]:
    return projection_scoped_labels(
        task_text,
        (label for label, _pattern in agent_candidate_fake_done_categories(task_text)),
    )


def _task_evidence_labels(task_text: str) -> list[str]:
    return projection_scoped_labels(
        task_text,
        (label for label, _pattern in agent_candidate_evidence_preference_categories(task_text)),
    )


def _projection_display_language(display_language: str) -> str:
    normalized = str(display_language or "").strip().lower()
    return "zh" if normalized.startswith("zh") else ""


def _projection_text(labels: list[str], *, default: str, language: str) -> str:
    fragments = [_domain_proof_focus(label, language=language) for label in _ordered_projection_labels(labels) if _domain_proof_focus(label, language=language)]
    return "; ".join(_dedupe(fragments)[: _projection_fragment_limit()]) if fragments else default


def _fake_done_projection_text(labels: list[str], *, language: str) -> str:
    fragments = [
        _fake_done_fragment(_domain_proof_focus(label, language=language), language=language)
        for label in _ordered_projection_labels(labels)
        if _domain_proof_focus(label, language=language)
    ]
    return "; ".join(_dedupe(fragments)[: _projection_fragment_limit()]) if fragments else _default_fake_done_focus(language)


def _domain_proof_focus(label: str, *, language: str) -> str:
    if language == "zh":
        localized = _task_domain_projection_string_map("focus_zh").get(label)
        if localized:
            return localized
    return _task_domain_projection_string_map("focus").get(label, "")


def _fake_done_fragment(focus: str, *, language: str) -> str:
    return f"{focus} 缺少直接证据时不得通过" if language == "zh" else f"{focus} must not pass without direct proof"


def _default_success_focus(language: str) -> str:
    return _task_domain_projection_language_defaults(language)["success_focus"]


def _default_fake_done_focus(language: str) -> str:
    return _task_domain_projection_language_defaults(language)["fake_done_focus"]


def _default_evidence_focus(language: str) -> str:
    return _task_domain_projection_language_defaults(language)["evidence_focus"]


def _projection_verifies(labels: list[str]) -> list[str]:
    verify_by_label = _task_domain_projection_string_map("evidence_verify")
    verifies = [verify_by_label[label] for label in _ordered_projection_labels(labels) if label in verify_by_label]
    return _dedupe([*_task_domain_projection_default_verifies(), *verifies])[: _projection_verify_limit()]


def _ordered_projection_labels(labels: list[str]) -> list[str]:
    priority_by_label = _task_domain_projection_priority()
    indexed = list(enumerate(labels))
    indexed.sort(key=lambda item: (priority_by_label.get(item[1], 9), item[0]))
    return [label for _index, label in indexed]


@lru_cache
def _task_domain_projection_asset() -> dict[str, Any]:
    asset = load_alignment_guidance_assets().task_domain_projection
    for key in ("defaults", "limits", "focus", "focus_zh", "evidence_verify", "priority"):
        if not isinstance(asset.get(key), dict):
            raise ValueError(f"{TASK_DOMAIN_PROJECTION_ASSET_NAME} must contain object field: {key}")
    return asset


def _task_domain_projection_string_map(key: str) -> dict[str, str]:
    value = _task_domain_projection_asset()[key]
    if not isinstance(value, dict) or not all(isinstance(item_key, str) and isinstance(item_value, str) for item_key, item_value in value.items()):
        raise ValueError(f"{TASK_DOMAIN_PROJECTION_ASSET_NAME}.{key} must be a string map")
    return value


def _task_domain_projection_priority() -> dict[str, int]:
    value = _task_domain_projection_asset()["priority"]
    if not isinstance(value, dict) or not all(isinstance(item_key, str) and isinstance(item_value, int) for item_key, item_value in value.items()):
        raise ValueError(f"{TASK_DOMAIN_PROJECTION_ASSET_NAME}.priority must be an integer map")
    return value


def _task_domain_projection_language_defaults(language: str) -> dict[str, str]:
    defaults = _task_domain_projection_asset()["defaults"]
    if not isinstance(defaults, dict):
        raise ValueError(f"{TASK_DOMAIN_PROJECTION_ASSET_NAME}.defaults must be an object")
    language_defaults = defaults.get("zh" if language == "zh" else "en")
    if not isinstance(language_defaults, dict) or not all(
        isinstance(language_defaults.get(key), str) for key in ("success_focus", "fake_done_focus", "evidence_focus")
    ):
        raise ValueError(f"{TASK_DOMAIN_PROJECTION_ASSET_NAME}.defaults must include en/zh focus strings")
    return language_defaults


def _task_domain_projection_default_verifies() -> list[str]:
    defaults = _task_domain_projection_asset()["defaults"]
    if not isinstance(defaults, dict):
        raise ValueError(f"{TASK_DOMAIN_PROJECTION_ASSET_NAME}.defaults must be an object")
    value = defaults.get("evidence_verifies")
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{TASK_DOMAIN_PROJECTION_ASSET_NAME}.defaults.evidence_verifies must be a string list")
    return value


def _projection_fragment_limit() -> int:
    return _projection_limit("fragment")


def _projection_verify_limit() -> int:
    return _projection_limit("verify")


def _projection_limit(key: str) -> int:
    limits = _task_domain_projection_asset()["limits"]
    value = limits.get(key) if isinstance(limits, dict) else None
    if not isinstance(value, int) or value < 1:
        raise ValueError(f"{TASK_DOMAIN_PROJECTION_ASSET_NAME}.limits.{key} must be a positive integer")
    return value


def _dedupe(values) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result
