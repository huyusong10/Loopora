from __future__ import annotations

from dataclasses import dataclass

from loopora.evidence_coverage_summary import summarize_evidence_coverage_projection
from loopora.structured_numbers import structured_non_negative_int


@dataclass(frozen=True)
class RunnerEvidenceProgressStagnationRequest:
    stagnation: dict
    coverage: dict
    coverage_path_available: bool
    trigger_window: object


def runner_evidence_progress_stagnation(request: RunnerEvidenceProgressStagnationRequest) -> dict:
    coverage = request.coverage if isinstance(request.coverage, dict) else {}
    coverage_summary = summarize_evidence_coverage_projection(
        coverage,
        coverage_path_available=request.coverage_path_available,
    )
    covered_checks = structured_non_negative_int(coverage_summary.get("covered_check_count"))
    missing_checks = structured_non_negative_int(coverage_summary.get("missing_check_count"))
    recent_counts = _recent_covered_check_counts(request.stagnation.get("recent_covered_check_counts"))
    previous_covered_checks = structured_non_negative_int(recent_counts[-1]) if recent_counts else 0
    no_progress = bool(recent_counts) and covered_checks <= previous_covered_checks
    consecutive_no_progress = structured_non_negative_int(request.stagnation.get("consecutive_no_required_coverage_delta"))
    consecutive_no_progress = consecutive_no_progress + 1 if no_progress and missing_checks > 0 else 0
    trigger_window = structured_non_negative_int(request.trigger_window, default=1) or 1
    evidence_progress_mode = "stalled" if missing_checks > 0 and consecutive_no_progress >= trigger_window else "none"
    return {
        **request.stagnation,
        "recent_covered_check_counts": [*recent_counts, covered_checks][-20:],
        "latest_coverage_status": str(coverage_summary.get("status") or "pending"),
        "latest_covered_check_count": covered_checks,
        "latest_missing_check_count": missing_checks,
        "latest_covered_check_ids": list(coverage_summary.get("covered_check_ids") or [])[:20],
        "latest_missing_check_ids": list(coverage_summary.get("missing_check_ids") or [])[:20],
        "latest_coverage_top_gaps": list(coverage_summary.get("top_gaps") or [])[:5],
        "consecutive_no_required_coverage_delta": consecutive_no_progress,
        "evidence_progress_mode": evidence_progress_mode,
    }


def _recent_covered_check_counts(raw_recent_counts: object) -> list[int]:
    if not isinstance(raw_recent_counts, list):
        return []
    return [structured_non_negative_int(item) for item in raw_recent_counts]
