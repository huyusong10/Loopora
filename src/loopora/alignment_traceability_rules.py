from __future__ import annotations

from pathlib import Path
import re

from loopora.alignment_semantics import text_mentions_loop_fit_contradiction
from loopora.alignment_traceability_agent_candidate_rules import (
    alignment_agent_candidate_evidence_preference_issues,
    alignment_agent_candidate_execution_strategy_issues,
    alignment_agent_candidate_fake_done_issues,
    alignment_agent_candidate_residual_risk_policy_issues,
    alignment_agent_candidate_success_surface_issues,
    alignment_agent_candidate_tradeoff_issues,
)
from loopora.alignment_traceability_categories import (
    agent_candidate_evidence_preference_categories,
    agent_candidate_execution_strategy_categories,
    agent_candidate_fake_done_categories,
    agent_candidate_residual_risk_policy_categories,
    agent_candidate_success_surface_categories,
    agent_candidate_tradeoff_categories,
)
from loopora.alignment_traceability_terms import (
    ALIGNMENT_AGENT_CANDIDATE_GENERIC_TERMS as ALIGNMENT_AGENT_CANDIDATE_GENERIC_TERMS,
    ALIGNMENT_LOOP_FIT_TRACEABILITY_GENERIC_TERMS,
    ALIGNMENT_TRACEABILITY_CJK_STOP_CHARS as ALIGNMENT_TRACEABILITY_CJK_STOP_CHARS,
    ALIGNMENT_TRACEABILITY_GENERIC_CJK_TERMS as ALIGNMENT_TRACEABILITY_GENERIC_CJK_TERMS,
    ALIGNMENT_TRACEABILITY_GENERIC_TERMS as ALIGNMENT_TRACEABILITY_GENERIC_TERMS,
    agent_candidate_traceability_terms,
    agreement_cjk_traceability_terms as agreement_cjk_traceability_terms,
    agreement_repeated_cjk_traceability_terms,
    agreement_traceability_terms,
)
from loopora.service_alignment_traceability_projection import (
    alignment_bundle_agreement_projection_text,
    alignment_bundle_runtime_responsibility_projection_text,
    alignment_governance_marker_responsibility_issues,
    alignment_traceability_term_is_present,
    normalize_alignment_traceability_text,
)
from loopora.service_alignment_workdir_snapshot import alignment_workdir_snapshot, alignment_workdir_snapshot_has_governance_markers

ALIGNMENT_AGREEMENT_TRACEABILITY_KEYS = [
    "loop_fit",
    "task_scope",
    "success_surface",
    "fake_done_risks",
    "evidence_preferences",
    "execution_strategy",
    "residual_risk_policy",
    "judgment_tradeoffs",
    "local_governance",
    "role_posture",
    "workflow_shape",
    "workdir_facts",
]


def alignment_bundle_agreement_traceability_issues(session: dict, bundle: dict) -> list[str]:
    agreement = session.get("working_agreement") if isinstance(session.get("working_agreement"), dict) else {}
    evidence = agreement.get("readiness_evidence") if isinstance(agreement.get("readiness_evidence"), dict) else {}
    bundle_text = alignment_bundle_agreement_projection_text(bundle)
    normalized_bundle_text = normalize_alignment_traceability_text(bundle_text)
    normalized_runtime_text = normalize_alignment_traceability_text(alignment_bundle_runtime_responsibility_projection_text(bundle))
    issues: list[str] = []
    if evidence:
        repeated_cjk_terms = agreement_repeated_cjk_traceability_terms(evidence.values())
        for key in ALIGNMENT_AGREEMENT_TRACEABILITY_KEYS:
            terms = agreement_traceability_terms(evidence.get(key))
            if key == "loop_fit":
                terms = [term for term in terms if term not in ALIGNMENT_LOOP_FIT_TRACEABILITY_GENERIC_TERMS]
            terms.extend(term for term in repeated_cjk_terms if term in str(evidence.get(key) or "") and term not in terms)
            if key == "workdir_facts":
                terms = [term for term in terms if "/" in term or "." in term]
            if key == "local_governance":
                terms = [term for term in terms if "/" in term or "." in term]
            if not terms:
                continue
            matched = [term for term in terms if alignment_traceability_term_is_present(term, normalized_bundle_text=normalized_bundle_text)]
            required_matches = 1 if len(terms) < 4 else 2
            if len(matched) >= required_matches:
                continue
            issues.append(
                "alignment bundle must project confirmed working agreement evidence into runnable surfaces: "
                f"{key} missing {', '.join(terms[:5])}"
            )
        issues.extend(
            alignment_governance_marker_responsibility_issues(
                evidence,
                normalized_runtime_text=normalized_runtime_text,
            )
        )
        issues.extend(
            alignment_agreement_category_projection_issues(
                evidence,
                normalized_bundle_text=normalized_bundle_text,
            )
        )
    workdir_snapshot = alignment_workdir_snapshot(Path(session["workdir"])) if session.get("workdir") else ""
    if alignment_workdir_snapshot_has_governance_markers(workdir_snapshot):
        issues.extend(
            alignment_governance_marker_responsibility_issues(
                {"workdir_snapshot": workdir_snapshot},
                normalized_runtime_text=normalized_runtime_text,
            )
        )
    return issues

