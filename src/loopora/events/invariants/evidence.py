from __future__ import annotations

import sqlite3

from loopora.events.invariants.common import accepted_evidence_ids, evidence_verifies_evidence_refs
from loopora.events.store import DomainEventAppendRequest


def require_evidence_accepted_identity(request: DomainEventAppendRequest) -> None:
    if request.aggregate_type != "run" or request.event_type not in {"EvidenceSubmitted", "EvidenceAccepted"}:
        return
    payload = request.payload or {}
    evidence_id = str(payload.get("evidence_id") or "").strip()
    if not evidence_id:
        raise ValueError(f"{request.event_type} requires evidence_id")
    raw_verifies = payload.get("verifies")
    if raw_verifies is not None and not isinstance(raw_verifies, list):
        raise ValueError(f"{request.event_type} verifies must be a list")
    verifies = [str(item).strip() for item in (raw_verifies or []) if str(item).strip()]
    if not verifies:
        raise ValueError(f"{request.event_type} requires at least one verifies reference")


def require_evidence_linked_to_target_identity(request: DomainEventAppendRequest) -> None:
    if request.aggregate_type != "run" or request.event_type != "EvidenceLinkedToTarget":
        return
    payload = request.payload or {}
    if not str(payload.get("evidence_id") or "").strip():
        raise ValueError("EvidenceLinkedToTarget requires evidence_id")
    target_refs = payload.get("target_refs")
    if not isinstance(target_refs, list) or not [str(item).strip() for item in target_refs if str(item).strip()]:
        raise ValueError("EvidenceLinkedToTarget requires target_refs")


def require_evidence_verified_evidence_refs_are_accepted(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.aggregate_type != "run" or request.event_type != "EvidenceAccepted":
        return
    refs = evidence_verifies_evidence_refs((request.payload or {}).get("verifies"))
    if not refs:
        return
    payload = request.payload or {}
    known_accepted_ids = accepted_evidence_ids(connection, request.stream_id)
    current_id = str(payload.get("evidence_id") or "").strip()
    if payload.get("measured_evidence") is True and current_id:
        known_accepted_ids.add(current_id)
    unknown_refs = sorted(ref for ref in refs if ref not in known_accepted_ids)
    if unknown_refs:
        raise ValueError("EvidenceAccepted verifies evidence refs must reference prior accepted evidence")
