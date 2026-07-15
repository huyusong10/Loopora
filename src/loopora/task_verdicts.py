from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from loopora.evidence_coverage import load_or_build_evidence_coverage_projection
from loopora.run_artifacts import RunArtifactLayout
from loopora.task_verdict_buckets import (
    BUCKET_KEYS,
    DISALLOWED_RESIDUAL_RISK_REASON as DISALLOWED_RESIDUAL_RISK_REASON,
    TARGET_STATUS_BUCKETS as TARGET_STATUS_BUCKETS,
    build_task_verdict_buckets as _build_buckets,
    bucket_list as _bucket_list,
    clean_text as _clean_text,
)

"""Task-verdict status and summary derivation."""



from loopora.coverage_target_semantics import coverage_target_is_required

from loopora.residual_risk_support import (
    residual_risk_is_managed,
    residual_risk_is_meaningful,
    residual_risk_text_matches_or_previews_any,
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
        for risk in string_list(latest_gatekeeper.get("residual_risk")):
            if not residual_risk_text_matches_or_previews_any(risk, risks):
                risks.append(risk)
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

TASK_VERDICT_STATUSES = {
    "not_evaluated",
    "passed",
    "failed",
    "insufficient_evidence",
    "passed_with_residual_risk",
}
PASSING_TASK_VERDICT_STATUSES = frozenset({"passed", "passed_with_residual_risk"})
TASK_VERDICT_SOURCES = {"gatekeeper", "rounds_completion", "run_status", "legacy"}
TERMINAL_RUN_STATUSES = {"succeeded", "failed", "stopped"}


def hydrate_run_status_and_task_verdict(run: dict) -> dict:
    if not run:
        return run
    run_status = str(run.get("status") or "").strip() or "unknown"
    task_verdict = normalize_task_verdict(run.get("task_verdict_json"))
    if not task_verdict:
        legacy_source = bool(run.get("last_verdict_json"))
        task_verdict = build_task_verdict(
            {**run, "status": run_status},
            run_dir=_run_dir_for(run),
            legacy=legacy_source,
        )
    run["run_status"] = run_status
    run["task_verdict"] = task_verdict
    run["task_verdict_json"] = task_verdict
    return run


def build_task_verdict(
    run: Mapping[str, Any],
    *,
    run_dir: Path | None = None,
    final_reason: str = "",
    legacy: bool = False,
) -> dict:
    run_status = str(run.get("status") or "").strip() or "unknown"
    raw_verdict = run.get("last_verdict_json")
    if not isinstance(raw_verdict, Mapping):
        raw_verdict = {}
    coverage = _load_coverage(run, run_dir)
    compiled_spec = _run_compiled_spec(run)
    buckets = _build_buckets(coverage, raw_verdict, compiled_spec)
    source = "legacy" if legacy else "run_status"
    status = "not_evaluated"

    gatekeeper_status = status_from_gatekeeper(raw_verdict, buckets, coverage, compiled_spec, require_coverage=not legacy)
    if gatekeeper_status:
        status = gatekeeper_status
        source = "legacy" if legacy else "gatekeeper"
    elif str(final_reason or "").strip() == "rounds_completed":
        status = "insufficient_evidence"
        source = "legacy" if legacy else "rounds_completion"
    elif run_status in TERMINAL_RUN_STATUSES:
        status = "not_evaluated"
        source = "legacy" if legacy else "run_status"

    summary = summary_for_task_verdict(
        status,
        raw_verdict,
        coverage,
        compiled_spec,
        fallback_summary=fallback_summary_for(status, source, run_status),
    )
    return {
        "status": status,
        "source": source,
        "summary": summary,
        "buckets": buckets,
    }


def normalize_task_verdict(value: object) -> dict:
    if not isinstance(value, Mapping):
        return {}
    status = str(value.get("status") or "").strip()
    source = str(value.get("source") or "").strip()
    if status not in TASK_VERDICT_STATUSES or source not in TASK_VERDICT_SOURCES:
        return {}
    raw_buckets = value.get("buckets") if isinstance(value.get("buckets"), Mapping) else {}
    buckets = {key: _bucket_list(raw_buckets.get(key)) for key in BUCKET_KEYS}
    return {
        "status": status,
        "source": source,
        "summary": _clean_text(value.get("summary"), max_length=600),
        "buckets": buckets,
    }


def _run_dir_for(run: Mapping[str, Any]) -> Path | None:
    runs_dir = str(run.get("runs_dir") or "").strip()
    return Path(runs_dir) if runs_dir else None


def _load_coverage(run: Mapping[str, Any], run_dir: Path | None) -> dict:
    target_dir = run_dir or _run_dir_for(run)
    if target_dir is None:
        return {}
    try:
        return load_or_build_evidence_coverage_projection(RunArtifactLayout(target_dir))
    except (OSError, UnicodeError, ValueError):
        return {}


def _run_compiled_spec(run: Mapping[str, Any]) -> Mapping[str, Any]:
    compiled_spec = run.get("compiled_spec")
    if isinstance(compiled_spec, Mapping):
        return compiled_spec
    compiled_spec_json = run.get("compiled_spec_json")
    if isinstance(compiled_spec_json, Mapping):
        return compiled_spec_json
    return {}
