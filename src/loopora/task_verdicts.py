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
from loopora.task_verdict_status import (
    CONTRADICTORY_GATEKEEPER_PASS_SUMMARY as CONTRADICTORY_GATEKEEPER_PASS_SUMMARY,
    DISALLOWED_RESIDUAL_RISK_SUMMARY as DISALLOWED_RESIDUAL_RISK_SUMMARY,
    UNMANAGED_RESIDUAL_RISK_SUMMARY as UNMANAGED_RESIDUAL_RISK_SUMMARY,
    fallback_summary_for,
    status_from_gatekeeper,
    summary_for_task_verdict,
)

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
