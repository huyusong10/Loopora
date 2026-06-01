from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from loopora.bundle_semantic_text import _semantic_text_is_specific
from loopora.residual_risk_support import residual_risk_is_unmanaged


def _lint_alignment_spec_semantics(compiled_spec: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if not _semantic_text_is_specific(compiled_spec.get("goal"), min_chars=72):
        issues.append("spec Task must describe the concrete user-facing task")
    issues.extend(_lint_alignment_spec_contract_sections(compiled_spec))
    return issues


def _lint_alignment_spec_contract_sections(compiled_spec: Mapping[str, Any]) -> list[str]:
    return [
        *_lint_alignment_done_when_semantics(compiled_spec),
        *_lint_alignment_success_and_fake_done_semantics(compiled_spec),
        *_lint_alignment_evidence_and_risk_semantics(compiled_spec),
    ]


def _lint_alignment_done_when_semantics(compiled_spec: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if not compiled_spec.get("checks"):
        issues.append("spec must include at least one Done When bullet")
    return issues


def _lint_alignment_success_and_fake_done_semantics(compiled_spec: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if not compiled_spec.get("success_surface"):
        issues.append("spec must include at least one Success Surface bullet")
    if not compiled_spec.get("fake_done_states"):
        issues.append("spec must include at least one Fake Done bullet")
    return issues


def _lint_alignment_evidence_and_risk_semantics(compiled_spec: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if not compiled_spec.get("evidence_preferences"):
        issues.append("spec must include at least one Evidence Preferences bullet")
    residual_risk = str(compiled_spec.get("residual_risk", "") or "").strip()
    if not residual_risk:
        issues.append("spec must include Residual Risk guidance")
    elif residual_risk_is_unmanaged(residual_risk):
        issues.append("spec Residual Risk guidance must name accepted risk handling or fail closed")
    return issues
