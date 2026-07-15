from __future__ import annotations

from dataclasses import dataclass

from loopora.residual_risk_support import residual_risk_is_unmanaged, residual_risk_policy_disallows_acceptance
from loopora.utils import structured_bool_is_true
from loopora.utils import structured_finite_number


from loopora.evidence_gate import concrete_evidence_claim_count, has_measured_gate_evidence

from loopora.evidence_coverage import (
    NON_SUPPORTING_EVIDENCE_RESULTS,
    evidence_item_is_non_supporting_gatekeeper_ref,
    evidence_item_is_supporting_gatekeeper_ref,
)

@dataclass(frozen=True)
class GatekeeperEvidenceContext:
    known_by_id: dict[str, dict]
    known_ids: set[str]
    current_id: str

@dataclass
class GatekeeperEvidenceGateState:
    result: dict
    evidence_refs: list[str]
    evidence_claims: list[str]
    metric_scores: dict
    context: GatekeeperEvidenceContext
    blocking_issues: list[str]

def build_gatekeeper_evidence_context(
    evidence_items: object,
    *,
    known_ids: list[str],
    current_evidence_id: str,
) -> GatekeeperEvidenceContext:
    known_by_id = {
        str(item.get("id") or "").strip(): item
        for item in list(evidence_items or [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    known_id_set = set(known_by_id)
    known_id_set.update(known_ids)
    return GatekeeperEvidenceContext(
        known_by_id=known_by_id,
        known_ids=known_id_set,
        current_id=str(current_evidence_id or "").strip(),
    )

def expand_self_evidence_refs(evidence_refs: list[str], context: GatekeeperEvidenceContext) -> list[str]:
    if not context.current_id:
        return evidence_refs
    return [context.current_id if item == "self" else item for item in evidence_refs]

def invalid_coverage_result_refs(evidence_refs: list[str], context: GatekeeperEvidenceContext) -> list[str]:
    return [item for item in evidence_refs if item not in context.known_ids]

def apply_gatekeeper_evidence_gate(state: GatekeeperEvidenceGateState) -> list[str]:
    if not state.result["passed"]:
        return state.evidence_refs
    has_measured_evidence = has_measured_gate_evidence(state.metric_scores, state.result.get("metrics"))
    concrete_claims = concrete_evidence_claim_count(state.evidence_claims)
    evidence_refs = state.evidence_refs
    if not evidence_refs and state.context.current_id and concrete_claims > 0 and has_measured_evidence:
        evidence_refs = [state.context.current_id]

    invalid_refs = _invalid_evidence_refs(evidence_refs, state.context)
    supporting_refs = _supporting_upstream_refs(evidence_refs, state.context)
    blocking_non_supporting_refs = _blocking_non_supporting_upstream_refs(evidence_refs, state.context)
    if invalid_refs:
        state.blocking_issues.append(_invalid_ref_blocker(invalid_refs))
        state.result["passed"] = False
        evidence_refs = [
            item for item in evidence_refs if item == state.context.current_id or item in state.context.known_ids
        ]
    elif evidence_refs and not supporting_refs and blocking_non_supporting_refs:
        state.blocking_issues.append("gatekeeper_pass_refs_not_supporting_evidence")
        state.result["passed"] = False
    elif not supporting_refs and concrete_claims > 0 and has_measured_evidence and state.context.current_id:
        evidence_refs = list(dict.fromkeys([*evidence_refs, state.context.current_id]))
    elif not evidence_refs:
        state.blocking_issues.append("gatekeeper_pass_requires_evidence_refs")
        state.result["passed"] = False
    elif not supporting_refs and _non_supporting_upstream_refs(evidence_refs, state.context):
        state.blocking_issues.append("gatekeeper_pass_refs_not_supporting_evidence")
        state.result["passed"] = False
    elif not supporting_refs and not has_measured_evidence:
        state.blocking_issues.append("gatekeeper_pass_requires_upstream_or_measured_evidence")
        state.result["passed"] = False
    return evidence_refs

def _invalid_evidence_refs(evidence_refs: list[str], context: GatekeeperEvidenceContext) -> list[str]:
    return [item for item in evidence_refs if item != context.current_id and item not in context.known_ids]

def _supporting_upstream_refs(evidence_refs: list[str], context: GatekeeperEvidenceContext) -> list[str]:
    return [
        item
        for item in evidence_refs
        if item != context.current_id
        and item in context.known_ids
        and evidence_item_is_supporting_gatekeeper_ref(context.known_by_id.get(item, {}))
    ]

def _non_supporting_upstream_refs(evidence_refs: list[str], context: GatekeeperEvidenceContext) -> list[str]:
    refs: list[str] = []
    for item in evidence_refs:
        if item == context.current_id or item not in context.known_ids:
            continue
        evidence_item = context.known_by_id.get(item, {})
        if evidence_item_is_non_supporting_gatekeeper_ref(evidence_item):
            refs.append(item)
    return refs

def _blocking_non_supporting_upstream_refs(evidence_refs: list[str], context: GatekeeperEvidenceContext) -> list[str]:
    refs: list[str] = []
    for item in evidence_refs:
        if item == context.current_id or item not in context.known_ids:
            continue
        evidence_item = context.known_by_id.get(item, {})
        if str(evidence_item.get("result") or "").strip().lower() in NON_SUPPORTING_EVIDENCE_RESULTS:
            refs.append(item)
    return refs

def _invalid_ref_blocker(invalid_refs: list[str]) -> str:
    return "gatekeeper_evidence_refs_unknown: " + ", ".join(invalid_refs[:4]) + (
        "..." if len(invalid_refs) > 4 else ""
    )


BLOCKED_GATEKEEPER_COMPOSITE_SCORE = 0.89
BLOCKED_GATEKEEPER_SCORE_ADJUSTMENT_THRESHOLD = 0.9


def _string_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


@dataclass(frozen=True)
class GatekeeperResultFields:
    feedback: str
    blocking_issues: list[str]
    metric_scores: dict
    composite_score: object
    evidence_refs: list[str]
    evidence_claims: list[str]


def _metric_scores_from_result(result: dict) -> dict:
    metric_scores = result.get("metric_scores")
    if isinstance(metric_scores, dict):
        return _normalize_metric_scores(metric_scores)
    return _metric_scores_from_metrics(result.get("metrics"))


def _normalize_metric_scores(metric_scores: dict) -> dict:
    normalized = {}
    for name, value in metric_scores.items():
        if not isinstance(value, dict):
            continue
        normalized[str(name)] = {
            **value,
            "passed": structured_bool_is_true(value.get("passed")),
        }
    return normalized


def _metric_scores_from_metrics(metrics: object) -> dict:
    metric_scores = {}
    for metric in list(metrics or []):
        if not isinstance(metric, dict):
            continue
        name = str(metric.get("name", "")).strip()
        if not name:
            continue
        metric_scores[name] = {
            "value": metric.get("value"),
            "threshold": metric.get("threshold"),
            "passed": structured_bool_is_true(metric.get("passed")),
        }
    return metric_scores


def _composite_score_for_result(result: dict, metric_scores: dict) -> object:
    composite_score = result.get("composite_score")
    if composite_score is not None:
        return composite_score
    quality_metric = metric_scores.get("quality_score")
    if isinstance(quality_metric, dict):
        return quality_metric.get("value")
    return 1.0 if structured_bool_is_true(result.get("passed")) else 0.0


def _metric_rows_from_scores(metric_scores: dict) -> list[dict]:
    return [
        {
            "name": name,
            "value": value.get("value"),
            "threshold": value.get("threshold"),
            "passed": value.get("passed"),
        }
        for name, value in metric_scores.items()
        if isinstance(value, dict)
    ]


def _coverage_result_evidence_refs(value: object) -> list[str]:
    refs: list[str] = []
    for item in list(value or []):
        if not isinstance(item, dict):
            continue
        refs.extend(_string_list(item.get("evidence_refs")))
    return list(dict.fromkeys(refs))


def _adjust_blocked_composite_score(composite_score: object, result: dict, blocking_issues: list[str]) -> object:
    score = structured_finite_number(composite_score)
    if not result["passed"] and score >= BLOCKED_GATEKEEPER_SCORE_ADJUSTMENT_THRESHOLD and blocking_issues:
        return BLOCKED_GATEKEEPER_COMPOSITE_SCORE
    return score


def _gatekeeper_residual_risk_blocker(code: str, residual_risks: list[str], guidance: str) -> str:
    detail = "; ".join(residual_risks[:2])
    if detail:
        return f"{code}: {detail}. {guidance}"
    return f"{code}: {guidance}"


def _populate_gatekeeper_result(result: dict, fields: GatekeeperResultFields) -> dict:
    result["decision_summary"] = str(result.get("decision_summary") or "").strip() or (
        "The loop still needs more evidence." if not result["passed"] else "All checks passed."
    )
    result["feedback_to_builder"] = fields.feedback
    result["feedback_to_generator"] = fields.feedback
    result["blocking_issues"] = fields.blocking_issues
    result["hard_constraint_violations"] = fields.blocking_issues
    result["metric_scores"] = fields.metric_scores
    result["composite_score"] = structured_finite_number(
        fields.composite_score,
        default=1.0 if result["passed"] else 0.0,
    )
    result["evidence_refs"] = fields.evidence_refs
    result["evidence_claims"] = fields.evidence_claims
    result["residual_risks"] = _string_list(result.get("residual_risks"))
    result["coverage_results"] = [item for item in list(result.get("coverage_results") or []) if isinstance(item, dict)]
    result["evidence_gate_status"] = "passed" if result["passed"] else ("blocked" if fields.blocking_issues else "not_passed")
    result.setdefault("failed_check_ids", [])
    result.setdefault("priority_failures", [])
    return result


def coerce_gatekeeper_output(
    output: dict,
    *,
    evidence_context: dict | None = None,
    current_evidence_id: str = "",
    compiled_spec: dict | None = None,
) -> dict:
    result = dict(output)
    feedback = str(result.get("feedback_to_builder") or result.get("feedback_to_generator") or "").strip()
    blocking_issues = _string_list(result.get("blocking_issues") or result.get("hard_constraint_violations"))
    evidence_refs = _string_list(result.get("evidence_refs") or result.get("evidence_item_ids"))
    evidence_claims = _string_list(result.get("evidence_claims") or result.get("evidence_summary"))
    gate_context = build_gatekeeper_evidence_context(
        (evidence_context or {}).get("items"),
        known_ids=_string_list((evidence_context or {}).get("known_ids")),
        current_evidence_id=current_evidence_id,
    )
    evidence_refs = expand_self_evidence_refs(evidence_refs, gate_context)
    metric_scores = _metric_scores_from_result(result)
    composite_score = _composite_score_for_result(result, metric_scores)
    result["metrics"] = _metric_rows_from_scores(metric_scores)
    result["passed"] = structured_bool_is_true(result.get("passed"))
    residual_risks = _string_list(result.get("residual_risks"))
    residual_risk_policy = str((compiled_spec or {}).get("residual_risk") or "").strip()
    if result["passed"] and residual_risks and residual_risk_policy_disallows_acceptance(residual_risk_policy):
        guidance = "The run contract disallows accepted residual risk; resolve it or report it as blocking before passing."
        blocking_issues.append(
            _gatekeeper_residual_risk_blocker("gatekeeper_pass_violates_no_residual_risk_policy", residual_risks, guidance)
        )
        if not feedback:
            feedback = guidance
        result["passed"] = False
    if result["passed"] and any(residual_risk_is_unmanaged(risk) for risk in residual_risks):
        guidance = "Move it to blocking_issues, remove it, or name an owner, follow-up, or acceptance path before passing."
        blocking_issues.append(
            _gatekeeper_residual_risk_blocker("gatekeeper_pass_has_unmanaged_residual_risk", residual_risks, guidance)
        )
        if not feedback:
            feedback = guidance
        result["passed"] = False
    evidence_refs = apply_gatekeeper_evidence_gate(
        GatekeeperEvidenceGateState(
            result=result,
            evidence_refs=evidence_refs,
            evidence_claims=evidence_claims,
            metric_scores=metric_scores,
            context=gate_context,
            blocking_issues=blocking_issues,
        )
    )
    invalid_coverage_refs = invalid_coverage_result_refs(
        _coverage_result_evidence_refs(result.get("coverage_results")),
        gate_context,
    )
    if result["passed"] and invalid_coverage_refs:
        blocking_issues.append(
            "gatekeeper_coverage_evidence_refs_unknown: "
            + ", ".join(invalid_coverage_refs[:4])
            + ("..." if len(invalid_coverage_refs) > 4 else "")
        )
        result["passed"] = False
    composite_score = _adjust_blocked_composite_score(composite_score, result, blocking_issues)
    return _populate_gatekeeper_result(
        result,
        GatekeeperResultFields(
            feedback=feedback,
            blocking_issues=blocking_issues,
            metric_scores=metric_scores,
            composite_score=composite_score,
            evidence_refs=evidence_refs,
            evidence_claims=evidence_claims,
        ),
    )
