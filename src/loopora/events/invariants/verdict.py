from __future__ import annotations

import sqlite3

from loopora.events.invariants.common import (
    BLOCKED_VERDICT_STATUSES,
    PASSABLE_COVERAGE_STATUSES,
    PASSING_VERDICT_STATUSES,
    VERDICT_STATUSES,
    accepted_evidence_ids,
    gap_entries_include_blocked,
    json_dict,
    latest_event_row,
    require_gap_entries_shape,
    residual_risk_entry_is_managed,
    verdict_evidence_refs,
    verdict_residual_risk_entries,
)
from loopora.events.store import DomainEventAppendRequest
from loopora.utils import structured_non_negative_int


def require_verdict_status_known(request: DomainEventAppendRequest) -> None:
    if request.aggregate_type != "run" or request.event_type != "VerdictIssued":
        return
    status = str((request.payload or {}).get("status") or "").strip().lower()
    if status not in VERDICT_STATUSES:
        raise ValueError("VerdictIssued status must be a kernel verdict status")


def require_verdict_evidence_refs_are_accepted(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.aggregate_type != "run" or request.event_type != "VerdictIssued":
        return
    evidence_refs = verdict_evidence_refs(request.payload or {})
    if not evidence_refs:
        return
    known_accepted_ids = accepted_evidence_ids(connection, request.stream_id)
    unknown_refs = sorted(ref for ref in evidence_refs if ref not in known_accepted_ids)
    if unknown_refs:
        raise ValueError("VerdictIssued evidence_refs must reference accepted EvidenceAccepted ids")


def require_verdict_next_gap_shape(request: DomainEventAppendRequest) -> None:
    if request.aggregate_type != "run" or request.event_type != "VerdictIssued":
        return
    status = str((request.payload or {}).get("status") or "").strip().lower()
    next_gap = (request.payload or {}).get("next_gap")
    if next_gap is None:
        return
    require_gap_entries_shape(next_gap, field_name="VerdictIssued next_gap")
    if status != "blocked" and gap_entries_include_blocked(next_gap):
        raise ValueError("blocked VerdictIssued next_gap requires blocked status")


def require_next_gap_selected_shape(request: DomainEventAppendRequest) -> None:
    if request.aggregate_type != "run" or request.event_type != "NextGapSelected":
        return
    payload = request.payload or {}
    next_gap = payload.get("next_gap")
    require_gap_entries_shape(next_gap, field_name="NextGapSelected next_gap")
    if not next_gap:
        raise ValueError("NextGapSelected requires next_gap")
    target_id = str(payload.get("target_id") or "").strip()
    status = str(payload.get("status") or "").strip().lower()
    if not target_id:
        raise ValueError("NextGapSelected requires target_id")
    if status not in {"missing", "weak", "blocked"}:
        raise ValueError("NextGapSelected requires unresolved status")
    if not any(
        target_id == str(item.get("target_id") or "").strip()
        and status == str(item.get("status") or "").strip().lower()
        for item in next_gap
        if isinstance(item, dict)
    ):
        raise ValueError("NextGapSelected target_id and status must match next_gap entry")


def require_residual_risk_accepted_shape(request: DomainEventAppendRequest) -> None:
    if request.aggregate_type != "run" or request.event_type != "ResidualRiskAccepted":
        return
    payload = request.payload or {}
    entries = payload.get("residual_risk")
    if not isinstance(entries, list):
        raise ValueError("ResidualRiskAccepted residual_risk must be a list")
    if not entries:
        raise ValueError("ResidualRiskAccepted requires residual_risk entries")
    if any(not isinstance(entry, dict) for entry in entries):
        raise ValueError("ResidualRiskAccepted residual_risk entries must be objects")
    if any(not residual_risk_entry_is_managed(entry) for entry in entries if isinstance(entry, dict)):
        raise ValueError("ResidualRiskAccepted residual_risk entries require management path")
    risk_count = structured_non_negative_int(payload.get("risk_count"))
    if risk_count != len(entries):
        raise ValueError("ResidualRiskAccepted risk_count must match residual_risk entries")


def require_passing_verdict_has_no_next_gap(request: DomainEventAppendRequest) -> None:
    if request.aggregate_type != "run" or request.event_type != "VerdictIssued":
        return
    status = str((request.payload or {}).get("status") or "").strip().lower()
    next_gap = (request.payload or {}).get("next_gap")
    if status in PASSING_VERDICT_STATUSES and isinstance(next_gap, list) and next_gap:
        raise ValueError("passing VerdictIssued cannot include unresolved next_gap")


def require_blocked_coverage_has_blocked_verdict(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.aggregate_type != "run" or request.event_type != "VerdictIssued":
        return
    status = str((request.payload or {}).get("status") or "").strip().lower()
    if status in BLOCKED_VERDICT_STATUSES:
        return
    coverage_row = latest_event_row(connection, request.stream_id, "CoverageRecomputed")
    if coverage_row is None:
        return
    coverage_payload = json_dict(coverage_row["payload_json"])
    coverage_status = str(coverage_payload.get("status") or "").strip().lower()
    blocked_count = structured_non_negative_int(coverage_payload.get("blocked_target_count"))
    if coverage_status == "blocked" or blocked_count:
        raise ValueError("VerdictIssued must be blocked when latest CoverageRecomputed has blocked targets")


def require_passing_verdict_has_passable_coverage(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.aggregate_type != "run" or request.event_type != "VerdictIssued":
        return
    status = str((request.payload or {}).get("status") or "").strip().lower()
    if status not in PASSING_VERDICT_STATUSES:
        return
    coverage_row = latest_event_row(connection, request.stream_id, "CoverageRecomputed")
    coverage_payload = json_dict(coverage_row["payload_json"]) if coverage_row is not None else {}
    coverage_status = str(coverage_payload.get("status") or "").strip().lower()
    if coverage_status not in PASSABLE_COVERAGE_STATUSES:
        raise ValueError("passing VerdictIssued requires latest CoverageRecomputed to be covered or weak")


def require_passed_with_residual_risk_has_managed_risk(request: DomainEventAppendRequest) -> None:
    if request.aggregate_type != "run" or request.event_type != "VerdictIssued":
        return
    status = str((request.payload or {}).get("status") or "").strip().lower()
    if status != "passed_with_residual_risk":
        return
    entries = verdict_residual_risk_entries(request.payload or {})
    if not entries:
        raise ValueError("passed_with_residual_risk VerdictIssued requires residual_risk bucket")
    if any(not residual_risk_entry_is_managed(entry) for entry in entries):
        raise ValueError("passed_with_residual_risk VerdictIssued residual_risk entries require management path")
