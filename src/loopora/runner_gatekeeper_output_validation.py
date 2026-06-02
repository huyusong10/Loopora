from __future__ import annotations

from dataclasses import dataclass

from loopora.runner_gatekeeper_evidence_gate import (
    GatekeeperEvidenceGateState,
    apply_gatekeeper_evidence_gate,
    build_gatekeeper_evidence_context,
    expand_self_evidence_refs,
    invalid_coverage_result_refs,
)
from loopora.residual_risk_support import residual_risk_is_unmanaged, residual_risk_policy_disallows_acceptance
from loopora.structured_booleans import structured_bool_is_true
from loopora.structured_numbers import structured_finite_number


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
