from __future__ import annotations

import sqlite3

from loopora.events.invariants.common import (
    PASSING_VERDICT_STATUSES,
    json_dict,
    latest_event_row,
    residual_risk_entry_is_managed,
    verdict_residual_risk_entries,
)
from loopora.events.store import DomainEventAppendRequest


def require_verdict_has_coverage_causation(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.aggregate_type != "run" or request.event_type not in {"VerdictRequested", "VerdictIssued"}:
        return
    coverage_row = latest_event_row(connection, request.stream_id, "CoverageRecomputed")
    if coverage_row is None:
        return
    if request.causation_id != coverage_row["event_id"]:
        requested_row = latest_event_row(connection, request.stream_id, "VerdictRequested")
        if (
            request.event_type != "VerdictIssued"
            or requested_row is None
            or request.causation_id != requested_row["event_id"]
            or requested_row["causation_id"] != coverage_row["event_id"]
        ):
            raise ValueError(f"{request.event_type} requires causation_id to reference latest CoverageRecomputed")


def require_verdict_closure_causation(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.aggregate_type != "run" or request.event_type not in {"VerdictAllowedClosure", "VerdictBlockedClosure"}:
        return
    verdict_row = latest_event_row(connection, request.stream_id, "VerdictIssued")
    if verdict_row is None:
        raise ValueError(f"{request.event_type} requires prior VerdictIssued")
    if request.causation_id != verdict_row["event_id"]:
        raise ValueError(f"{request.event_type} requires causation_id to reference latest VerdictIssued")
    verdict_status = str(json_dict(verdict_row["payload_json"]).get("status") or "").strip().lower()
    if request.event_type == "VerdictAllowedClosure" and verdict_status not in PASSING_VERDICT_STATUSES:
        raise ValueError("VerdictAllowedClosure requires passing VerdictIssued")
    if request.event_type == "VerdictBlockedClosure" and verdict_status in PASSING_VERDICT_STATUSES:
        raise ValueError("VerdictBlockedClosure requires non-passing VerdictIssued")


def require_next_gap_selected_causation(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.aggregate_type != "run" or request.event_type != "NextGapSelected":
        return
    closure_row = latest_event_row(connection, request.stream_id, "VerdictBlockedClosure")
    if closure_row is None:
        raise ValueError("NextGapSelected requires prior VerdictBlockedClosure")
    if request.causation_id != closure_row["event_id"]:
        raise ValueError("NextGapSelected requires causation_id to reference latest VerdictBlockedClosure")
    existing_row = connection.execute(
        """
        SELECT event_type FROM event_store
        WHERE stream_id = ?
          AND causation_id = ?
          AND event_type = 'NextGapSelected'
        ORDER BY sequence DESC
        LIMIT 1
        """,
        (request.stream_id, request.causation_id),
    ).fetchone()
    if existing_row is not None:
        raise ValueError("VerdictBlockedClosure already selected next gap")
    verdict_row = latest_event_row(connection, request.stream_id, "VerdictIssued")
    if verdict_row is None or closure_row["causation_id"] != verdict_row["event_id"]:
        raise ValueError("NextGapSelected requires latest VerdictBlockedClosure for latest VerdictIssued")
    verdict_payload = json_dict(verdict_row["payload_json"])
    verdict_next_gap = verdict_payload.get("next_gap")
    if not isinstance(verdict_next_gap, list) or not verdict_next_gap:
        raise ValueError("NextGapSelected requires latest VerdictIssued next_gap")
    target_id = str((request.payload or {}).get("target_id") or "").strip()
    status = str((request.payload or {}).get("status") or "").strip().lower()
    if not any(
        target_id == str(item.get("target_id") or "").strip()
        and status == str(item.get("status") or "").strip().lower()
        for item in verdict_next_gap
        if isinstance(item, dict)
    ):
        raise ValueError("NextGapSelected must select a latest VerdictIssued next_gap entry")


def require_residual_risk_accepted_causation(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.aggregate_type != "run" or request.event_type != "ResidualRiskAccepted":
        return
    closure_row = latest_event_row(connection, request.stream_id, "VerdictAllowedClosure")
    if closure_row is None:
        raise ValueError("ResidualRiskAccepted requires prior VerdictAllowedClosure")
    if request.causation_id != closure_row["event_id"]:
        raise ValueError("ResidualRiskAccepted requires causation_id to reference latest VerdictAllowedClosure")
    existing_row = connection.execute(
        """
        SELECT event_type FROM event_store
        WHERE stream_id = ?
          AND causation_id = ?
          AND event_type = 'ResidualRiskAccepted'
        ORDER BY sequence DESC
        LIMIT 1
        """,
        (request.stream_id, request.causation_id),
    ).fetchone()
    if existing_row is not None:
        raise ValueError("VerdictAllowedClosure already accepted residual risk")
    verdict_row = latest_event_row(connection, request.stream_id, "VerdictIssued")
    if verdict_row is None or closure_row["causation_id"] != verdict_row["event_id"]:
        raise ValueError("ResidualRiskAccepted requires latest VerdictAllowedClosure for latest VerdictIssued")
    verdict_payload = json_dict(verdict_row["payload_json"])
    if str(verdict_payload.get("status") or "").strip().lower() != "passed_with_residual_risk":
        raise ValueError("ResidualRiskAccepted requires passed_with_residual_risk VerdictIssued")
    entries = verdict_residual_risk_entries(verdict_payload)
    if not entries or any(not residual_risk_entry_is_managed(entry) for entry in entries):
        raise ValueError("ResidualRiskAccepted requires latest VerdictIssued managed residual_risk entries")
