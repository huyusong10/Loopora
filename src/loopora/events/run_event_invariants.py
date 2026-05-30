from __future__ import annotations

import json
import sqlite3

from loopora.events.schemas import RUN_EVENT_TYPES, RUN_TERMINAL_EVENT_TYPES
from loopora.events.store import DomainEventAppendRequest
from loopora.structured_numbers import structured_non_negative_int

VERDICT_STATUSES = frozenset({"not_evaluated", "continue_required", "blocked", "passed", "passed_with_residual_risk"})
COVERAGE_STATUSES = frozenset({"partial", "covered", "weak", "blocked"})
PASSING_VERDICT_STATUSES = frozenset({"passed", "passed_with_residual_risk"})
BLOCKED_VERDICT_STATUSES = frozenset({"blocked"})
PASSABLE_COVERAGE_STATUSES = frozenset({"covered", "weak"})
UNRESOLVED_GAP_STATUSES = frozenset({"missing", "weak", "blocked"})
RESIDUAL_RISK_MANAGEMENT_KEYS = frozenset({"owner", "follow_up", "followup", "acceptance_path"})
CoverageTargetCounts = tuple[int, int, int, int, int]


def require_run_event_append_invariants(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    _require_run_lifecycle_append_allowed(connection, request)
    _require_run_closed_causation_references_passing_verdict(connection, request)
    _require_step_result_event_identity(request)
    _require_step_result_event_causation(connection, request)
    _require_evidence_accepted_identity(request)
    _require_evidence_verified_evidence_refs_are_accepted(connection, request)
    _require_coverage_payload_status_consistency(request)
    _require_coverage_top_gaps_shape(request)
    _require_passable_coverage_has_evidence_causation(connection, request)
    _require_verdict_has_coverage_causation(connection, request)
    _require_verdict_status_known(request)
    _require_verdict_evidence_refs_are_accepted(connection, request)
    _require_verdict_next_gap_shape(request)
    _require_passing_verdict_has_no_next_gap(request)
    _require_blocked_coverage_has_blocked_verdict(connection, request)
    _require_passing_verdict_has_passable_coverage(connection, request)
    _require_passed_with_residual_risk_has_managed_risk(request)


def _require_run_lifecycle_append_allowed(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.aggregate_type != "run" or request.event_type not in RUN_EVENT_TYPES:
        return
    placeholders = ",".join("?" for _item in RUN_TERMINAL_EVENT_TYPES)
    row = connection.execute(
        f"""
        SELECT event_type FROM event_store
        WHERE stream_id = ? AND event_type IN ({placeholders})
        ORDER BY sequence DESC
        LIMIT 1
        """,
        (request.stream_id, *sorted(RUN_TERMINAL_EVENT_TYPES)),
    ).fetchone()
    if row is not None:
        raise ValueError(
            "terminal run stream cannot append lifecycle event "
            f"{request.event_type} after {row['event_type']}"
        )


def _require_run_closed_causation_references_passing_verdict(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.aggregate_type != "run" or request.event_type != "RunClosed" or not request.causation_id:
        return
    row = connection.execute(
        """
        SELECT event_id, event_type, payload_json FROM event_store
        WHERE stream_id = ? AND event_id = ?
        LIMIT 1
        """,
        (request.stream_id, request.causation_id),
    ).fetchone()
    if row is None or row["event_type"] != "VerdictIssued":
        raise ValueError("RunClosed causation_id must reference VerdictIssued")
    payload = _json_dict(row["payload_json"])
    status = str(payload.get("status") or "").strip().lower()
    if status not in PASSING_VERDICT_STATUSES:
        raise ValueError("RunClosed causation_id must reference passing VerdictIssued")
    latest_row = _latest_event_row(connection, request.stream_id, "VerdictIssued")
    if latest_row is not None and request.causation_id != latest_row["event_id"]:
        raise ValueError("RunClosed causation_id must reference latest VerdictIssued")


def _require_evidence_accepted_identity(request: DomainEventAppendRequest) -> None:
    if request.aggregate_type != "run" or request.event_type != "EvidenceAccepted":
        return
    payload = request.payload or {}
    evidence_id = str(payload.get("evidence_id") or "").strip()
    if not evidence_id:
        raise ValueError("EvidenceAccepted requires evidence_id")
    raw_verifies = payload.get("verifies")
    if raw_verifies is not None and not isinstance(raw_verifies, list):
        raise ValueError("EvidenceAccepted verifies must be a list")
    verifies = [str(item).strip() for item in (raw_verifies or []) if str(item).strip()]
    if not verifies:
        raise ValueError("EvidenceAccepted requires at least one verifies reference")


def _require_evidence_verified_evidence_refs_are_accepted(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.aggregate_type != "run" or request.event_type != "EvidenceAccepted":
        return
    refs = _evidence_verifies_evidence_refs((request.payload or {}).get("verifies"))
    if not refs:
        return
    payload = request.payload or {}
    accepted_ids = _accepted_evidence_ids(connection, request.stream_id)
    current_id = str(payload.get("evidence_id") or "").strip()
    if payload.get("measured_evidence") is True and current_id:
        accepted_ids.add(current_id)
    unknown_refs = sorted(ref for ref in refs if ref not in accepted_ids)
    if unknown_refs:
        raise ValueError("EvidenceAccepted verifies evidence refs must reference prior accepted evidence")


def _require_step_result_event_causation(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.aggregate_type != "run":
        return
    required_source = {
        "StepAccepted": "StepSubmitted",
        "StepSubmissionRejected": "StepSubmitted",
        "StepCommitted": "StepAccepted",
    }.get(request.event_type)
    if required_source is None:
        return
    row = _latest_event_row(connection, request.stream_id, required_source)
    if row is None:
        raise ValueError(f"{request.event_type} requires prior {required_source}")
    if request.causation_id != row["event_id"]:
        raise ValueError(f"{request.event_type} requires causation_id to reference latest {required_source}")
    _require_step_submission_decision_is_open(connection, request)
    _require_step_acceptance_commit_is_open(connection, request)
    _require_step_result_payload_matches_source(request, source_payload=_json_dict(row["payload_json"]))


def _require_step_result_event_identity(request: DomainEventAppendRequest) -> None:
    if request.aggregate_type != "run" or request.event_type not in {
        "StepSubmitted",
        "StepAccepted",
        "StepSubmissionRejected",
        "StepCommitted",
    }:
        return
    payload = request.payload or {}
    if not str(payload.get("step_id") or "").strip():
        raise ValueError(f"{request.event_type} requires step_id")
    if payload.get("iteration") is None or not str(payload.get("iteration")).strip():
        raise ValueError(f"{request.event_type} requires iteration")


def _require_step_submission_decision_is_open(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.event_type not in {"StepAccepted", "StepSubmissionRejected"} or not request.causation_id:
        return
    row = connection.execute(
        """
        SELECT event_type FROM event_store
        WHERE stream_id = ?
          AND causation_id = ?
          AND event_type IN ('StepAccepted', 'StepSubmissionRejected')
        ORDER BY sequence DESC
        LIMIT 1
        """,
        (request.stream_id, request.causation_id),
    ).fetchone()
    if row is not None:
        raise ValueError("StepSubmitted already has accepted or rejected decision")


def _require_step_acceptance_commit_is_open(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.event_type != "StepCommitted" or not request.causation_id:
        return
    row = connection.execute(
        """
        SELECT event_type FROM event_store
        WHERE stream_id = ?
          AND causation_id = ?
          AND event_type = 'StepCommitted'
        ORDER BY sequence DESC
        LIMIT 1
        """,
        (request.stream_id, request.causation_id),
    ).fetchone()
    if row is not None:
        raise ValueError("StepAccepted already has committed result")


def _require_step_result_payload_matches_source(request: DomainEventAppendRequest, *, source_payload: dict) -> None:
    payload = request.payload or {}
    source_step_id = str(source_payload.get("step_id") or "").strip()
    step_id = str(payload.get("step_id") or "").strip()
    if not step_id or not source_step_id or step_id != source_step_id:
        raise ValueError(f"{request.event_type} requires step_id to match causation event")
    source_iteration = source_payload.get("iteration")
    iteration = payload.get("iteration")
    if source_iteration is not None and iteration is not None and str(iteration) != str(source_iteration):
        raise ValueError(f"{request.event_type} requires iteration to match causation event")


def _require_coverage_payload_status_consistency(request: DomainEventAppendRequest) -> None:
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


def _require_coverage_top_gaps_shape(request: DomainEventAppendRequest) -> None:
    if request.aggregate_type != "run" or request.event_type != "CoverageRecomputed":
        return
    coverage_status = str((request.payload or {}).get("status") or "").strip().lower()
    top_gaps = (request.payload or {}).get("top_gaps")
    if top_gaps is None:
        return
    _require_gap_entries_shape(top_gaps, field_name="CoverageRecomputed top_gaps")
    if coverage_status == "covered" and top_gaps:
        raise ValueError("covered CoverageRecomputed cannot include top_gaps")
    if coverage_status != "blocked" and _gap_entries_include_blocked(top_gaps):
        raise ValueError("blocked CoverageRecomputed top_gaps require blocked status")


def _require_passable_coverage_has_evidence_causation(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.aggregate_type != "run" or request.event_type != "CoverageRecomputed":
        return
    coverage_status = str((request.payload or {}).get("status") or "").strip().lower()
    if coverage_status not in PASSABLE_COVERAGE_STATUSES:
        return
    evidence_row = _latest_event_row(connection, request.stream_id, "EvidenceAccepted")
    if evidence_row is None:
        raise ValueError("passable CoverageRecomputed requires prior EvidenceAccepted")
    if request.causation_id != evidence_row["event_id"]:
        raise ValueError("passable CoverageRecomputed requires causation_id to reference latest EvidenceAccepted")
    evidence_payload = _json_dict(evidence_row["payload_json"])
    if not _evidence_verifies_coverage_source(evidence_payload.get("verifies")):
        raise ValueError("passable CoverageRecomputed requires latest EvidenceAccepted to verify a target or evidence ref")


def _require_passing_verdict_has_passable_coverage(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.aggregate_type != "run" or request.event_type != "VerdictIssued":
        return
    status = str((request.payload or {}).get("status") or "").strip().lower()
    if status not in PASSING_VERDICT_STATUSES:
        return
    coverage_row = _latest_event_row(connection, request.stream_id, "CoverageRecomputed")
    coverage_payload = _json_dict(coverage_row["payload_json"]) if coverage_row is not None else {}
    coverage_status = str(coverage_payload.get("status") or "").strip().lower()
    if coverage_status not in PASSABLE_COVERAGE_STATUSES:
        raise ValueError("passing VerdictIssued requires latest CoverageRecomputed to be covered or weak")


def _require_blocked_coverage_has_blocked_verdict(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.aggregate_type != "run" or request.event_type != "VerdictIssued":
        return
    status = str((request.payload or {}).get("status") or "").strip().lower()
    if status in BLOCKED_VERDICT_STATUSES:
        return
    coverage_row = _latest_event_row(connection, request.stream_id, "CoverageRecomputed")
    if coverage_row is None:
        return
    coverage_payload = _json_dict(coverage_row["payload_json"])
    coverage_status = str(coverage_payload.get("status") or "").strip().lower()
    blocked_count = structured_non_negative_int(coverage_payload.get("blocked_target_count"))
    if coverage_status == "blocked" or blocked_count:
        raise ValueError("VerdictIssued must be blocked when latest CoverageRecomputed has blocked targets")


def _require_passed_with_residual_risk_has_managed_risk(request: DomainEventAppendRequest) -> None:
    if request.aggregate_type != "run" or request.event_type != "VerdictIssued":
        return
    status = str((request.payload or {}).get("status") or "").strip().lower()
    if status != "passed_with_residual_risk":
        return
    entries = _verdict_residual_risk_entries(request.payload or {})
    if not entries:
        raise ValueError("passed_with_residual_risk VerdictIssued requires residual_risk bucket")
    if any(not _residual_risk_entry_is_managed(entry) for entry in entries):
        raise ValueError("passed_with_residual_risk VerdictIssued residual_risk entries require management path")


def _require_verdict_evidence_refs_are_accepted(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.aggregate_type != "run" or request.event_type != "VerdictIssued":
        return
    evidence_refs = _verdict_evidence_refs(request.payload or {})
    if not evidence_refs:
        return
    accepted_ids = _accepted_evidence_ids(connection, request.stream_id)
    unknown_refs = sorted(ref for ref in evidence_refs if ref not in accepted_ids)
    if unknown_refs:
        raise ValueError("VerdictIssued evidence_refs must reference accepted EvidenceAccepted ids")


def _require_verdict_status_known(request: DomainEventAppendRequest) -> None:
    if request.aggregate_type != "run" or request.event_type != "VerdictIssued":
        return
    status = str((request.payload or {}).get("status") or "").strip().lower()
    if status not in VERDICT_STATUSES:
        raise ValueError("VerdictIssued status must be a kernel verdict status")


def _require_verdict_next_gap_shape(request: DomainEventAppendRequest) -> None:
    if request.aggregate_type != "run" or request.event_type != "VerdictIssued":
        return
    status = str((request.payload or {}).get("status") or "").strip().lower()
    next_gap = (request.payload or {}).get("next_gap")
    if next_gap is None:
        return
    _require_gap_entries_shape(next_gap, field_name="VerdictIssued next_gap")
    if status != "blocked" and _gap_entries_include_blocked(next_gap):
        raise ValueError("blocked VerdictIssued next_gap requires blocked status")


def _require_passing_verdict_has_no_next_gap(request: DomainEventAppendRequest) -> None:
    if request.aggregate_type != "run" or request.event_type != "VerdictIssued":
        return
    status = str((request.payload or {}).get("status") or "").strip().lower()
    next_gap = (request.payload or {}).get("next_gap")
    if status in PASSING_VERDICT_STATUSES and isinstance(next_gap, list) and next_gap:
        raise ValueError("passing VerdictIssued cannot include unresolved next_gap")


def _require_verdict_has_coverage_causation(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.aggregate_type != "run" or request.event_type != "VerdictIssued":
        return
    coverage_row = _latest_event_row(connection, request.stream_id, "CoverageRecomputed")
    if coverage_row is None:
        return
    if request.causation_id != coverage_row["event_id"]:
        raise ValueError("VerdictIssued requires causation_id to reference latest CoverageRecomputed")


def _require_gap_entries_shape(value: object, *, field_name: str) -> None:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    for item in value:
        if not isinstance(item, dict):
            raise ValueError(f"{field_name} entries must be objects")
        target_id = str(item.get("target_id") or "").strip()
        if not target_id:
            raise ValueError(f"{field_name} entries require target_id")
        status = str(item.get("status") or "").strip().lower()
        if status not in UNRESOLVED_GAP_STATUSES:
            raise ValueError(f"{field_name} entries require unresolved status")


def _gap_entries_include_blocked(value: object) -> bool:
    return any(
        isinstance(item, dict) and str(item.get("status") or "").strip().lower() == "blocked"
        for item in list(value or [])
    )


def _json_dict(raw_value: object) -> dict:
    try:
        value = json.loads(str(raw_value or "{}"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _latest_event_row(connection: sqlite3.Connection, stream_id: str, event_type: str) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT event_id, event_type, payload_json FROM event_store
        WHERE stream_id = ? AND event_type = ?
        ORDER BY sequence DESC
        LIMIT 1
        """,
        (stream_id, event_type),
    ).fetchone()


def _evidence_verifies_coverage_source(value: object) -> bool:
    return any(str(item).strip().startswith(("target:", "evidence:")) for item in list(value or []))


def _evidence_verifies_evidence_refs(value: object) -> set[str]:
    refs: set[str] = set()
    for item in list(value or []):
        text = str(item).strip()
        if not text.startswith("evidence:"):
            continue
        ref = text.split(":", 1)[1].strip()
        if ref:
            refs.add(ref)
        else:
            refs.add(text)
    return refs


def _accepted_evidence_ids(connection: sqlite3.Connection, stream_id: str) -> set[str]:
    rows = connection.execute(
        """
        SELECT payload_json FROM event_store
        WHERE stream_id = ? AND event_type = 'EvidenceAccepted'
        """,
        (stream_id,),
    ).fetchall()
    return {
        evidence_id
        for row in rows
        if (evidence_id := str(_json_dict(row["payload_json"]).get("evidence_id") or "").strip())
    }


def _verdict_evidence_refs(payload: dict) -> set[str]:
    refs: set[str] = set()
    for item in _verdict_bucket_entries(payload):
        evidence_refs = item.get("evidence_refs")
        if "evidence_refs" in item and not isinstance(evidence_refs, list):
            raise ValueError("VerdictIssued evidence_refs must be a list")
        if not isinstance(evidence_refs, list):
            continue
        refs.update(str(ref).strip() for ref in evidence_refs if str(ref).strip())
    return refs


def _verdict_residual_risk_entries(payload: dict) -> list[dict]:
    buckets = payload.get("buckets")
    if not isinstance(buckets, dict):
        return []
    entries = buckets.get("residual_risk")
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def _verdict_bucket_entries(payload: dict) -> list[dict]:
    buckets = payload.get("buckets")
    if buckets is None:
        return []
    if not isinstance(buckets, dict):
        raise ValueError("VerdictIssued buckets must be an object")
    entries: list[dict] = []
    for items in buckets.values():
        if not isinstance(items, list):
            raise ValueError("VerdictIssued bucket entries must be lists")
        entries.extend(item for item in items if isinstance(item, dict))
    return entries


def _residual_risk_entry_is_managed(entry: dict) -> bool:
    if not str(entry.get("label") or entry.get("risk") or "").strip():
        return False
    if entry.get("managed") is True:
        return True
    return any(str(entry.get(key) or "").strip() for key in RESIDUAL_RISK_MANAGEMENT_KEYS)
