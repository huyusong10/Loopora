from __future__ import annotations

"""Task-verdict status and summary derivation."""

from collections.abc import Mapping
from typing import Any

from loopora.coverage_target_semantics import coverage_target_is_required
from loopora.residual_risk_support import (
    residual_risk_is_managed,
    residual_risk_is_meaningful,
    residual_risk_is_unmanaged,
    residual_risk_policy_disallows_acceptance,
)
from loopora.task_verdict_buckets import (
    clean_text,
    string_list,
    verdict_blockers,
    verdict_residual_risk_texts,
)

UNMANAGED_RESIDUAL_RISK_SUMMARY = "GateKeeper reported residual risk without a named owner, follow-up, or acceptance path."
DISALLOWED_RESIDUAL_RISK_SUMMARY = "GateKeeper reported residual risk even though the run contract disallows accepted residual risk."
CONTRADICTORY_GATEKEEPER_PASS_SUMMARY = "GateKeeper reported blocking issues while also marking the task passed."


def status_from_gatekeeper(
    verdict: Mapping[str, Any],
    buckets: Mapping[str, list[dict]],
    coverage: Mapping[str, Any],
    compiled_spec: Mapping[str, Any],
    *,
    require_coverage: bool,
) -> str:
    if not verdict:
        return ""
    if verdict.get("passed") is True:
        return _passed_gatekeeper_status(verdict, coverage, compiled_spec, require_coverage=require_coverage)
    if verdict.get("passed") is False:
        return "failed" if buckets.get("blocking") or verdict_blockers(verdict) else "insufficient_evidence"
    return ""


def summary_for_task_verdict(
    status: str,
    verdict: Mapping[str, Any],
    coverage: Mapping[str, Any],
    compiled_spec: Mapping[str, Any],
    *,
    fallback_summary: str,
) -> str:
    coverage_summary = coverage.get("summary") if isinstance(coverage.get("summary"), Mapping) else {}
    coverage_reason = clean_text(coverage_summary.get("reason"), max_length=600)
    if verdict.get("passed") is True and status == "failed" and verdict_blockers(verdict):
        return CONTRADICTORY_GATEKEEPER_PASS_SUMMARY
    if (
        verdict.get("passed") is True
        and status == "insufficient_evidence"
        and _gatekeeper_reports_residual_risk_disallowed_by_policy(verdict, coverage, compiled_spec)
    ):
        return DISALLOWED_RESIDUAL_RISK_SUMMARY
    if verdict.get("passed") is True and status == "insufficient_evidence" and _gatekeeper_reports_unmanaged_residual_risk(verdict, coverage):
        return UNMANAGED_RESIDUAL_RISK_SUMMARY
    if verdict.get("passed") is True and status in {"failed", "insufficient_evidence"} and coverage_reason:
        return coverage_reason
    decision_summary = clean_text(verdict.get("decision_summary"), max_length=600) if _has_literal_gatekeeper_verdict(verdict) else ""
    return decision_summary or (coverage_reason or fallback_summary)


def fallback_summary_for(status: str, source: str, run_status: str) -> str:
    status_summaries = {
        "passed": "GateKeeper found sufficient evidence for the task.",
        "passed_with_residual_risk": "GateKeeper passed the task with residual risk still visible.",
        "failed": "The latest judgment reported blocking evidence against the task.",
        "insufficient_evidence": ("The run reached its lifecycle boundary, but the evidence is not strong enough for a task pass."),
    }
    if source == "legacy":
        return "This legacy run has no persisted task verdict; Loopora derived a compatibility verdict on read."
    return status_summaries.get(status, f"The run is {run_status}, and no evidence-based task verdict is available.")


def _passed_gatekeeper_status(
    verdict: Mapping[str, Any],
    coverage: Mapping[str, Any],
    compiled_spec: Mapping[str, Any],
    *,
    require_coverage: bool,
) -> str:
    required_coverage_status = _required_coverage_status(coverage)
    insufficient_evidence = (
        required_coverage_status == "incomplete"
        or (require_coverage and required_coverage_status == "unknown")
        or _gatekeeper_reports_residual_risk_disallowed_by_policy(verdict, coverage, compiled_spec)
        or _gatekeeper_reports_unmanaged_residual_risk(verdict, coverage)
    )
    status = "passed"
    if verdict_blockers(verdict) or _coverage_has_blocked_target(coverage):
        status = "failed"
    elif insufficient_evidence:
        status = "insufficient_evidence"
    elif _gatekeeper_reports_managed_residual_risk(verdict, coverage):
        status = "passed_with_residual_risk"
    return status


def _coverage_has_blocked_target(coverage: Mapping[str, Any]) -> bool:
    targets = coverage.get("targets")
    if not isinstance(targets, list):
        return False
    return any(isinstance(target, Mapping) and str(target.get("status") or "").strip().lower() == "blocked" for target in targets)


def _gatekeeper_reports_managed_residual_risk(
    verdict: Mapping[str, Any],
    coverage: Mapping[str, Any],
) -> bool:
    return any(residual_risk_is_managed(risk) for risk in _gatekeeper_residual_risk_texts(verdict, coverage))


def _gatekeeper_reports_unmanaged_residual_risk(
    verdict: Mapping[str, Any],
    coverage: Mapping[str, Any],
) -> bool:
    return any(residual_risk_is_unmanaged(risk) for risk in _gatekeeper_residual_risk_texts(verdict, coverage))


def _gatekeeper_reports_residual_risk_disallowed_by_policy(
    verdict: Mapping[str, Any],
    coverage: Mapping[str, Any],
    compiled_spec: Mapping[str, Any],
) -> bool:
    return residual_risk_policy_disallows_acceptance(compiled_spec.get("residual_risk")) and any(
        residual_risk_is_meaningful(risk) for risk in _gatekeeper_residual_risk_texts(verdict, coverage)
    )


def _gatekeeper_residual_risk_texts(verdict: Mapping[str, Any], coverage: Mapping[str, Any]) -> list[str]:
    risks = verdict_residual_risk_texts(verdict)
    latest_gatekeeper = coverage.get("latest_gatekeeper")
    if isinstance(latest_gatekeeper, Mapping):
        risks.extend(string_list(latest_gatekeeper.get("residual_risk")))
    return risks


def _required_coverage_status(coverage: Mapping[str, Any]) -> str:
    targets = coverage.get("targets")
    if not isinstance(targets, list):
        return "unknown"
    required_targets = [target for target in targets if isinstance(target, Mapping) and coverage_target_is_required(target)]
    if not required_targets:
        return "unknown"
    statuses = {str(target.get("status") or "missing").strip().lower() for target in required_targets}
    if "blocked" in statuses:
        return "blocked"
    if any(status != "covered" for status in statuses):
        return "incomplete"
    return "covered"


def _has_literal_gatekeeper_verdict(verdict: Mapping[str, Any]) -> bool:
    return verdict.get("passed") is True or verdict.get("passed") is False
