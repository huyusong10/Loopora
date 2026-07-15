from __future__ import annotations

import re
from typing import Literal

AgentCoreBlockerKind = Literal[
    "evidence_refs_unknown",
    "coverage_target_unknown",
    "dispatch_mismatch",
    "inline_forbidden",
    "schema_mismatch",
    "stale_step",
    "other_core_validation",
]

GENERIC_NEXT_ACTIONS = {
    "",
    "Continue only after the blocking issues are resolved.",
    "Continue only after the blocking issues are resolved",
    "None.",
    "None",
    "No action needed.",
    "No action needed",
    "No action required.",
    "No action required",
    "N/A",
    "n/a",
    "na",
}

BLOCKER_EXPLANATIONS = {
    "gatekeeper_pass_has_unmanaged_residual_risk": (
        "residual_risks must name an owner, follow-up, or acceptance path; otherwise move the risk to blocking_issues before passing"
    ),
    "gatekeeper_pass_violates_no_residual_risk_policy": (
        "the run contract disallows accepted residual risk; resolve the risk or report it as blocking before passing"
    ),
    "gatekeeper_pass_refs_not_supporting_evidence": (
        "a pass must cite upstream evidence that is not blocked, failed, rejected, or errored; produce direct project-owned proof or mark passed=false"
    ),
    "gatekeeper_pass_requires_evidence_refs": (
        "a pass must cite exact supporting evidence_refs from known_evidence_ids; copy a supporting id or mark passed=false"
    ),
    "gatekeeper_pass_requires_upstream_or_measured_evidence": (
        "a pass needs supporting upstream evidence or measured self evidence; produce that proof before asking GateKeeper to pass"
    ),
}

BLOCKER_NEXT_ACTIONS = (
    (
        "gatekeeper_pass_has_unmanaged_residual_risk",
        "Resolve the residual risk or make it managed with an owner, follow-up, or acceptance path before asking GateKeeper to pass again.",
    ),
    (
        "gatekeeper_pass_violates_no_residual_risk_policy",
        "Resolve the residual risk or report it as blocking before asking GateKeeper to pass again.",
    ),
    (
        "gatekeeper_pass_refs_not_supporting_evidence",
        (
            "Produce new project-owned proof or cite a non-blocked supporting evidence ref before asking GateKeeper to pass again; "
            "otherwise submit GateKeeper with passed=false and blocking_issues."
        ),
    ),
    (
        "gatekeeper_pass_requires_evidence_refs",
        "Copy exact supporting evidence_refs from known_evidence_ids before asking GateKeeper to pass again.",
    ),
    (
        "gatekeeper_pass_requires_upstream_or_measured_evidence",
        "Add upstream or measured evidence for the required targets before asking GateKeeper to pass again.",
    ),
)

CORE_BLOCKER_MARKERS: tuple[tuple[AgentCoreBlockerKind, tuple[str, ...]], ...] = (
    ("evidence_refs_unknown", ("evidence_refs_unknown",)),
    ("coverage_target_unknown", ("coverage_results_unknown_target_id",)),
    ("dispatch_mismatch", ("agent-native submit used", "target_agent", "actual_agent")),
    ("inline_forbidden", ("inline",)),
    ("schema_mismatch", ("output_schema", "result does not match")),
    ("stale_step", ("submitted step_id does not match", "agent-native step was already submitted")),
)


def actionable_blocking_item(item: str) -> str:
    cleaned = str(item or "").strip()
    if not cleaned or ":" in cleaned:
        return cleaned
    target_explanation = coverage_target_blocker_explanation(cleaned)
    if target_explanation:
        return f"{cleaned}: {target_explanation}"
    explanation = BLOCKER_EXPLANATIONS.get(cleaned)
    return f"{cleaned}: {explanation}" if explanation else cleaned


def coverage_target_blocker_explanation(cleaned: str) -> str:
    if re.fullmatch(r"check_\d+", cleaned):
        return "required check id; see required_coverage.missing_check_ids and top_coverage_gaps for the contract text"
    if re.fullmatch(r"done_when\.check_\d+", cleaned):
        return "coverage target id; see required_coverage.top_coverage_gaps for status, text, and evidence refs"
    if re.fullmatch(r"(?:fake_done\.risk|evidence_preference\.pref|success_surface\.surface)_\d+", cleaned):
        return "coverage target id; see top_coverage_gaps for status, text, and evidence refs"
    if cleaned == "gatekeeper.finish":
        return "GateKeeper finish target; cite supporting evidence or keep the run blocked"
    return ""


def actionable_next_action(action: str, blocking_items: list[str]) -> str:
    cleaned = str(action or "").strip()
    normalized_cleaned = cleaned.strip(".").strip().lower()
    if cleaned not in GENERIC_NEXT_ACTIONS and normalized_cleaned not in {
        "none",
        "n/a",
        "na",
        "not applicable",
        "no action needed",
        "no action required",
    }:
        return cleaned
    joined = " ".join(blocking_items)
    for marker, next_action in BLOCKER_NEXT_ACTIONS:
        if marker in joined:
            return next_action
    return cleaned


def core_blocker_kind(error: str) -> AgentCoreBlockerKind:
    for kind, markers in CORE_BLOCKER_MARKERS:
        if any(marker in error for marker in markers):
            return kind
    return "other_core_validation"
