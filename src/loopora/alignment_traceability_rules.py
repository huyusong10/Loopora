from __future__ import annotations

from pathlib import Path
from loopora.alignment_semantics import text_mentions_loop_fit_contradiction
from loopora.alignment_traceability_terms import (
    ALIGNMENT_AGENT_CANDIDATE_GENERIC_TERMS as ALIGNMENT_AGENT_CANDIDATE_GENERIC_TERMS,
    ALIGNMENT_LOOP_FIT_TRACEABILITY_GENERIC_TERMS,
    ALIGNMENT_TRACEABILITY_CJK_STOP_CHARS as ALIGNMENT_TRACEABILITY_CJK_STOP_CHARS,
    ALIGNMENT_TRACEABILITY_GENERIC_CJK_TERMS as ALIGNMENT_TRACEABILITY_GENERIC_CJK_TERMS,
    ALIGNMENT_TRACEABILITY_GENERIC_TERMS as ALIGNMENT_TRACEABILITY_GENERIC_TERMS,
    agent_candidate_task_anchor_terms,
    agent_candidate_traceability_terms as agent_candidate_traceability_terms,
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
    workdir_snapshot = alignment_workdir_snapshot(Path(session["workdir"])) if session.get("workdir") else ""
    if alignment_workdir_snapshot_has_governance_markers(workdir_snapshot):
        issues.extend(
            alignment_governance_marker_responsibility_issues(
                {"workdir_snapshot": workdir_snapshot},
                normalized_runtime_text=normalized_runtime_text,
            )
        )
    return issues

def alignment_agent_candidate_traceability_issues(
    task_text: str,
    bundle: dict,
    *,
    include_loop_fit_contradiction: bool = True,
    include_candidate_contract_issues: bool = True,
) -> list[str]:
    task_text = str(task_text or "")
    issues: list[str] = []
    if include_loop_fit_contradiction and text_mentions_loop_fit_contradiction(task_text):
        issues.append(
            "Agent-native candidate cannot compile a Loop when the host Agent task context says Loopora is not fit; "
            "ask the user or use Web review before generating a runnable Loop"
        )
    normalized_bundle_text = normalize_alignment_traceability_text(alignment_bundle_agreement_projection_text(bundle))
    normalized_runtime_text = normalize_alignment_traceability_text(alignment_bundle_runtime_responsibility_projection_text(bundle))
    terms = agent_candidate_task_anchor_terms(task_text)
    if terms:
        matched = [term for term in terms if alignment_traceability_term_is_present(term, normalized_bundle_text=normalized_bundle_text)]
        required_matches = 1 if len(terms) < 4 else 2
        if len(matched) < required_matches:
            issues.append(
                "Agent-native candidate must project the host Agent task context into runnable surfaces: missing "
                + ", ".join(terms[:5])
            )
    if not include_candidate_contract_issues:
        return issues
    issues.extend(
        alignment_governance_marker_responsibility_issues(
            {"agent_candidate": task_text},
            normalized_runtime_text=normalized_runtime_text,
        )
    )
    return issues
