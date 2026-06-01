from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from loopora.coverage_target_semantics import coverage_target_is_required
from loopora.structured_numbers import structured_non_negative_int


def summarize_evidence_coverage_projection(projection: Mapping[str, Any], *, coverage_path_available: bool = True) -> dict:
    coverage_path = str(projection.get("coverage_path") or "").strip() if coverage_path_available else ""
    return {
        "ledger_path": str(projection.get("ledger_path") or ""),
        "coverage_path": coverage_path,
        "status": str(projection.get("status") or "pending"),
        "summary": _mapping_or_empty(projection.get("summary")),
        "evidence_count": structured_non_negative_int(projection.get("evidence_count")),
        "check_count": structured_non_negative_int(projection.get("check_count")),
        "covered_check_count": structured_non_negative_int(projection.get("covered_check_count")),
        "missing_check_count": structured_non_negative_int(projection.get("missing_check_count")),
        "covered_check_ids": _projection_string_list(projection.get("covered_check_ids")),
        "missing_check_ids": _projection_string_list(projection.get("missing_check_ids")),
        "target_count": structured_non_negative_int(projection.get("target_count")),
        "covered_target_count": structured_non_negative_int(projection.get("covered_target_count")),
        "weak_target_count": structured_non_negative_int(projection.get("weak_target_count")),
        "missing_target_count": structured_non_negative_int(projection.get("missing_target_count")),
        "blocked_target_count": structured_non_negative_int(projection.get("blocked_target_count")),
        "top_gaps": _projection_mapping_list(projection.get("top_gaps"), limit=5),
        "evidence_kind_counts": _mapping_or_empty(projection.get("evidence_kind_counts")),
        "artifact_ref_count": structured_non_negative_int(projection.get("artifact_ref_count")),
        "residual_risk_count": structured_non_negative_int(projection.get("residual_risk_count")),
        "risk_signals": _projection_string_list(projection.get("risk_signals"), limit=5),
        "latest_gatekeeper": _mapping_or_empty(projection.get("latest_gatekeeper")),
    }


def target_projection(row: Mapping[str, Any]) -> dict:
    return {
        "id": str(row.get("id") or ""),
        "kind": str(row.get("kind") or ""),
        "source_section": str(row.get("source_section") or ""),
        "source_id": str(row.get("source_id") or ""),
        "label": str(row.get("label") or ""),
        "text": str(row.get("text") or ""),
        "required": coverage_target_is_required(row),
        "status": str(row.get("status") or "missing"),
        "reason": str(row.get("reason") or ""),
        "evidence_refs": list(row.get("evidence_refs") or []),
        "artifact_refs": list(row.get("artifact_refs") or [])[:12],
    }


def top_coverage_gaps(target_rows: list[dict]) -> list[dict]:
    severity = {"blocked": 0, "missing": 1, "weak": 2}
    gaps = [row for row in target_rows if row.get("status") != "covered"]
    gaps.sort(key=lambda row: (0 if coverage_target_is_required(row) else 1, severity.get(str(row.get("status")), 9), str(row.get("id"))))
    return [
        {
            "target_id": row["id"],
            "kind": row["kind"],
            "source_section": row["source_section"],
            "status": row["status"],
            "required": coverage_target_is_required(row),
            "reason": row["reason"],
            "text": row["text"],
            "evidence_refs": row["evidence_refs"],
        }
        for row in gaps[:5]
    ]


def coverage_summary(status: str, top_gaps: list[dict]) -> dict:
    if status == "covered":
        reason = "Required and advisory coverage targets have supporting evidence."
    elif status == "weak":
        reason = "Required targets are covered, but advisory evidence is incomplete."
    elif status == "partial":
        reason = "Required coverage targets still lack direct evidence."
    elif status == "blocked":
        reason = "GateKeeper or target evidence reported a blocker."
    elif status == "legacy":
        reason = "This run does not have a readable evidence ledger."
    else:
        reason = "No evidence ledger entries are available yet."
    return {
        "status": status,
        "reason": reason,
        "primary_gap": top_gaps[0] if top_gaps else {},
    }


def _mapping_or_empty(value: object) -> dict:
    return dict(value) if isinstance(value, Mapping) else {}


def _projection_string_list(value: object, *, limit: int | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    items = [item for item in value if isinstance(item, str)]
    return items[:limit] if limit is not None else items


def _projection_mapping_list(value: object, *, limit: int) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)][:limit]
