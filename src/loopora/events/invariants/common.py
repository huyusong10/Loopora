from __future__ import annotations

import json
import sqlite3

VERDICT_STATUSES = frozenset({"not_evaluated", "continue_required", "blocked", "passed", "passed_with_residual_risk"})
COVERAGE_STATUSES = frozenset({"partial", "covered", "weak", "blocked"})
PASSING_VERDICT_STATUSES = frozenset({"passed", "passed_with_residual_risk"})
BLOCKED_VERDICT_STATUSES = frozenset({"blocked"})
PASSABLE_COVERAGE_STATUSES = frozenset({"covered", "weak"})
UNRESOLVED_GAP_STATUSES = frozenset({"missing", "weak", "blocked"})
RESIDUAL_RISK_MANAGEMENT_KEYS = frozenset({"owner", "follow_up", "followup", "acceptance_path"})
CoverageTargetCounts = tuple[int, int, int, int, int]


def json_dict(raw_value: object) -> dict:
    try:
        value = json.loads(str(raw_value or "{}"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def latest_event_row(connection: sqlite3.Connection, stream_id: str, event_type: str) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT event_id, event_type, causation_id, payload_json FROM event_store
        WHERE stream_id = ? AND event_type = ?
        ORDER BY sequence DESC
        LIMIT 1
        """,
        (stream_id, event_type),
    ).fetchone()


def require_gap_entries_shape(value: object, *, field_name: str) -> None:
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


def gap_entries_include_blocked(value: object) -> bool:
    return any(
        isinstance(item, dict) and str(item.get("status") or "").strip().lower() == "blocked"
        for item in list(value or [])
    )


def evidence_verifies_coverage_source(value: object) -> bool:
    return any(str(item).strip().startswith(("target:", "evidence:")) for item in list(value or []))


def evidence_verifies_evidence_refs(value: object) -> set[str]:
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


def accepted_evidence_ids(connection: sqlite3.Connection, stream_id: str) -> set[str]:
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
        if (evidence_id := str(json_dict(row["payload_json"]).get("evidence_id") or "").strip())
    }


def verdict_evidence_refs(payload: dict) -> set[str]:
    refs: set[str] = set()
    for item in verdict_bucket_entries(payload):
        evidence_refs = item.get("evidence_refs")
        if "evidence_refs" in item and not isinstance(evidence_refs, list):
            raise ValueError("VerdictIssued evidence_refs must be a list")
        if not isinstance(evidence_refs, list):
            continue
        refs.update(str(ref).strip() for ref in evidence_refs if str(ref).strip())
    return refs


def verdict_residual_risk_entries(payload: dict) -> list[dict]:
    buckets = payload.get("buckets")
    if not isinstance(buckets, dict):
        return []
    entries = buckets.get("residual_risk")
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def verdict_bucket_entries(payload: dict) -> list[dict]:
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


def residual_risk_entry_is_managed(entry: dict) -> bool:
    if not str(entry.get("label") or entry.get("risk") or "").strip():
        return False
    if entry.get("managed") is True:
        return True
    return any(str(entry.get(key) or "").strip() for key in RESIDUAL_RISK_MANAGEMENT_KEYS)
