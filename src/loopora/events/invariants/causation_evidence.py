from __future__ import annotations

import sqlite3

from loopora.events.invariants.common import (
    PASSABLE_COVERAGE_STATUSES,
    evidence_verifies_coverage_source,
    json_dict,
    latest_event_row,
)
from loopora.events.store import DomainEventAppendRequest


def require_passable_coverage_has_evidence_causation(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.aggregate_type != "run" or request.event_type != "CoverageRecomputed":
        return
    coverage_status = str((request.payload or {}).get("status") or "").strip().lower()
    if coverage_status not in PASSABLE_COVERAGE_STATUSES:
        return
    evidence_row = latest_event_row(connection, request.stream_id, "EvidenceAccepted")
    if evidence_row is None:
        raise ValueError("passable CoverageRecomputed requires prior EvidenceAccepted")
    if request.causation_id != evidence_row["event_id"]:
        linked_row = latest_event_row(connection, request.stream_id, "EvidenceLinkedToTarget")
        if linked_row is None or request.causation_id != linked_row["event_id"]:
            raise ValueError(
                "passable CoverageRecomputed requires causation_id to reference latest EvidenceAccepted or EvidenceLinkedToTarget"
            )
        linked_payload = json_dict(linked_row["payload_json"])
        if not linked_payload.get("target_refs"):
            raise ValueError("passable CoverageRecomputed requires latest EvidenceLinkedToTarget to reference target_refs")
        return
    evidence_payload = json_dict(evidence_row["payload_json"])
    if not evidence_verifies_coverage_source(evidence_payload.get("verifies")):
        raise ValueError("passable CoverageRecomputed requires latest EvidenceAccepted to verify a target or evidence ref")


def require_evidence_linked_to_target_causation(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.aggregate_type != "run" or request.event_type != "EvidenceLinkedToTarget":
        return
    evidence_row = latest_event_row(connection, request.stream_id, "EvidenceAccepted")
    if evidence_row is None:
        raise ValueError("EvidenceLinkedToTarget requires prior EvidenceAccepted")
    if request.causation_id != evidence_row["event_id"]:
        raise ValueError("EvidenceLinkedToTarget requires causation_id to reference latest EvidenceAccepted")
