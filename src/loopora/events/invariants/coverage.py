from __future__ import annotations

from loopora.events.invariants.common import (
    COVERAGE_STATUSES,
    CoverageTargetCounts,
    gap_entries_include_blocked,
    require_gap_entries_shape,
)
from loopora.events.store import DomainEventAppendRequest
from loopora.utils import structured_non_negative_int


def require_coverage_payload_status_consistency(request: DomainEventAppendRequest) -> None:
    if request.aggregate_type != "run" or request.event_type != "CoverageRecomputed":
        return
    payload = request.payload or {}
    coverage_status = str(payload.get("status") or "").strip().lower()
    target_count = structured_non_negative_int(payload.get("target_count"))
    covered_count = structured_non_negative_int(payload.get("covered_target_count"))
    weak_count = structured_non_negative_int(payload.get("weak_target_count"))
    missing_count = structured_non_negative_int(payload.get("missing_target_count"))
    blocked_count = structured_non_negative_int(payload.get("blocked_target_count"))
    counts = (target_count, covered_count, weak_count, missing_count, blocked_count)
    _require_coverage_status_known(coverage_status)
    _require_coverage_target_counts_fit_total(counts)
    _require_coverage_status_matches_counts(coverage_status, counts)


def require_coverage_top_gaps_shape(request: DomainEventAppendRequest) -> None:
    if request.aggregate_type != "run" or request.event_type != "CoverageRecomputed":
        return
    coverage_status = str((request.payload or {}).get("status") or "").strip().lower()
    top_gaps = (request.payload or {}).get("top_gaps")
    if top_gaps is None:
        return
    require_gap_entries_shape(top_gaps, field_name="CoverageRecomputed top_gaps")
    if coverage_status == "covered" and top_gaps:
        raise ValueError("covered CoverageRecomputed cannot include top_gaps")
    if coverage_status != "blocked" and gap_entries_include_blocked(top_gaps):
        raise ValueError("blocked CoverageRecomputed top_gaps require blocked status")


def _require_coverage_status_known(coverage_status: str) -> None:
    if coverage_status not in COVERAGE_STATUSES:
        raise ValueError("CoverageRecomputed status must be a kernel coverage status")


def _require_coverage_target_counts_fit_total(counts: CoverageTargetCounts) -> None:
    target_count, covered_count, weak_count, missing_count, blocked_count = counts
    if target_count and any(count > target_count for count in (covered_count, weak_count, missing_count, blocked_count)):
        raise ValueError("CoverageRecomputed target counts cannot exceed target_count")
    if target_count and covered_count + weak_count + missing_count + blocked_count > target_count:
        raise ValueError("CoverageRecomputed classified target counts cannot exceed target_count")


def _require_coverage_status_matches_counts(coverage_status: str, counts: CoverageTargetCounts) -> None:
    if coverage_status == "covered":
        _require_covered_coverage_counts(counts)
    elif coverage_status == "weak":
        _require_weak_coverage_counts(counts)
    elif coverage_status == "partial":
        _require_partial_coverage_counts(counts)
    elif coverage_status == "blocked":
        _require_blocked_coverage_counts(counts)


def _require_blocked_coverage_counts(counts: CoverageTargetCounts) -> None:
    _, _, _, _, blocked_count = counts
    if not blocked_count:
        raise ValueError("blocked CoverageRecomputed requires blocked_target_count")


def _require_covered_coverage_counts(counts: CoverageTargetCounts) -> None:
    target_count, covered_count, weak_count, missing_count, blocked_count = counts
    if weak_count or missing_count or blocked_count:
        raise ValueError("covered CoverageRecomputed cannot include weak, missing, or blocked targets")
    if target_count and covered_count != target_count:
        raise ValueError("covered CoverageRecomputed requires covered_target_count to match target_count")


def _require_weak_coverage_counts(counts: CoverageTargetCounts) -> None:
    target_count, _, weak_count, missing_count, blocked_count = counts
    if blocked_count:
        raise ValueError("weak CoverageRecomputed cannot include blocked targets")
    if target_count and not weak_count and not missing_count:
        raise ValueError("weak CoverageRecomputed requires weak or missing targets")


def _require_partial_coverage_counts(counts: CoverageTargetCounts) -> None:
    target_count, _, weak_count, missing_count, blocked_count = counts
    if blocked_count:
        raise ValueError("partial CoverageRecomputed cannot include blocked targets")
    if target_count and not weak_count and not missing_count:
        raise ValueError("partial CoverageRecomputed requires weak or missing targets")