def alignment_agreement_category_projection_issues(evidence: dict, *, normalized_bundle_text: str) -> list[str]:
    category_checks = (
        (
            "success_surface",
            "success surface",
            agent_candidate_success_surface_categories(
                str(evidence.get("success_surface") or ""),
                require_explicit_marker=False,
            ),
            1,
        ),
        (
            "fake_done_risks",
            "fake-done risks",
            agent_candidate_fake_done_categories(
                str(evidence.get("fake_done_risks") or ""),
                require_explicit_marker=False,
            ),
            1,
        ),
        (
            "evidence_preferences",
            "evidence preferences",
            agent_candidate_evidence_preference_categories(
                str(evidence.get("evidence_preferences") or ""),
                require_explicit_marker=False,
            ),
            1,
        ),
        (
            "execution_strategy",
            "execution strategy",
            agent_candidate_execution_strategy_categories(
                str(evidence.get("execution_strategy") or ""),
                require_explicit_marker=False,
            ),
            2,
        ),
        (
            "residual_risk_policy",
            "residual-risk policy",
            agent_candidate_residual_risk_policy_categories(
                str(evidence.get("residual_risk_policy") or ""),
                require_explicit_marker=False,
            ),
            1,
        ),
        (
            "judgment_tradeoffs",
            "judgment tradeoffs",
            agent_candidate_tradeoff_categories(str(evidence.get("judgment_tradeoffs") or "")),
            2,
        ),
    )
    issues: list[str] = []
    for _key, label, categories, minimum_category_count in category_checks:
        if len(categories) < minimum_category_count:
            continue
        missing = [
            category_label
            for category_label, bundle_pattern in categories
            if not re.search(bundle_pattern, normalized_bundle_text, re.I)
        ]
        if not missing:
            continue
        issues.append(
            "alignment bundle must project confirmed working agreement "
            f"{label} into runnable surfaces: missing {', '.join(missing)}"
        )
    return issues


def alignment_agent_candidate_traceability_issues(task_text: str, bundle: dict) -> list[str]:
    task_text = str(task_text or "")
    issues: list[str] = []
    if text_mentions_loop_fit_contradiction(task_text):
        issues.append(
            "agent-first candidate cannot compile a Loop when the host Agent task summary says Loopora is not fit; "
            "ask the user or use Web review before generating a runnable Loop"
        )
    normalized_bundle_text = normalize_alignment_traceability_text(alignment_bundle_agreement_projection_text(bundle))
    normalized_runtime_text = normalize_alignment_traceability_text(alignment_bundle_runtime_responsibility_projection_text(bundle))
    terms = agent_candidate_traceability_terms(task_text)
    if terms:
        matched = [term for term in terms if alignment_traceability_term_is_present(term, normalized_bundle_text=normalized_bundle_text)]
        required_matches = 1 if len(terms) < 4 else 2
        if len(matched) < required_matches:
            issues.append(
                "agent-first candidate must project the host Agent task summary into runnable surfaces: "
                + "missing "
                + ", ".join(terms[:5])
            )
    issues.extend(
        alignment_governance_marker_responsibility_issues(
            {"agent_candidate": task_text},
            normalized_runtime_text=normalized_runtime_text,
        )
    )
    issues.extend(
        alignment_agent_candidate_tradeoff_issues(
            task_text,
            normalized_bundle_text=normalized_bundle_text,
        )
    )
    issues.extend(
        alignment_agent_candidate_execution_strategy_issues(
            task_text,
            normalized_bundle_text=normalized_bundle_text,
        )
    )
    issues.extend(
        alignment_agent_candidate_residual_risk_policy_issues(
            task_text,
            normalized_bundle_text=normalized_bundle_text,
        )
    )
    issues.extend(
        alignment_agent_candidate_success_surface_issues(
            task_text,
            normalized_bundle_text=normalized_bundle_text,
        )
    )
    issues.extend(
        alignment_agent_candidate_fake_done_issues(
            task_text,
            normalized_bundle_text=normalized_bundle_text,
        )
    )
    issues.extend(
        alignment_agent_candidate_evidence_preference_issues(
            task_text,
            normalized_bundle_text=normalized_bundle_text,
        )
    )
    return issues
